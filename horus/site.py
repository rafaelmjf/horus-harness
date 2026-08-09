"""`horus site build` — a static fleet page, sourced from remote.

The cockpit reads local clones, so it can only show projects checked out on the
machine you are at. This reads `.horus/` **from remote**, so it sees every project
whether or not it is cloned — which is the only thing this surface offers that the
cockpit does not, and therefore the only reason for it to exist.

Three properties follow from that, and each is load-bearing:

- **Static output, no runtime.** The page is a projection over committed files. A
  server would add a live dependency for data that only changes when someone pushes,
  and the previous hosted surface went unused partly because it was slow.
- **`pushedAt`-gated rebuilds.** One cheap list call answers "did anything change";
  content is re-read only for repos whose `pushedAt` moved. Freshness therefore
  costs one API call, not one per project.
- **Freshness on the face of it.** Every project carries the commit and the time it
  was read. A page that looks current while being stale is worse than one that
  admits its age — the published wiki sat six commits behind with nothing reporting
  it, and that is the failure this stamp exists to prevent.

The reader is here because the `.horus/` parsing already is. The *page* is a plain
static file and the same build writes `fleet.json` beside it, so a different
front-end can consume the data without touching any of this.
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

from horus import frontmatter, topics as topics_mod

_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}

TOPICS_PATH = ".horus/topics"
BACKLOG_PATH = ".horus/backlog"
INACTIVE = frozenset({"done", "folded-in", "retired", "shipped", "shelved"})

# A fetcher takes (full_name, path, ref) and returns file text, or a list of entry
# names for a directory, or None. Injected so the whole builder is testable offline.
Fetcher = Callable[[str, str, str], Any]


@dataclass(frozen=True)
class SiteTopic:
    name: str
    state: str
    priority: str
    problem: str
    solution: str


@dataclass(frozen=True)
class SiteCard:
    name: str
    topic: str
    status: str
    type: str
    summary: str


@dataclass
class SiteProject:
    name: str
    full_name: str
    url: str
    default_branch: str
    pushed_at: str
    vision: str = ""
    topics: list[SiteTopic] = field(default_factory=list)
    cards: list[SiteCard] = field(default_factory=list)
    read_at: str = ""
    error: str = ""


def gh_fetch(full_name: str, path: str, ref: str) -> Any:
    """Read a file's text or a directory's entry names from GitHub. None on any
    failure — a single unreadable repo must never take the whole build down."""
    try:
        result = subprocess.run(
            ["gh", "api", "--method", "GET", f"repos/{full_name}/contents/{path}", "-f", f"ref={ref}"],
            text=True, capture_output=True, check=False, **_NO_WINDOW,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout or "null")
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        return [str(e.get("name", "")) for e in data if e.get("type") == "file"]
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(str(data.get("content") or "")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _first_para(body: str, heading: str) -> str:
    import re
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    if not match:
        return ""
    for para in match.group(1).strip().split("\n\n"):
        cleaned = " ".join(para.split())
        if cleaned:
            return cleaned
    return ""


def _heading(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def read_project(project: SiteProject, fetch: Fetcher = gh_fetch) -> SiteProject:
    """Populate one project's topics and cards from remote. Partial data is kept:
    a repo with topics but an unreadable backlog still renders its topics."""
    ref = project.default_branch or "main"

    prd = fetch(project.full_name, ".horus/PRD.md", ref)
    if isinstance(prd, str):
        body = frontmatter.parse(prd).body
        for line in body.splitlines():
            cleaned = " ".join(line.split())
            if cleaned and not cleaned.startswith("#"):
                project.vision = cleaned[:150]
                break

    names = fetch(project.full_name, TOPICS_PATH, ref)
    for fname in sorted(names or []):
        if not fname.endswith(".md") or fname.lower() == "readme.md":
            continue
        text = fetch(project.full_name, f"{TOPICS_PATH}/{fname}", ref)
        if not isinstance(text, str):
            continue
        doc = frontmatter.parse(text)
        state = str(doc.front_matter.get("state", "")).strip().lower()
        project.topics.append(SiteTopic(
            name=fname[:-3],
            state=state if state in topics_mod.STATES else topics_mod.DEFAULT_STATE,
            priority=str(doc.front_matter.get("priority", "")).strip().lower() or "medium",
            problem=_first_para(doc.body, "The problem"),
            solution=_first_para(doc.body, "What we are building")
                     or _first_para(doc.body, "What was decided"),
        ))

    names = fetch(project.full_name, BACKLOG_PATH, ref)
    for fname in sorted(names or []):
        if not fname.endswith(".md") or fname.lower() == "readme.md":
            continue
        text = fetch(project.full_name, f"{BACKLOG_PATH}/{fname}", ref)
        if not isinstance(text, str):
            continue
        doc = frontmatter.parse(text)
        fm = doc.front_matter
        if str(fm.get("status", "open")).strip().lower() in INACTIVE:
            continue
        topic = str(fm.get("topic", "")).strip().strip("'\"")
        if not topic:
            continue
        readiness = str(fm.get("readiness", "")).strip().lower()
        heading = _heading(doc.body, fname[:-3])
        summary = heading.split("—", 1)[1].strip() if "—" in heading else heading
        project.cards.append(SiteCard(
            name=fname[:-3], topic=topic,
            status={"ready": "Ready", "shaping": "Shaping", "gated": "Gated",
                    "deferred": "Deferred"}.get(readiness, "Unsorted"),
            type=str(fm.get("type", "")).strip().lower() or "task",
            summary=summary[:180],
        ))
    return project


def needs_rebuild(project: SiteProject, previous: dict[str, Any] | None) -> bool:
    """True when this project's content must be re-read.

    The `pushedAt` short-circuit: unchanged means the repo has had no push since the
    last build, so its `.horus/` cannot have moved either. Missing or malformed prior
    state always rebuilds — guessing "unchanged" would serve stale data silently,
    which is the one outcome this surface must not produce.
    """
    if not previous:
        return True
    prior = previous.get("pushed_at")
    return not (prior and project.pushed_at and prior == project.pushed_at)


def to_json(projects: list[SiteProject], *, generated_at: str) -> str:
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "projects": [asdict(p) for p in projects],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def load_previous(out_dir: Path) -> dict[str, dict[str, Any]]:
    """Prior build's per-project state, keyed by full_name. Absent or unreadable →
    empty, which forces a full rebuild rather than trusting nothing."""
    path = out_dir / "fleet.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {p.get("full_name", ""): p for p in data.get("projects", []) if isinstance(p, dict)}
