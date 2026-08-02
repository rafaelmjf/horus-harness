"""Estimate the token footprint Horus adds to native-agent workflows.

This is intentionally a measurement aid, not a billing oracle. The observed
attribution is an upper bound: if a turn touches Horus files or commands, the
whole turn is counted as Horus-related because local logs do not expose a
counterfactual "same turn without Horus" split.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, NamedTuple

from horus import codex_usage, skills, templates


class FootprintItem(NamedTuple):
    name: str
    chars: int
    estimated_tokens: int


class TokenUsage(NamedTuple):
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0


class UsageSummary(NamedTuple):
    agent: str
    turns: int
    horus_turns: int
    total: TokenUsage
    horus: TokenUsage


class SessionUsage(NamedTuple):
    session_id: str
    agent: str
    project: str
    status: str
    turns: int
    total: TokenUsage
    matched: bool
    note: str = ""


class BaselineSession(NamedTuple):
    session_id: str
    agent: str
    turns: int
    total: TokenUsage
    matched: bool
    note: str = ""


class BaselineGroup(NamedTuple):
    label: str
    sessions: list[BaselineSession]
    turns: int
    total: TokenUsage


class BaselineComparison(NamedTuple):
    without_horus: BaselineGroup
    with_horus: BaselineGroup
    incremental: TokenUsage


_HORUS_MARKERS = (
    "horus",
    ".horus",
    "horus-consolidate",
    "horus-distill-history",
    "horus-infer",
)


def rough_token_count(text: str) -> int:
    """A dependency-free prompt-size estimate: roughly one token per four chars."""
    return round(len(text) / 4) if text else 0


def static_footprint() -> list[FootprintItem]:
    """Prompt/template surfaces Horus projects into native agents."""
    items: list[tuple[str, str]] = [
        ("managed instruction block", templates.shared_block("AGENTS.md")),
        ("usage closure prompt", templates.USAGE_CLOSURE_PROMPT),
        ("usage closure advisory", templates.USAGE_CLOSURE_ADVISORY),
        ("merge closure instruction", templates.MERGE_CLOSURE_INSTRUCTION),
        ("hosted-session restart guard instruction", templates.HOSTED_RESTART_INSTRUCTION),
        ("consolidate routine prompt", templates.CONSOLIDATE_PROMPT),
        ("distill-history routine prompt", templates.DISTILL_HISTORY_PROMPT),
        ("infer routine prompt", templates.INFER_PROMPT),
    ]
    for skill in skills.SKILLS:
        items.append((f"{skill.name} skill", skill.content))
    return [FootprintItem(name, len(text), rough_token_count(text)) for name, text in items]


def codex_overhead(project_root: Path, *, home: Path | None = None) -> UsageSummary:
    total = TokenUsage()
    horus = TokenUsage()
    turns = horus_turns = 0
    root = project_root.resolve()
    for path in _codex_rollouts(home or codex_usage.codex_home()):
        current_project = False
        horus_related = False
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "turn_context":
                payload = event.get("payload")
                current_project = isinstance(payload, dict) and _matches_project(payload, root)
                horus_related = False
                continue
            if not current_project:
                continue
            payload = event.get("payload")
            if _contains_horus_marker(payload):
                horus_related = True
            usage = _codex_token_usage(payload)
            if usage is None:
                continue
            turns += 1
            total = _add_usage(total, usage)
            if horus_related:
                horus_turns += 1
                horus = _add_usage(horus, usage)
            horus_related = False
    return UsageSummary("codex", turns, horus_turns, total, horus)


def codex_session_usage(
    session_id: str,
    project_root: Path,
    *,
    home: Path | None = None,
) -> tuple[int, TokenUsage] | None:
    root = project_root.resolve()
    for path in _codex_rollouts(home or codex_usage.codex_home()):
        current_session = False
        current_project = False
        meta_project = False
        turns = 0
        total = TokenUsage()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            payload = event.get("payload")
            if event.get("type") == "session_meta":
                current_session = isinstance(payload, dict) and (
                    payload.get("session_id") == session_id or payload.get("id") == session_id
                )
                meta_project = isinstance(payload, dict) and _matches_project(payload, root)
                current_project = meta_project
                continue
            if not current_session:
                continue
            if event.get("type") == "turn_context":
                current_project = isinstance(payload, dict) and _matches_project(payload, root)
                continue
            usage = _codex_token_usage(payload)
            if usage is None or not (current_project or meta_project):
                continue
            turns += 1
            total = _add_usage(total, usage)
        if current_session:
            return turns, total
    return None


def claude_overhead(project_root: Path, *, home: Path | None = None) -> UsageSummary:
    root = project_root.resolve()
    records: dict[str, dict[str, Any]] = {}
    for path in _claude_jsonl_files(home):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or not _event_matches_project(event, root):
                continue
            usage = _claude_token_usage(event)
            if usage is None:
                continue
            key = str(event.get("requestId") or event.get("uuid") or f"{path}:{len(records)}")
            rec = records.setdefault(key, {"usage": usage, "horus": False})
            rec["horus"] = bool(rec["horus"]) or _contains_horus_marker(event)

    total = TokenUsage()
    horus = TokenUsage()
    horus_turns = 0
    for rec in records.values():
        usage = rec["usage"]
        total = _add_usage(total, usage)
        if rec["horus"]:
            horus_turns += 1
            horus = _add_usage(horus, usage)
    return UsageSummary("claude", len(records), horus_turns, total, horus)


def claude_session_usage(
    session_id: str,
    project_root: Path,
    *,
    home: Path | None = None,
) -> tuple[int, TokenUsage] | None:
    root = project_root.resolve()
    records: dict[str, TokenUsage] = {}
    found_session = False
    for path in _claude_jsonl_files(home):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("sessionId") != session_id:
                continue
            found_session = True
            if not _event_matches_project(event, root):
                continue
            usage = _claude_token_usage(event)
            if usage is None:
                continue
            key = str(event.get("requestId") or event.get("uuid") or f"{path}:{len(records)}")
            records.setdefault(key, usage)
    if not found_session:
        return None
    total = TokenUsage()
    for usage in records.values():
        total = _add_usage(total, usage)
    return len(records), total


def session_usages(
    records: list[Any],
    *,
    codex_home: Path | None = None,
    claude_home: Path | None = None,
) -> list[SessionUsage]:
    out: list[SessionUsage] = []
    for rec in records:
        project = Path(rec.project)
        result: tuple[int, TokenUsage] | None
        note = ""
        if rec.agent == "codex":
            result = codex_session_usage(rec.session_id, project, home=codex_home)
            if result is None:
                note = "no matching Codex rollout session id"
        elif rec.agent == "claude":
            result = claude_session_usage(rec.session_id, project, home=claude_home)
            if result is None:
                note = "no matching Claude project log session id"
        else:
            result = None
            note = "unsupported agent"
        if result is None:
            out.append(SessionUsage(rec.session_id, rec.agent, rec.project, rec.status, 0, TokenUsage(), False, note))
        else:
            turns, total = result
            out.append(SessionUsage(rec.session_id, rec.agent, rec.project, rec.status, turns, total, True, note))
    return out


def baseline_comparison(
    without_horus: list[tuple[str, str]],
    with_horus: list[tuple[str, str]],
    project_root: Path,
    *,
    without_project_root: Path | None = None,
    with_project_root: Path | None = None,
    codex_home: Path | None = None,
    claude_home: Path | None = None,
) -> BaselineComparison:
    """Aggregate explicit A/B session ids without surfacing transcript content."""
    without_root = without_project_root or project_root
    with_root = with_project_root or project_root
    without_group = _baseline_group(
        "without Horus", without_horus, without_root, codex_home=codex_home, claude_home=claude_home
    )
    with_group = _baseline_group(
        "with Horus", with_horus, with_root, codex_home=codex_home, claude_home=claude_home
    )
    return BaselineComparison(
        without_group,
        with_group,
        _subtract_usage(with_group.total, without_group.total),
    )


def _baseline_group(
    label: str,
    specs: list[tuple[str, str]],
    project_root: Path,
    *,
    codex_home: Path | None,
    claude_home: Path | None,
) -> BaselineGroup:
    rows: list[BaselineSession] = []
    turns_total = 0
    usage_total = TokenUsage()
    for agent, session_id in specs:
        result: tuple[int, TokenUsage] | None
        if agent == "codex":
            result = codex_session_usage(session_id, project_root, home=codex_home)
            note = "no matching Codex rollout session id"
        elif agent == "claude":
            result = claude_session_usage(session_id, project_root, home=claude_home)
            note = "no matching Claude project log session id"
        else:
            result = None
            note = "unsupported agent"
        if result is None:
            rows.append(BaselineSession(session_id, agent, 0, TokenUsage(), False, note))
            continue
        turns, usage = result
        turns_total += turns
        usage_total = _add_usage(usage_total, usage)
        rows.append(BaselineSession(session_id, agent, turns, usage, True))
    return BaselineGroup(label, rows, turns_total, usage_total)


def _codex_rollouts(home: Path) -> list[Path]:
    sessions = home / "sessions"
    if not sessions.is_dir():
        return []
    files = [p for p in sessions.rglob("rollout-*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def _claude_jsonl_files(home: Path | None) -> list[Path]:
    base = home or Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    projects = base / "projects"
    if not projects.is_dir():
        return []
    return sorted(p for p in projects.rglob("*.jsonl") if p.is_file())


def _matches_project(payload: dict[str, Any], root: Path) -> bool:
    candidates: list[Path] = []
    cwd = payload.get("cwd")
    if isinstance(cwd, str):
        candidates.append(Path(cwd))
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        candidates.extend(Path(p) for p in roots if isinstance(p, str))
    for candidate in candidates:
        try:
            if candidate.resolve() == root:
                return True
        except OSError:
            continue
    return False


def _event_matches_project(event: dict[str, Any], root: Path) -> bool:
    cwd = event.get("cwd")
    if not isinstance(cwd, str):
        return False
    try:
        return Path(cwd).resolve() == root
    except OSError:
        return False


def _contains_horus_marker(value: Any) -> bool:
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":")).lower()
    except (TypeError, ValueError):
        text = str(value).lower()
    return any(marker in text for marker in _HORUS_MARKERS)


def _codex_token_usage(payload: Any) -> TokenUsage | None:
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    usage = info.get("last_token_usage")
    return _usage_from_mapping(usage) if isinstance(usage, dict) else None


def _claude_token_usage(event: dict[str, Any]) -> TokenUsage | None:
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    usage = message.get("usage")
    return _usage_from_mapping(usage) if isinstance(usage, dict) else None


def _usage_from_mapping(data: dict[str, Any]) -> TokenUsage:
    input_tokens = _int(data.get("input_tokens"))
    cached_input_tokens = _int(data.get("cached_input_tokens"))
    cache_creation_input_tokens = _int(data.get("cache_creation_input_tokens"))
    cache_read_input_tokens = _int(data.get("cache_read_input_tokens"))
    output_tokens = _int(data.get("output_tokens"))
    reasoning_output_tokens = _int(data.get("reasoning_output_tokens"))
    total_tokens = _int(data.get("total_tokens"))
    if total_tokens == 0:
        total_tokens = (
            input_tokens
            + cached_input_tokens
            + cache_creation_input_tokens
            + cache_read_input_tokens
            + output_tokens
            + reasoning_output_tokens
        )
    return TokenUsage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        output_tokens=output_tokens,
        reasoning_output_tokens=reasoning_output_tokens,
        total_tokens=total_tokens,
    )


def _int(value: Any) -> int:
    return value if isinstance(value, int) and value > 0 else 0


def _add_usage(a: TokenUsage, b: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=a.input_tokens + b.input_tokens,
        cached_input_tokens=a.cached_input_tokens + b.cached_input_tokens,
        cache_creation_input_tokens=a.cache_creation_input_tokens + b.cache_creation_input_tokens,
        cache_read_input_tokens=a.cache_read_input_tokens + b.cache_read_input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        reasoning_output_tokens=a.reasoning_output_tokens + b.reasoning_output_tokens,
        total_tokens=a.total_tokens + b.total_tokens,
    )


def _subtract_usage(a: TokenUsage, b: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=a.input_tokens - b.input_tokens,
        cached_input_tokens=a.cached_input_tokens - b.cached_input_tokens,
        cache_creation_input_tokens=a.cache_creation_input_tokens - b.cache_creation_input_tokens,
        cache_read_input_tokens=a.cache_read_input_tokens - b.cache_read_input_tokens,
        output_tokens=a.output_tokens - b.output_tokens,
        reasoning_output_tokens=a.reasoning_output_tokens - b.reasoning_output_tokens,
        total_tokens=a.total_tokens - b.total_tokens,
    )
