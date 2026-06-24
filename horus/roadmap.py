"""Parse the roadmap checklist into tasks, progress, and the next actionable step.

The "next step" is derived deterministically from the roadmap: the first
in-progress (`[~]`) task, or else the first open (`[ ]`) task. This keeps the
dashboard's highlighted next step in sync with the roadmap with zero extra config.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# - [ ] todo / - [x] done / - [~] in-progress (also * bullets)
_TASK_RE = re.compile(r"^[-*]\s+\[([ xX~])\]\s+(.*)$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

_STATE = {" ": "todo", "x": "done", "X": "done", "~": "partial"}


class Task(NamedTuple):
    state: str  # "todo" | "done" | "partial"
    text: str
    section: str  # nearest preceding heading, or "" if none


class Progress(NamedTuple):
    done: int
    total: int

    @property
    def pct(self) -> int:
        return round(100 * self.done / self.total) if self.total else 0


def parse_tasks(roadmap_body: str) -> list[Task]:
    tasks: list[Task] = []
    section = ""
    for line in roadmap_body.splitlines():
        heading = _HEADING_RE.match(line.strip())
        if heading:
            section = heading.group(2).strip()
            continue
        m = _TASK_RE.match(line.strip())
        if m:
            tasks.append(Task(_STATE[m.group(1)], m.group(2).strip(), section))
    return tasks


def progress(tasks: list[Task]) -> Progress:
    return Progress(sum(1 for t in tasks if t.state == "done"), len(tasks))


def next_step(tasks: list[Task]) -> Task | None:
    """First in-progress task, else first open task, else None (all done/empty)."""
    for t in tasks:
        if t.state == "partial":
            return t
    for t in tasks:
        if t.state == "todo":
            return t
    return None
