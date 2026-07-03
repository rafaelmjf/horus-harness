"""`.horus/` continuity model and the `horus doctor project` check."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from horus import frontmatter

HORUS_DIR = ".horus"
# Required lanes: a project's continuity is broken without these.
COMMITTED_FILES = ("project.md", "roadmap.md", "decisions.md")
# Structure-v2 lanes: recommended, warn-if-missing so pre-v2 repos migrate gently.
RECOMMENDED_FILES = ("features.md", "history.md")
SESSIONS_DIR = "sessions"
TEMP_DIR = "temp"


class Finding(NamedTuple):
    level: str  # "ok" | "warn" | "fail"
    message: str


def horus_dir(project_root: Path) -> Path:
    return project_root / HORUS_DIR


def recent_sessions(project_root: Path, limit: int = 5) -> list[Path]:
    sessions = horus_dir(project_root) / SESSIONS_DIR
    if not sessions.is_dir():
        return []
    # Sort newest-first by mtime (sessions/ is gitignored and local-only, so
    # mtime reliably reflects real creation/edit order), tie-broken by name.
    files = [
        p
        for p in sessions.glob("*.md")
        if p.is_file() and p.name.lower() != "readme.md"
    ]
    files.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return files[:limit]


def _check_focus(project_root: Path, source: str) -> list[Finding]:
    """current_focus health via the shared PRD-first resolver."""
    focus = frontmatter.resolve_focus(project_root).get("current_focus", "")
    if not focus:
        return [Finding("warn", f"{source}: no current_focus set")]
    if focus.lower().startswith("describe "):
        return [Finding("warn", f"{source}: current_focus still the placeholder")]
    return []


def _check_sessions(project_root: Path) -> list[Finding]:
    sessions_path = horus_dir(project_root) / SESSIONS_DIR
    if not sessions_path.is_dir():
        return [Finding("warn", f"no {HORUS_DIR}/{SESSIONS_DIR}/ directory")]
    recent = recent_sessions(project_root)
    if recent:
        return [
            Finding("ok", f"{len(recent)} recent session summary(ies); latest: {recent[0].name}")
        ]
    return [Finding("warn", "no session summaries yet")]


def check_project(project_root: Path) -> list[Finding]:
    """Inspect a project's `.horus/` continuity and return findings."""
    findings: list[Finding] = []
    hdir = horus_dir(project_root)

    if not hdir.is_dir():
        findings.append(
            Finding("fail", f"no {HORUS_DIR}/ directory (run `horus init`)")
        )
        return findings

    findings.append(Finding("ok", f"{HORUS_DIR}/ present"))

    # Structure v3 (PRD.md + sessions/): the six lanes are not required; the PRD
    # carries vision/backlog/shipped/rules and the focus fields live in its
    # frontmatter (transitional shims still win per-field via the resolver).
    prd = hdir / frontmatter.PRD_FILE
    if prd.is_file():
        if prd.read_text(encoding="utf-8").strip():
            findings.append(Finding("ok", f"{HORUS_DIR}/{frontmatter.PRD_FILE} present (structure v3)"))
        else:
            findings.append(Finding("warn", f"{HORUS_DIR}/{frontmatter.PRD_FILE} is empty"))
        findings.extend(_check_focus(project_root, frontmatter.PRD_FILE))
        findings.extend(_check_sessions(project_root))
        return findings

    for name in COMMITTED_FILES:
        path = hdir / name
        if not path.is_file():
            findings.append(Finding("fail", f"missing {HORUS_DIR}/{name}"))
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            findings.append(Finding("warn", f"{HORUS_DIR}/{name} is empty"))
        else:
            findings.append(Finding("ok", f"{HORUS_DIR}/{name} present"))

    for name in RECOMMENDED_FILES:
        path = hdir / name
        if not path.is_file():
            findings.append(
                Finding("warn", f"{HORUS_DIR}/{name} missing (structure v2; run `horus init` to scaffold)")
            )
        elif not path.read_text(encoding="utf-8").strip():
            findings.append(Finding("warn", f"{HORUS_DIR}/{name} is empty"))
        else:
            findings.append(Finding("ok", f"{HORUS_DIR}/{name} present"))

    # current_focus health, from project.md / roadmap.md front matter.
    for name in ("project.md", "roadmap.md"):
        path = hdir / name
        if not path.is_file():
            continue
        doc = frontmatter.parse(path.read_text(encoding="utf-8"))
        focus = doc.front_matter.get("current_focus", "").strip()
        if not focus:
            findings.append(Finding("warn", f"{name}: no current_focus set"))
        elif focus.lower().startswith("describe "):
            findings.append(
                Finding("warn", f"{name}: current_focus still the placeholder")
            )

    findings.extend(_check_sessions(project_root))

    return findings
