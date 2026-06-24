"""Deterministically infer project state from existing files.

Most repos already describe themselves in a README, ROADMAP/TODO, a status file,
or CLAUDE.md/AGENTS.md. Rather than scaffolding `.horus/` from blank templates,
this module mines those files for a title, description, status, current focus,
and roadmap tasks. It is intentionally deterministic (no model calls) - richer,
fuzzier inference is a natural later job for the agent-execution layer.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import NamedTuple

from horus import frontmatter, instructions, roadmap

# Named files to mine, in rough priority order (first match wins for description).
_SOURCE_NAMES = [
    "STATUS.md",
    "PROJECT_STATUS.md",
    "PROJECT.md",
    "ROADMAP.md",
    "TODO.md",
    "TODOS.md",
    "PLAN.md",
    "README.md",
    "docs/README.md",
    "CLAUDE.md",
    "AGENTS.md",
]

# Top-level files whose names suggest status/roadmap content (discovered by glob,
# case-insensitive) so oddly-named files like PROJECT_STATUS.md or ROADMAP-2026.md
# are picked up too.
_GLOB_PATTERNS = ["*status*.md", "*roadmap*.md", "*todo*.md", "*plan*.md", "*backlog*.md"]

# Preference order for the one-paragraph description.
_DESCRIPTION_NAMES = [
    "README.md",
    "docs/README.md",
    "PROJECT.md",
    "PROJECT_STATUS.md",
    "STATUS.md",
    "CLAUDE.md",
    "AGENTS.md",
]

_MAX_TASKS = 40
_H1_RE = re.compile(r"^#\s+(.*)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_ROADMAP_SECTION_RE = re.compile(
    r"roadmap|to-?do|next|plan|milestone|backlog|tasks|upcoming|goals", re.I
)

# Status emoji used as checkbox-equivalents in many hand-written status docs.
# A bullet led by one of these is treated as a task with the mapped state.
_EMOJI_STATE = [
    ("✅", "done"), ("✔️", "done"), ("✔", "done"), ("☑️", "done"), ("☑", "done"),
    ("🟢", "done"), ("🟩", "done"),
    ("🚧", "partial"), ("🔄", "partial"), ("⏳", "partial"), ("🟡", "partial"), ("🟠", "partial"),
    ("⬜", "todo"), ("◻️", "todo"), ("◻", "todo"), ("🔲", "todo"), ("🟦", "todo"),
    ("🔴", "todo"), ("🟥", "todo"),
]


def _emoji_state(content: str):
    """If a bullet starts with a status emoji, return (state, text-without-emoji)."""
    for marker, state in _EMOJI_STATE:
        if content.startswith(marker):
            return state, content[len(marker):].lstrip(" :-—").strip()
    return None


class Inference(NamedTuple):
    title: str
    description: str
    status: str
    current_focus: str
    tasks: list  # list[roadmap.Task]
    sources: list  # list[str] of filenames mined

    def has_content(self) -> bool:
        return bool(self.description or self.tasks)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


def _strip_managed(text: str) -> str:
    block = instructions.extract_block(text)
    return text.replace(block.raw, "") if block.found else text


def _candidate_names(root: Path) -> list[str]:
    names: list[str] = [n for n in _SOURCE_NAMES if (root / n).is_file()]
    try:
        entries = sorted(root.iterdir())
    except OSError:
        entries = []
    for p in entries:
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        low = p.name.lower()
        if p.name not in names and any(fnmatch.fnmatch(low, pat) for pat in _GLOB_PATTERNS):
            names.append(p.name)
    return names


def gather_sources(root: Path) -> dict[str, str]:
    """Return {filename: text} for existing source files, with the Horus managed
    block stripped from instruction files so we never mine our own scaffold."""
    found: dict[str, str] = {}
    for name in _candidate_names(root):
        path = root / name
        if not path.is_file():
            continue
        text = _read(path)
        if name in ("CLAUDE.md", "AGENTS.md"):
            text = _strip_managed(text)
        if text.strip():
            found[name] = text
    return found


def _first_h1(text: str) -> str:
    for line in text.splitlines():
        m = _H1_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return ""


def _first_paragraph(text: str) -> str:
    body = frontmatter.parse(text).body
    para: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if para:
                break
            continue
        if s.startswith(("#", ">", "```", "<!--")) or _BULLET_RE.match(s):
            if para:
                break
            continue
        para.append(s)
    return " ".join(para)


def _extract_tasks(sources: dict[str, str]) -> list:
    tasks: list = []
    seen: set[str] = set()

    def add(state: str, text: str, section: str) -> None:
        key = text.lower()
        if text and key not in seen and len(tasks) < _MAX_TASKS:
            seen.add(key)
            tasks.append(roadmap.Task(state, text, section))

    for text in sources.values():
        # Explicit checkbox items anywhere in the file.
        for t in roadmap.parse_tasks(text):
            add(t.state, t.text, t.section)
        in_roadmap = False
        section = ""
        for line in text.splitlines():
            heading = _HEADING_RE.match(line.strip())
            if heading:
                section = heading.group(2).strip()
                in_roadmap = bool(_ROADMAP_SECTION_RE.search(section))
                continue
            bullet = _BULLET_RE.match(line.strip())
            if not bullet:
                continue
            content = bullet.group(1).strip()
            if content.startswith("["):  # checkbox, already captured above
                continue
            emoji = _emoji_state(content)
            if emoji:  # status-emoji bullet: capture anywhere, with mapped state
                add(emoji[0], emoji[1], section)
            elif in_roadmap:  # plain bullet under a roadmap/TODO-like heading
                add("todo", content, section)
    return tasks


def _infer_status(sources: dict[str, str]) -> str:
    for text in sources.values():
        m = re.search(r"^status:\s*(.+)$", text, re.I | re.M)
        if m:
            return m.group(1).strip().strip("\"'").split()[0].lower()
    return "active" if sources else "planning"


def _infer_focus(sources: dict[str, str], tasks: list) -> str:
    for text in sources.values():
        m = re.search(r"current[_ ]focus[\"']?\s*[:=]\s*(.+)", text, re.I)
        if m:
            return m.group(1).strip().strip("\"'").splitlines()[0][:200]
    ns = roadmap.next_step(tasks)
    return ns.text if ns else ""


def infer(root: Path) -> Inference:
    sources = gather_sources(root)

    title = ""
    for name in ("README.md", "docs/README.md", "PROJECT.md"):
        if name in sources:
            title = _first_h1(sources[name])
            if title:
                break
    title = title or root.name

    description = ""
    for name in _DESCRIPTION_NAMES:
        if name in sources:
            description = _first_paragraph(sources[name])
            if description:
                break

    tasks = _extract_tasks(sources)
    return Inference(
        title=title,
        description=description,
        status=_infer_status(sources),
        current_focus=_infer_focus(sources, tasks),
        tasks=tasks,
        sources=list(sources.keys()),
    )


def is_placeholder(path: Path) -> bool:
    """True if a `.horus/` file still looks like an untouched template."""
    if not path.is_file():
        return True
    text = path.read_text(encoding="utf-8")
    focus = frontmatter.parse(text).front_matter.get("current_focus", "")
    return (
        focus.strip().lower().startswith("describe ")
        or "One-paragraph description of what this project is." in text
        or "- [ ] First task." in text
    )
