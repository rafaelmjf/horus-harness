"""`.horus/topics/` — groupings of work that state their own purpose.

A **topic** answers "why are we doing any of this", which a card cannot: a card is
one piece of work, and a pile of cards is a pile of fragments. A topic file states
the problem being solved and what the finished thing should look like, in prose a
reader with no project context can follow, and member cards point at it with a
`topic:` frontmatter key.

Two properties are deliberate:

- **Topics live outside `backlog/`.** They therefore cannot land in a readiness
  queue, cannot trip the Unclassified gate, and cannot be mistaken for
  dispatchable work — by construction rather than by special-casing every reader.
  Only member cards are ever dispatchable.
- **A topic may have no members.** Either the direction is stated but not yet
  broken into pieces (`state: open`), or a question was answered and no work
  follows (`state: settled`). Those look identical from a card count, so the
  state is recorded rather than inferred.

This module is additive: `vision_facet` and the facet convergence read-out are
untouched, so a project that never creates a topic behaves exactly as before.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from horus import frontmatter
from horus.continuity import Finding

TOPICS_DIRNAME = "topics"
TOPIC_FIELD = "topic"

STATE_OPEN = "open"
STATE_SETTLED = "settled"
STATES: tuple[str, ...] = (STATE_OPEN, STATE_SETTLED)
DEFAULT_STATE = STATE_OPEN

# Display order for a topic list; anything unrecognized sorts after these.
PRIORITY_ORDER: tuple[str, ...] = ("now", "next", "high", "medium", "low")

_PURPOSE_RE = re.compile(r"^##\s+The problem\s*$(.*?)(?=^##\s|\Z)", re.M | re.S)


def topics_dir(project_root: Path) -> Path:
    return project_root / ".horus" / TOPICS_DIRNAME


@dataclass(frozen=True)
class Topic:
    path: Path
    name: str          # filename stem — the identifier member cards reference
    title: str         # first `# ` heading, or the stem
    state: str         # "open" | "settled"
    priority: str
    purpose: str       # first paragraph under `## The problem`, "" when absent


def _title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def _purpose(body: str) -> str:
    """The opening paragraph of `## The problem` — the one line a topic list shows.

    Best-effort by design: a topic whose body does not use that heading still loads,
    it just has no summary to display. Never raises, never guesses from other text.
    """
    match = _PURPOSE_RE.search(body)
    if not match:
        return ""
    for para in match.group(1).strip().split("\n\n"):
        cleaned = " ".join(para.split())
        if cleaned:
            return cleaned
    return ""


def _topic_from_path(path: Path) -> Topic | None:
    try:
        doc = frontmatter.parse(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    fm = doc.front_matter
    state = str(fm.get("state", "")).strip().lower() or DEFAULT_STATE
    return Topic(
        path=path,
        name=path.stem,
        title=_title(doc.body, path.stem),
        state=state if state in STATES else DEFAULT_STATE,
        priority=str(fm.get("priority", "")).strip().lower(),
        purpose=_purpose(doc.body),
    )


def load_topics(project_root: Path) -> list[Topic]:
    """Topic files, sorted by filename. Absent directory → no topics, no error."""
    tdir = topics_dir(project_root)
    if not tdir.is_dir():
        return []
    found = [_topic_from_path(p) for p in sorted(tdir.glob("*.md"))
             if p.is_file() and p.name.lower() != "readme.md"]
    return [t for t in found if t is not None]


def card_topic(card) -> str:
    """A card's `topic:` value, read from its raw frontmatter record.

    Uses ``Card.fields`` rather than requiring a named attribute so this works
    against any Card, including ones built before the field existed.
    """
    named = getattr(card, TOPIC_FIELD, "")
    if named:
        return str(named).strip().strip("'\"").strip()
    for key, value in getattr(card, "fields", ()):
        if key == TOPIC_FIELD:
            return str(value).strip().strip("'\"").strip()
    return ""


def members(cards, topic_name: str) -> list:
    return [c for c in cards if card_topic(c) == topic_name]


def sort_key(topic: Topic) -> tuple:
    try:
        rank = PRIORITY_ORDER.index(topic.priority)
    except ValueError:
        rank = len(PRIORITY_ORDER)
    return (rank, topic.name)


def findings(project_root: Path, cards) -> list[Finding]:
    """Advisory read-out for `horus consolidate`. Never blocking.

    Silent on a project with no topics *and* no card referencing one, so adopting
    topics stays opt-in per project and nothing nags a repo that has not.
    """
    topics = load_topics(project_root)
    referenced = {t for t in (card_topic(c) for c in cards) if t}
    if not topics and not referenced:
        return []

    known = {t.name for t in topics}
    out: list[Finding] = []

    # A card pointing at a topic file that does not exist: the grouping silently
    # loses its thesis, which is the whole point of the topic.
    dangling = sorted(referenced - known)
    if dangling:
        out.append(Finding(
            "warn",
            f"{len(dangling)} card(s) name a topic with no file in .horus/topics/: "
            f"{', '.join(dangling)} — write the topic or fix the key",
        ))

    open_with = [t for t in topics if t.state == STATE_OPEN and members(cards, t.name)]
    open_without = [t for t in topics if t.state == STATE_OPEN and not members(cards, t.name)]
    settled = [t for t in topics if t.state == STATE_SETTLED]

    if open_with:
        detail = ", ".join(f"{t.name} ({len(members(cards, t.name))})"
                           for t in sorted(open_with, key=sort_key))
        out.append(Finding("ok", f"topics with open work — {detail}"))
    if open_without:
        out.append(Finding(
            "info",
            f"{len(open_without)} topic(s) stated but not yet broken into cards — "
            f"{', '.join(t.name for t in sorted(open_without, key=sort_key))}",
        ))
    if settled:
        out.append(Finding(
            "info",
            f"{len(settled)} settled topic(s) (answered, no work follows) — "
            f"{', '.join(t.name for t in sorted(settled, key=sort_key))}",
        ))

    # Active cards only: shelved and retired work is deliberately left on the old
    # grouping, so counting it here would report ~66 "problems" that are policy.
    from horus import backlog as _backlog
    untopiced = [c for c in cards
                 if not card_topic(c) and c.status not in _backlog.INACTIVE_STATUSES]
    if topics and untopiced:
        out.append(Finding(
            "info",
            f"{len(untopiced)} card(s) carry no topic — group them or leave ungrouped "
            "(a topic is never required)",
        ))
    return out
