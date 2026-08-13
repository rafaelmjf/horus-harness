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
