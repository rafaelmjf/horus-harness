"""Deterministic capture of local agent-session exhaust — phase 1 of the curator.

Reads Claude (`~/.claude/projects/*/*.jsonl`) and Codex
(`~/.codex/sessions/**/rollout-*.jsonl`) session stores plus every isolated
account under ``~/.horus/accounts/``, parses both record schemas, redacts
secrets, attributes each session to a project by its git remote (self-flagging
ambiguity rather than guessing), and writes a metadata skeleton manifest plus
redacted per-project bundles.

No LLM runs here. This is the factual foundation the batched curation pass
(phase 2) interprets. Raw output stays local — it holds secrets and is never
pushed.

Ported from the 2026-08-12 PoC (`horus-builder-poc/extract.py`); the
PoC-specific acceptance-leakage suppression was dropped.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from . import config

MAX_TURN_CHARS = 12_000

# Phase 2 (interpretation) shells out to the authenticated native CLI on a cheap
# tier — "horus's model routing" — rather than adding an inference dependency.
CURATION_MODEL_DEFAULT = "claude-haiku-4-5-20251001"
CURATION_INPUT_CAP = 120_000  # chars of bundle fed to the model per project

# Redaction runs on every captured turn. Each hit is counted so the manifest can
# report a scan result — a planted credential shows up as a nonzero count.
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(\buser\s*/\s*password\s*:\s*)[^\r\n]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(PGPASSWORD)(\s*[:=]\s*)[\"']?[^\s;\"']+[\"']?"), r"\1\2[REDACTED]"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{16,}"), r"\1 [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{16,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bntn_[A-Za-z0-9]{20,}\b"), "[REDACTED_NOTION_TOKEN]"),
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "[REDACTED_AWS_KEY]"),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|secret|password)"
            r"(\s*[:=]\s*)[\"']?[^\s,;\"']{8,}[\"']?"
        ),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"(?i)(https?://[^\s/:@]+:)[^\s/@]+(@)"), r"\1[REDACTED]\2"),
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


@dataclass
class Turn:
    role: str
    text: str
    timestamp: str | None


@dataclass
class Session:
    path: Path
    agent: str
    account: str
    source: str
    session_id: str
    project_path: str | None
    entrypoint: str
    surface: str
    content_hash: str
    secrets_redacted: int = 0
    turns: list[Turn] = field(default_factory=list)
    git_branches: list[str] = field(default_factory=list)
    ai_titles: list[str] = field(default_factory=list)
    last_prompts: list[str] = field(default_factory=list)

    @property
    def start(self) -> str | None:
        values = [t.timestamp for t in self.turns if t.timestamp]
        return min(values) if values else None

    @property
    def end(self) -> str | None:
        values = [t.timestamp for t in self.turns if t.timestamp]
        return max(values) if values else None


def redact(text: str) -> tuple[str, int]:
    """Return (redacted_text, hit_count). The count is the secret-scan signal."""
    text = text.replace("\x00", "")
    hits = 0
    for pattern, replacement in SECRET_PATTERNS:
        text, n = pattern.subn(replacement, text)
        hits += n
    return text, hits


def normalize_text(text: str) -> tuple[str, int]:
    text, hits = redact(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<system-reminder>[\s\S]*?</system-reminder>", "", text, flags=re.I)
    text = re.sub(r"<local-command-caveat>[\s\S]*?</local-command-caveat>", "", text, flags=re.I)
    for tag in (
        "environment_context", "recommended_plugins", "permissions instructions",
        "collaboration_mode", "apps_instructions", "plugins_instructions",
        "skills_instructions", "app-context", "INSTRUCTIONS",
    ):
        text = re.sub(rf"<{re.escape(tag)}(?:\s[^>]*)?>[\s\S]*?</{re.escape(tag)}>", "", text, flags=re.I)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip()
    if len(text) > MAX_TURN_CHARS:
        text = text[:MAX_TURN_CHARS] + f"\n[TURN TRUNCATED: {len(text) - MAX_TURN_CHARS} chars omitted]"
    return text, hits


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    pieces: list[str] = []
    for block in content:
        if isinstance(block, str):
            pieces.append(block)
            continue
        if not isinstance(block, dict):
            continue
        if str(block.get("type", "")) in {"text", "input_text", "output_text"} and isinstance(block.get("text"), str):
            pieces.append(block["text"])
        # Deliberately exclude tool_use, tool_result, thinking, images, machinery.
    return "\n".join(pieces)


def useful_turn(role: str, text: str) -> bool:
    if role not in {"user", "assistant"} or not text.strip():
        return False
    stripped = text.strip()
    if stripped.startswith("<system-reminder>") and stripped.endswith("</system-reminder>"):
        return False
    if stripped.startswith("<local-command-caveat>"):
        return False
    return True


def decode_claude_slug(slug: str) -> str | None:
    match = re.match(r"^([A-Za-z])--(.+)$", slug)
    if not match:
        return None
    drive, rest = match.groups()
    # Fallback only — explicit cwd fields win because '-' is lossy.
    return f"{drive.upper()}:\\" + rest.replace("-", "\\")


def dominant_path(paths: Iterable[str]) -> str | None:
    cleaned = [p.removeprefix("\\\\?\\") for p in paths if p]
    if not cleaned:
        return None
    return Counter(cleaned).most_common(1)[0][0]


def surface_for(entrypoint: str) -> str:
    return {"claude-desktop": "App", "cli": "CLI", "sdk-ts": "SDK"}.get(entrypoint, "SDK")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_claude(path: Path, account: str) -> Session | None:
    turns: list[Turn] = []
    cwd_values: list[str] = []
    session_id = path.stem
    git_branches: list[str] = []
    ai_titles: list[str] = []
    last_prompts: list[str] = []
    entrypoints: list[str] = []
    secrets = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(record.get("cwd"), str):
                cwd_values.append(record["cwd"])
            if isinstance(record.get("entrypoint"), str):
                entrypoints.append(record["entrypoint"])
            branch = record.get("gitBranch")
            if isinstance(branch, str) and branch and branch not in git_branches:
                git_branches.append(branch)
            if isinstance(record.get("sessionId"), str):
                session_id = record["sessionId"]
            record_type = record.get("type")
            if record_type == "custom-title" and isinstance(record.get("customTitle"), str):
                title, n = normalize_text(record["customTitle"])
                secrets += n
                if title and title not in ai_titles:
                    ai_titles.append(title)
            if record_type == "last-prompt" and isinstance(record.get("lastPrompt"), str):
                prompt, n = normalize_text(record["lastPrompt"])
                secrets += n
                if prompt and prompt not in last_prompts:
                    last_prompts.append(prompt)
            if record_type not in {"user", "assistant"}:
                continue
            message = record.get("message") if isinstance(record.get("message"), dict) else {}
            role = str(message.get("role") or record_type)
            text, n = normalize_text(content_text(message.get("content", record.get("content"))))
            secrets += n
            if useful_turn(role, text):
                if not turns or turns[-1].role != role or turns[-1].text != text:
                    turns.append(Turn(role, text, record.get("timestamp")))
    if not turns:
        return None
    project_path = dominant_path(cwd_values) or decode_claude_slug(path.parent.name)
    entrypoint = Counter(entrypoints).most_common(1)[0][0] if entrypoints else "cli"
    return Session(
        path=path, agent="claude", account=account, source="claude-jsonl",
        session_id=session_id, project_path=project_path, entrypoint=entrypoint,
        surface=surface_for(entrypoint), content_hash=hash_file(path),
        secrets_redacted=secrets, turns=turns, git_branches=git_branches,
        ai_titles=ai_titles, last_prompts=last_prompts,
    )


def parse_codex(path: Path, account: str) -> Session | None:
    turns: list[Turn] = []
    early_cwds: list[str] = []
    session_id = path.stem
    git_branches: list[str] = []
    secrets = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, line in enumerate(handle):
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            if record.get("type") == "session_meta":
                session_id = str(payload.get("id") or payload.get("session_id") or session_id)
                if isinstance(payload.get("cwd"), str):
                    early_cwds.append(payload["cwd"])
                git_payload = payload.get("git") if isinstance(payload.get("git"), dict) else {}
                if isinstance(git_payload.get("branch"), str) and git_payload["branch"] not in git_branches:
                    git_branches.append(git_payload["branch"])
            elif record.get("type") == "turn_context" and index < 250 and isinstance(payload.get("cwd"), str):
                early_cwds.append(payload["cwd"])
            if record.get("type") != "response_item" or payload.get("type") != "message":
                continue
            role = str(payload.get("role", ""))
            text, n = normalize_text(content_text(payload.get("content")))
            secrets += n
            if useful_turn(role, text):
                if not turns or turns[-1].role != role or turns[-1].text != text:
                    turns.append(Turn(role, text, record.get("timestamp")))
    if not turns:
        return None
    return Session(
        path=path, agent="codex", account=account, source="codex-rollout",
        session_id=session_id, project_path=dominant_path(early_cwds), entrypoint="cli",
        surface="CLI", content_hash=hash_file(path), secrets_redacted=secrets,
        turns=turns, git_branches=git_branches,
    )


def discover(home: Path | None = None) -> list[tuple[str, str, Path]]:
    home = home or Path.home()
    accounts = config.config_dir() / "accounts"
    found: list[tuple[str, str, Path]] = []
    for path in (home / ".claude" / "projects").glob("*/*.jsonl"):
        found.append(("claude", "claude-ambient", path))
    for account_dir in accounts.glob("claude-*"):
        for path in (account_dir / "projects").glob("*/*.jsonl"):
            found.append(("claude", account_dir.name, path))
    for path in (home / ".codex" / "sessions").glob("*/*/*/rollout-*.jsonl"):
        found.append(("codex", "codex-ambient", path))
    for account_dir in accounts.glob("codex-*"):
        sessions_dir = account_dir / "sessions"
        if sessions_dir.is_dir():
            for path in sessions_dir.rglob("*.jsonl"):
                found.append(("codex", account_dir.name, path))
    return sorted(set(found), key=lambda item: str(item[2]).lower())


def git_info(project_path: str | None) -> tuple[str | None, str | None]:
    if not project_path:
        return None, None
    path = Path(project_path)
    if not path.is_dir():
        return None, project_path  # moved/deleted checkout — flagged downstream
    try:
        remote = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            text=True, capture_output=True, timeout=3, check=False,
        )
        root = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            text=True, capture_output=True, timeout=3, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, str(path)
    return (remote.stdout.strip() or None), (root.stdout.strip() or str(path)).replace("/", "\\")


def project_name(path: str | None, remote: str | None) -> str:
    if remote:
        stem = remote.rstrip("/").rsplit("/", 1)[-1]
        if ":" in stem:
            stem = stem.rsplit(":", 1)[-1]
        return re.sub(r"\.git$", "", stem, flags=re.I) or "unnamed"
    if path:
        return Path(path).name or re.sub(r"[:\\/]+", "-", path)
    return "unattributed"


def safe_slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.").lower()
    return slug or "unattributed"


def iso_date(timestamp: str | None) -> str | None:
    return timestamp[:10] if timestamp else None


def attribution_flags(sessions: list[Session], git_cache: dict[str, tuple[str | None, str | None]]) -> list[str]:
    """Name every reason this project's attribution is uncertain — never guess silently."""
    flags: list[str] = []
    checkouts = {s.project_path for s in sessions if s.project_path}
    if len(checkouts) > 1:
        flags.append(f"merged checkout: {len(checkouts)} distinct paths collapsed by git remote")
    remotes = {git_cache.get(s.project_path or "", (None, None))[0] for s in sessions}
    remotes.discard(None)
    if len(remotes) > 1:
        flags.append(f"ambiguous remote: {len(remotes)} origins seen for one identity")
    for s in sessions:
        if s.project_path and not Path(s.project_path).is_dir():
            flags.append(f"moved/deleted checkout: {s.project_path} (session {s.session_id[:8]})")
    if not remotes and any(s.project_path for s in sessions):
        flags.append("no git remote — attributed by filesystem path, not remote")
    if any(s.project_path is None for s in sessions):
        flags.append("non-project session(s): no cwd recorded")
    return flags


def curate(out_dir: Path, home: Path | None = None) -> dict[str, Any]:
    """Run the full deterministic pass and write manifest + bundles under out_dir."""
    bundles = out_dir / "bundles"
    bundles.mkdir(parents=True, exist_ok=True)
    prior = _load_prior_hashes(out_dir)

    discovered = discover(home)
    sessions: list[Session] = []
    parse_errors: list[str] = []
    for agent, account, path in discovered:
        try:
            session = parse_claude(path, account) if agent == "claude" else parse_codex(path, account)
            if session:
                sessions.append(session)
        except Exception as exc:  # keep going, make the gap visible
            parse_errors.append(f"{path}: {type(exc).__name__}: {exc}")

    git_cache: dict[str, tuple[str | None, str | None]] = {}
    grouped: dict[str, list[Session]] = defaultdict(list)
    for session in sessions:
        key = session.project_path or ""
        if key not in git_cache:
            git_cache[key] = git_info(session.project_path)
        remote, _ = git_cache[key]
        identity = ("remote:" + remote.lower()) if remote else ("path:" + key.lower() if key else "unattributed")
        grouped[identity].append(session)

    projects: dict[str, dict[str, Any]] = {}
    used_slugs: set[str] = set()
    total_secrets = 0
    for _, project_sessions in sorted(grouped.items()):
        resolved = [git_cache.get(s.project_path or "", (None, s.project_path))[1] for s in project_sessions]
        path_counts = Counter(p for p in resolved if p)
        # Prefer the most recent live checkout; frequency alone promotes stale clones.
        path = next((p for p in reversed(resolved) if p and Path(p).is_dir()), None)
        path = path or (path_counts.most_common(1)[0][0] if path_counts else None)
        remote = next(
            (git_cache.get(s.project_path or "", (None, None))[0]
             for s in reversed(project_sessions) if git_cache.get(s.project_path or "", (None, None))[0]),
            None,
        )
        name = project_name(path, remote)
        slug = safe_slug(name)
        if slug in used_slugs:
            suffix = 2
            while f"{slug}-{suffix}" in used_slugs:
                suffix += 1
            slug = f"{slug}-{suffix}"
        used_slugs.add(slug)
        project_sessions.sort(key=lambda s: (s.start or "", str(s.path)))
        total_secrets += sum(s.secrets_redacted for s in project_sessions)

        bundle_path = bundles / f"{slug}.txt"
        with bundle_path.open("w", encoding="utf-8", newline="\n") as out:
            out.write(f"PROJECT: {name}\nPATH: {path or '(unattributed)'}\nREMOTE: {remote or '(none)'}\n")
            out.write("NOTE: filtered natural-language turns only; tool payloads removed; secrets redacted.\n\n")
            for s in project_sessions:
                out.write(
                    f"=== SESSION {s.session_id} | {s.agent}/{s.account} | {s.surface}/{s.entrypoint} | "
                    f"{s.start or '?'} to {s.end or '?'} | {len(s.turns)} turns ===\n"
                )
                for turn in s.turns:
                    out.write(f"\n[{turn.timestamp or '?'}] {turn.role.upper()}\n{turn.text}\n")
                out.write("\n")

        starts = [s.start for s in project_sessions if s.start]
        ends = [s.end for s in project_sessions if s.end]
        projects[slug] = {
            "name": name,
            "path": path,
            "git_remote": remote,
            "has_horus": bool(path and (Path(path) / ".horus").is_dir()),
            "session_count": len(project_sessions),
            "turn_count": sum(len(s.turns) for s in project_sessions),
            "secrets_redacted": sum(s.secrets_redacted for s in project_sessions),
            "date_start": iso_date(min(starts)) if starts else None,
            "date_end": iso_date(max(ends)) if ends else None,
            "agents": sorted({s.agent for s in project_sessions}),
            "accounts": sorted({s.account for s in project_sessions}),
            "attribution_flags": attribution_flags(project_sessions, git_cache),
            "bundle": str(bundle_path.relative_to(out_dir)).replace("\\", "/"),
            "sessions": [
                {
                    "id": s.session_id,
                    "source_path": str(s.path),
                    "agent": s.agent,
                    "account": s.account,
                    "surface": s.surface,
                    "entrypoint": s.entrypoint,
                    "start": s.start,
                    "end": s.end,
                    "turns": len(s.turns),
                    "checkout_path": s.project_path,
                    "git_branch": " -> ".join(s.git_branches) if s.git_branches else None,
                    "ai_titles": s.ai_titles,
                    "last_prompts": s.last_prompts,
                    "content_hash": s.content_hash,
                    # Watermark: unchanged sessions can be skipped by the LLM pass.
                    "changed": prior.get(str(s.path)) != s.content_hash,
                }
                for s in project_sessions
            ],
        }

    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_files_discovered": len(discovered),
        "sessions_processed": len(sessions),
        "projects_found": len(projects),
        "secrets_redacted": total_secrets,
        "parse_errors": parse_errors,
        "projects": projects,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def _load_prior_hashes(out_dir: Path) -> dict[str, str]:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {
        s["source_path"]: s.get("content_hash", "")
        for project in data.get("projects", {}).values()
        for s in project.get("sessions", [])
        if s.get("source_path")
    }


def default_out_dir() -> Path:
    return config.config_dir() / "curate"


# --- Phase 2: batched LLM curation ------------------------------------------

CURATION_PROMPT = """\
You are curating one project's agent-session history into a durable ledger entry.
Below is the filtered, secret-redacted transcript for project "{name}" — natural-language
turns only, tool output removed, grouped by session with headers.

Write a concise Markdown ledger entry with exactly these sections:

## Context
2-3 lines: what this project is and what these sessions were working on.

## Segments
One bullet per distinct work segment (segment by git branch or topic, NOT by session —
a long multi-branch session yields several segments; a short one yields one). Each bullet:
`**<branch or topic>** — what happened, 1-2 sentences.` Keep it proportional to the work.

## Discussed / Decided / Shipped / Open
Four short subsections (`### Discussed`, `### Decided`, `### Shipped`, `### Open`),
bullets only, omit a subsection if genuinely empty. "Shipped" = merged/delivered;
"Open" = unresolved next steps.

Be specific and factual. Do not invent. Output only the Markdown, no preamble.

---
{bundle}
"""


def run_model(
    prompt: str,
    *,
    model: str,
    account: str | None = None,
    executable: str = "claude",
    timeout: int = 300,
) -> str:
    """One-shot headless call to the native CLI; returns its text response.

    Routes through the account's isolated ``CLAUDE_CONFIG_DIR`` when mapped —
    the same routing ``horus run`` uses — so no inference dependency is added.
    """
    exe = shutil.which(executable) or executable  # honor PATHEXT on Windows
    env = os.environ.copy()
    cfg = config.load_account_config_dirs().get(account) if account else None
    if cfg:
        env["CLAUDE_CONFIG_DIR"] = str(Path(cfg))
    proc = subprocess.run(
        [exe, "-p", prompt, "--model", model],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, env=env, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"{executable} -p exited {proc.returncode}")
    return proc.stdout.strip()


def _curation_state_path(out_dir: Path) -> Path:
    return out_dir / "curation" / "state.json"


def _load_curation_state(out_dir: Path) -> dict[str, list[str]]:
    path = _curation_state_path(out_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def interpret(
    out_dir: Path,
    *,
    manifest: dict[str, Any],
    model: str = CURATION_MODEL_DEFAULT,
    account: str | None = None,
    only_project: str | None = None,
    force: bool = False,
    runner: Callable[..., str] = run_model,
) -> dict[str, Any]:
    """Curate changed projects into ``curation/<slug>.md``. Unchanged projects are
    skipped via the content-hash watermark unless ``force``. ``runner`` is injectable
    so tests never spend tokens."""
    curation_dir = out_dir / "curation"
    curation_dir.mkdir(parents=True, exist_ok=True)
    state = _load_curation_state(out_dir)
    result = {"curated": [], "skipped": [], "errors": []}

    for slug, project in sorted(manifest["projects"].items()):
        if only_project and slug != only_project:
            continue
        hashes = sorted(s["content_hash"] for s in project["sessions"])
        md_path = curation_dir / f"{slug}.md"
        if not force and md_path.exists() and state.get(slug) == hashes:
            result["skipped"].append(slug)
            continue
        bundle = (out_dir / project["bundle"]).read_text(encoding="utf-8")
        if len(bundle) > CURATION_INPUT_CAP:
            bundle = bundle[:CURATION_INPUT_CAP] + "\n[BUNDLE TRUNCATED for curation]"
        prompt = CURATION_PROMPT.format(name=project["name"], bundle=bundle)
        try:
            text = runner(prompt, model=model, account=account)
        except Exception as exc:
            result["errors"].append(f"{slug}: {type(exc).__name__}: {exc}")
            continue
        md_path.write_text(text.rstrip() + "\n", encoding="utf-8")
        state[slug] = hashes
        result["curated"].append(slug)

    _curation_state_path(out_dir).write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


# --- Phase 3: the portfolio git-of-record -----------------------------------

# The skeleton is per-project metadata only — never raw turn text. These are the
# manifest fields safe to push; the bundle stays local.
_SKELETON_PROJECT_KEYS = (
    "name", "path", "git_remote", "has_horus", "session_count", "turn_count",
    "secrets_redacted", "date_start", "date_end", "agents", "accounts",
    "attribution_flags",
)
_SKELETON_SESSION_KEYS = (
    "id", "agent", "account", "surface", "entrypoint", "start", "end", "turns",
    "checkout_path", "git_branch", "content_hash",
)


def default_portfolio_dir() -> Path:
    return config.config_dir() / "portfolio"


# Sumi-e static view: warm paper, ink tones, one seal. Self-contained, no network
# (CSP blocks everything), data embedded as JSON. Regenerated from the manifest +
# curation each run — no hand-curated maps.
_PORTFOLIO_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'none'; font-src 'none'; connect-src 'none'">
<title>Session Portfolio — unified agent history</title>
<style>
:root{color-scheme:light dark;
--paper:#FBFAF7;--paper-2:#F2F0EB;--panel:#EDEAE3;--ink:#121110;--ink-2:#3A3835;
--ink-3:#6B6862;--ink-4:#8A867E;--line:#DCD8CF;--seal:#C0342A;--seal-wash:rgba(192,52,42,.07);
--radius:12px;}
@media (prefers-color-scheme:dark){:root{
--paper:#0E0E0D;--paper-2:#151513;--panel:#232220;--ink:#F4F1EA;--ink-2:#C6C2B9;
--ink-3:#918D85;--ink-4:#7A766F;--line:#2C2A27;--seal:#D8483C;--seal-wash:rgba(216,72,60,.12);}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Georgia,"Iowan Old Style",serif}
button,select{font:inherit;color:var(--ink);background:var(--paper);border:1px solid var(--line)}
button{cursor:pointer}
.shell{width:min(1500px,100%);margin:0 auto;padding:32px 28px}
header{margin-bottom:20px}
h1{font-weight:normal;font-size:clamp(26px,4vw,40px);letter-spacing:.01em;margin:0 0 8px}
.lede{margin:0;color:var(--ink-3);max-width:760px}
.stats{display:flex;flex-wrap:wrap;gap:20px;margin-top:16px}
.stat strong{display:block;font-size:22px}.stat span{color:var(--ink-4);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.toolbar{position:sticky;top:0;z-index:5;background:var(--paper);border-block:1px solid var(--line);padding:12px 0;margin:8px 0 18px}
.toolbar-row{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center}.toolbar-row+.toolbar-row{margin-top:8px}
.group{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.group-label{color:var(--ink-4);font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:.08em}
.toggle,.view-tab{border-radius:999px;padding:6px 12px}
.toggle[aria-pressed=true],.view-tab[aria-selected=true]{border-color:var(--seal);background:var(--seal-wash);color:var(--seal)}
select{border-radius:8px;padding:6px 9px;max-width:320px}
.badge{display:inline-flex;align-items:center;border-radius:999px;padding:2px 9px;color:#fff;font-size:11px;white-space:nowrap}
.main-layout{display:grid;grid-template-columns:minmax(320px,42%) minmax(0,1fr);gap:18px;align-items:start}
.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.section-head h2{margin:0;font-size:17px;font-weight:normal}.count{color:var(--ink-4);font-size:12px}
.project-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.project-card{width:100%;text-align:left;padding:14px;border-radius:var(--radius);background:var(--paper-2);min-height:120px}
.project-card:hover{border-color:var(--seal)}.project-card.active{border-color:var(--seal);box-shadow:inset 0 0 0 1px var(--seal)}
.project-name{display:block;font-size:15px;font-weight:bold;margin-bottom:5px;overflow-wrap:anywhere}
.project-path{display:block;color:var(--ink-4);font:11px/1.35 ui-monospace,Consolas,monospace;overflow-wrap:anywhere;min-height:28px}
.card-meta,.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.chip{border:1px solid var(--line);border-radius:999px;padding:2px 8px;font-size:11px;color:var(--ink-3);background:var(--panel)}
.chip.horus{color:var(--seal);border-color:var(--seal)}
.chip.flag{color:var(--seal);background:var(--seal-wash);border-color:var(--seal)}
.detail,.timeline-pane{background:var(--paper-2);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.detail{position:sticky;top:120px;max-height:calc(100vh-140px);overflow:auto}
.detail-head,.timeline-head{padding:17px 18px;border-bottom:1px solid var(--line)}
.detail-head h2,.timeline-head h2{margin:0 0 5px;font-size:19px;font-weight:normal;overflow-wrap:anywhere}
.detail-meta{color:var(--ink-4);font-size:12px;overflow-wrap:anywhere}
.curation{padding:16px 18px;border-bottom:1px solid var(--line);white-space:pre-wrap;font-size:13px;color:var(--ink-2)}
.curation.empty{color:var(--ink-4);font-style:italic}
.session-list{list-style:none;margin:0;padding:0}
.session{display:grid;grid-template-columns:130px minmax(0,1fr);gap:14px;padding:15px 18px;border-bottom:1px solid var(--line)}
.session:last-child{border-bottom:0}.session-time{color:var(--ink-4);font-size:12px}.session-side .badge{margin-top:6px}
.session-project{display:block;color:var(--seal);font-weight:bold;margin-bottom:6px;overflow-wrap:anywhere}
.topic{margin-bottom:8px}
.session-facts{display:grid;grid-template-columns:auto minmax(0,1fr);gap:3px 8px;color:var(--ink-4);font-size:12px}
.session-facts dt{font-weight:bold}.session-facts dd{margin:0;min-width:0;overflow-wrap:anywhere}
code{font:11px/1.35 ui-monospace,Consolas,monospace;background:var(--panel);border-radius:4px;padding:1px 4px}
.empty{padding:32px;text-align:center;color:var(--ink-4)}.hidden{display:none!important}
footer{color:var(--ink-4);font-size:12px;padding:28px 0 6px;text-align:center}
@media(max-width:1050px){.main-layout{grid-template-columns:1fr}.detail{position:static;max-height:none}}
@media(max-width:680px){.shell{padding:18px 14px}.project-grid{grid-template-columns:1fr}.toolbar{position:static}.session{grid-template-columns:1fr;gap:7px}}
</style>
</head>
<body>
<div class="shell">
<header>
<h1>Session portfolio</h1>
<p class="lede">Every local coding session on this machine — the Claude app, the Claude CLI, and Codex, under all accounts — distilled into one browsable history. No app owns it; any agent can read it.</p>
<div class="stats" id="stats"></div>
</header>
<div class="toolbar" aria-label="Portfolio controls">
<div class="toolbar-row">
<div class="group" role="tablist" aria-label="View"><span class="group-label">View</span>
<button class="view-tab" data-view="projects" role="tab" aria-selected="true">By project</button>
<button class="view-tab" data-view="timeline" role="tab" aria-selected="false">Timeline</button></div>
<div class="group" id="sort-group"><label class="group-label" for="sort">Sort</label>
<select id="sort"><option value="activity">Activity</option><option value="recency">Recency</option><option value="name">Name</option></select></div>
</div>
<div class="toolbar-row">
<div class="group" id="account-filters"><span class="group-label">Accounts</span></div>
<div class="group" id="agent-filters"><span class="group-label">Agents</span></div>
</div>
</div>
<main>
<section id="project-view" class="main-layout">
<div><div class="section-head"><h2>Projects</h2><span class="count" id="project-count"></span></div>
<div class="project-grid" id="project-grid"></div></div>
<aside class="detail" id="project-detail" aria-live="polite"></aside>
</section>
<section id="timeline-view" class="timeline-pane hidden">
<div class="timeline-head"><h2>Unified timeline</h2><div class="detail-meta" id="timeline-count"></div></div>
<ol class="session-list" id="global-timeline"></ol>
</section>
</main>
<footer>Self-contained UTF-8 artifact · no network · curated summaries + metadata only · no raw transcripts</footer>
</div>
<script id="portfolio-data" type="application/json">__DATA__</script>
<script>
(()=>{'use strict';
const data=JSON.parse(document.getElementById('portfolio-data').textContent);
const projects=data.projects, sessions=data.sessions;
const projectById=new Map(projects.map(p=>[p.id,p]));
const PALETTE=['#C0342A','#2F6E5B','#7A5AA6','#B4702A','#3B6EA5','#8A867E'];
const accountColor=new Map(data.summary.accounts.map((a,i)=>[a,PALETTE[i%PALETTE.length]]));
const state={view:'projects',selected:projects.length?projects[0].id:null,sort:'activity',
accounts:new Set(data.summary.accounts),agents:new Set(data.summary.agents)};
const el=id=>document.getElementById(id);
const fmtDate=iso=>iso?new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:'UTC'}).format(new Date(iso)):'?';
const shortDate=iso=>iso?new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'2-digit',timeZone:'UTC'}).format(new Date(iso)):'?';
const make=(t,c,x)=>{const n=document.createElement(t);if(c)n.className=c;if(x!==undefined)n.textContent=x;return n;};
const badge=a=>{const b=make('span','badge',a);b.style.background=accountColor.get(a)||'#8A867E';return b;};
const passes=s=>state.accounts.has(s.account)&&state.agents.has(s.agent);
const cardSessions=p=>sessions.filter(s=>s.project===p.id&&passes(s));
function renderStats(){
const items=[[data.summary.projects,'projects'],[data.summary.sessions,'sessions'],
[data.summary.accounts.length,'accounts'],[`${shortDate(data.summary.dateStart)} – ${shortDate(data.summary.dateEnd)}`,'span']];
el('stats').replaceChildren(...items.map(([v,l])=>{const d=make('div','stat');d.append(make('strong','',String(v)),make('span','',l));return d;}));}
function renderControls(){
el('sort').addEventListener('change',e=>{state.sort=e.target.value;renderProjects();});
for(const a of data.summary.accounts){const b=make('button','toggle',a);b.setAttribute('aria-pressed','true');
b.addEventListener('click',()=>{state.accounts.has(a)?state.accounts.delete(a):state.accounts.add(a);b.setAttribute('aria-pressed',String(state.accounts.has(a)));render();});
el('account-filters').append(b);}
for(const g of data.summary.agents){const b=make('button','toggle',g);b.setAttribute('aria-pressed','true');
b.addEventListener('click',()=>{state.agents.has(g)?state.agents.delete(g):state.agents.add(g);b.setAttribute('aria-pressed',String(state.agents.has(g)));render();});
el('agent-filters').append(b);}
document.querySelectorAll('.view-tab').forEach(b=>b.addEventListener('click',()=>{state.view=b.dataset.view;render();}));}
function renderProjectCard(p){
const visible=cardSessions(p);
const card=make('button',`project-card${p.id===state.selected?' active':''}`);card.type='button';
card.append(make('span','project-name',p.name),make('span','project-path',p.path));
const meta=make('span','card-meta');
meta.append(make('span','chip',`${visible.length}/${p.sessionCount} sessions`));
if(p.curation)meta.append(make('span','chip','curated'));
if(p.hasHorus)meta.append(make('span','chip horus','.horus'));
card.append(meta);
if(p.flags.length){const c=make('span','chips');p.flags.forEach(f=>c.append(make('span','chip flag',f.split(':')[0])));card.append(c);}
card.addEventListener('click',()=>{state.selected=p.id;renderProjects();});
return card;}
function renderProjects(){
let visible=projects.filter(p=>cardSessions(p).length);
const sorters={activity:(a,b)=>cardSessions(b).length-cardSessions(a).length||b.turns-a.turns,
recency:(a,b)=>(b.dateEnd||'').localeCompare(a.dateEnd||''),name:(a,b)=>a.name.localeCompare(b.name)};
visible.sort(sorters[state.sort]);
if(visible.length&&!visible.some(p=>p.id===state.selected))state.selected=visible[0].id;
el('project-grid').replaceChildren(...visible.map(renderProjectCard));
el('project-count').textContent=`${visible.length} of ${projects.length}`;
const sel=projectById.get(state.selected),detail=el('project-detail');detail.replaceChildren();
if(!sel||!visible.length){detail.append(make('div','empty','No projects match the active filters.'));return;}
const list=cardSessions(sel);
const head=make('div','detail-head');head.append(make('h2','',sel.name));
head.append(make('div','detail-meta',`${list.length} of ${sel.sessionCount} sessions · ${sel.remote||'no git remote resolved'}`));
detail.append(head);
detail.append(make('div',sel.curation?'curation':'curation empty',sel.curation||'Not yet curated — run horus curate --interpret.'));
detail.append(renderSessionList(list,false));}
function renderSession(s,showProject){
const li=make('li','session');
const side=make('div','session-side');side.append(make('time','session-time',fmtDate(s.start)),badge(s.account));
const body=make('div','session-body');
if(showProject)body.append(make('span','session-project',projectById.get(s.project).name));
body.append(make('div','topic',s.topic));
const facts=make('dl','session-facts');
[['Agent',s.agent],['Surface',s.surface||'?'],['Branch',s.branch],['Turns',String(s.turns)],['Checkout',s.checkout]]
.forEach(([k,v])=>{facts.append(make('dt','',k));const dd=make('dd');(k==='Branch'||k==='Checkout')?dd.append(make('code','',v)):dd.textContent=v;facts.append(dd);});
body.append(facts);li.append(side,body);return li;}
function renderSessionList(list,showProject){const ol=make('ol','session-list');
list.length?list.forEach(s=>ol.append(renderSession(s,showProject))):ol.append(make('li','empty','No sessions match the active filters.'));return ol;}
function renderTimeline(){
const list=sessions.filter(passes);el('timeline-count').textContent=`${list.length} of ${sessions.length} sessions · oldest first`;
el('global-timeline').replaceChildren(...(list.length?list.map(s=>renderSession(s,true)):[make('li','empty','No sessions match.')]));}
function render(){
document.querySelectorAll('.view-tab').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.view===state.view)));
el('project-view').classList.toggle('hidden',state.view!=='projects');
el('timeline-view').classList.toggle('hidden',state.view!=='timeline');
el('sort-group').classList.toggle('hidden',state.view!=='projects');
renderProjects();renderTimeline();}
renderStats();renderControls();render();
})();
</script>
</body>
</html>'''


def _skeleton_for(project: dict[str, Any]) -> dict[str, Any]:
    skel = {k: project.get(k) for k in _SKELETON_PROJECT_KEYS}
    skel["sessions"] = [{k: s.get(k) for k in _SKELETON_SESSION_KEYS} for s in project["sessions"]]
    return skel


def _git(portfolio_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(portfolio_dir), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )


def _portfolio_index_md(projects: list[tuple[str, dict[str, Any]]]) -> str:
    lines = ["# Portfolio ledger", "",
             f"Regenerated {datetime.now().astimezone().isoformat(timespec='seconds')}. "
             "Derived from local session stores — each project's own `.horus/` stays authoritative.",
             "",
             "| Project | Dates | Sessions | Agents | Accounts | Flags |",
             "|---|---|---|---|---|---|"]
    for slug, p in projects:
        span = f"{p['date_start'] or '?'} → {p['date_end'] or '?'}"
        flags = "⚠︎" if p["attribution_flags"] else ""
        lines.append(
            f"| [{p['name']}](projects/{slug}/curation.md) | {span} | {p['session_count']} | "
            f"{', '.join(p['agents'])} | {', '.join(p['accounts'])} | {flags} |"
        )
    return "\n".join(lines) + "\n"


def _session_topic(session: dict[str, Any]) -> str:
    """A one-line label for a session in the view — best available signal."""
    for key in ("ai_titles", "last_prompts"):
        vals = session.get(key) or []
        if vals:
            text = re.sub(r"\s+", " ", vals[0]).strip()
            return text[:140] + ("…" if len(text) > 140 else "")
    branch = session.get("git_branch")
    return f"branch {branch}" if branch else "session"


def _portfolio_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    projects, sessions = [], []
    for slug, p in sorted(manifest["projects"].items()):
        curated = p.get("_curation")
        projects.append({
            "id": slug, "name": p["name"], "path": p.get("path") or "unattributed",
            "remote": p.get("git_remote"), "hasHorus": bool(p.get("has_horus")),
            "flags": p.get("attribution_flags", []), "curation": curated,
            "sessionCount": p["session_count"], "turns": p["turn_count"],
            "dateStart": p.get("date_start"), "dateEnd": p.get("date_end"),
        })
        for s in p["sessions"]:
            sessions.append({
                "id": s["id"], "project": slug, "account": s["account"], "agent": s["agent"],
                "surface": s.get("surface"), "start": s.get("start"), "end": s.get("end"),
                "branch": s.get("git_branch") or "not recorded", "turns": s["turns"],
                "checkout": s.get("checkout_path") or p.get("path") or "not attributed",
                "topic": _session_topic(s),
            })
    sessions.sort(key=lambda s: s["start"] or "")
    dated = [s["start"] for s in sessions if s["start"]]
    return {
        "summary": {
            "projects": len(projects), "sessions": len(sessions),
            "accounts": sorted({s["account"] for s in sessions}),
            "agents": sorted({s["agent"] for s in sessions}),
            "dateStart": min(dated) if dated else None,
            "dateEnd": max(dated) if dated else None,
        },
        "projects": projects, "sessions": sessions,
    }


def render_portfolio_html(manifest: dict[str, Any], curation_dir: Path) -> str:
    """Self-contained sumi-e static view, regenerated from the curator's own data."""
    payload = _portfolio_payload_with_curation(manifest, curation_dir)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return _PORTFOLIO_TEMPLATE.replace("__DATA__", encoded)


def _portfolio_payload_with_curation(manifest: dict[str, Any], curation_dir: Path) -> dict[str, Any]:
    for slug, p in manifest["projects"].items():
        md = curation_dir / f"{slug}.md"
        p["_curation"] = md.read_text(encoding="utf-8") if md.exists() else None
    return _portfolio_payload(manifest)


def assemble_portfolio(
    out_dir: Path,
    portfolio_dir: Path,
    *,
    manifest: dict[str, Any],
    push: bool = False,
) -> dict[str, Any]:
    """Assemble the portfolio git-of-record from curated output. Copies curation +
    skeleton only — raw bundles never enter the portfolio. Idempotent/regeneratable:
    re-running reproduces the same tree."""
    projects = sorted(manifest["projects"].items())
    proj_root = portfolio_dir / "projects"
    proj_root.mkdir(parents=True, exist_ok=True)

    curation_dir = out_dir / "curation"
    written = 0
    for slug, project in projects:
        dest = proj_root / slug
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "skeleton.json").write_text(
            json.dumps(_skeleton_for(project), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        src_md = curation_dir / f"{slug}.md"
        if src_md.exists():
            (dest / "curation.md").write_text(src_md.read_text(encoding="utf-8"), encoding="utf-8")
            written += 1

    (portfolio_dir / "index.md").write_text(_portfolio_index_md(projects), encoding="utf-8")
    (portfolio_dir / "index.html").write_text(
        render_portfolio_html(manifest, curation_dir), encoding="utf-8"
    )
    # Belt-and-braces: raw bundles must never be tracked here.
    (portfolio_dir / ".gitignore").write_text("bundles/\n*.bundle\n", encoding="utf-8")

    result = {"projects": len(projects), "curations": written, "pushed": False, "git": None}
    if not (portfolio_dir / ".git").is_dir():
        _git(portfolio_dir, "init", "-q")
    # The portfolio is horus-owned; give it a local identity when the environment
    # has none (fresh CI, no global git config) so the commit never fails.
    if not _git(portfolio_dir, "config", "user.email").stdout.strip():
        _git(portfolio_dir, "config", "user.email", "curator@horus.local")
        _git(portfolio_dir, "config", "user.name", "Horus Curator")
    _git(portfolio_dir, "add", "-A")
    status = _git(portfolio_dir, "status", "--porcelain")
    if status.stdout.strip():
        commit = _git(portfolio_dir, "commit", "-q", "-m",
                      f"portfolio: {len(projects)} projects, {written} curated "
                      f"({datetime.now().astimezone().date()})")
        result["git"] = "committed" if commit.returncode == 0 else commit.stderr.strip()
    else:
        result["git"] = "no changes"

    if push:
        remotes = _git(portfolio_dir, "remote")
        if "origin" in remotes.stdout.split():
            pushed = _git(portfolio_dir, "push", "origin", "HEAD")
            result["pushed"] = pushed.returncode == 0
            if pushed.returncode != 0:
                result["push_error"] = pushed.stderr.strip()
        else:
            result["push_error"] = (
                "no 'origin' remote set — create a private repo and "
                f"`git -C {portfolio_dir} remote add origin <url>` first"
            )
    return result
