"""Canonical topic projection for active backlog cards and research receipts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from horus import backlog

SCHEMA_VERSION = 3


def _card_sort_key(card: backlog.Card) -> tuple:
    return backlog.readiness_sort_key(card)


@dataclass(frozen=True)
class TopicGroup:
    topic: str  # free-form slug, or "" for Unsorted
    children: tuple[backlog.Card, ...] = ()


@dataclass(frozen=True)
class Tree:
    topics: tuple[TopicGroup, ...] = field(default_factory=tuple)
    readiness: tuple[backlog.ReadinessGroup, ...] = field(default_factory=tuple)


# --- configurable group-by lens (TUI grouped-list view) --------------------

GROUP_BY_LENSES: tuple[str, ...] = ("none", "readiness", "topic", "status", "priority")
GROUP_BY_LABELS: dict[str, str] = {
    "none": "None (flat)",
    "readiness": "Readiness",
    "topic": "Topic",
    "status": "Status",
    "priority": "Priority",
}
DEFAULT_GROUP_BY = "topic"

_PRIORITY_ORDER: tuple[str, ...] = ("now", "next", "high", "medium", "low")

READINESS_FILTERS: tuple[str, ...] = ("all", "active", "ready", "parked")
READINESS_FILTER_LABELS: dict[str, str] = {
    "all": "All",
    "active": "Active",
    "ready": "Ready",
    "parked": "Parked",
}
_FILTER_QUEUES: dict[str, frozenset[str]] = {
    "active": frozenset({
        backlog.QUEUE_READY_ELIGIBLE, backlog.QUEUE_READY_ATTENDED,
        backlog.QUEUE_SHAPING, backlog.QUEUE_UNCLASSIFIED,
    }),
    "ready": frozenset({backlog.QUEUE_READY_ELIGIBLE, backlog.QUEUE_READY_ATTENDED}),
    "parked": frozenset({backlog.QUEUE_GATED, backlog.QUEUE_DEFERRED}),
}
_READY_QUEUES: frozenset[str] = frozenset(
    {backlog.QUEUE_READY_ELIGIBLE, backlog.QUEUE_READY_ATTENDED}
)


def filter_cards(cards, readiness_filter: str) -> list[backlog.Card]:
    """Keep only cards admitted by ``readiness_filter``, preserving order."""
    allowed = _FILTER_QUEUES.get(readiness_filter)
    if allowed is None:
        return list(cards)
    return [c for c in cards if backlog.readiness_queue(c) in allowed]


def ready_count(cards) -> int:
    return sum(1 for c in cards if backlog.readiness_queue(c) in _READY_QUEUES)


@dataclass(frozen=True)
class GroupSection:
    key: str
    label: str
    subtitle: str
    children: tuple[backlog.Card, ...]


def _sections_by_field(cards, keyfn, order: tuple[str, ...], prefix: str) -> list[GroupSection]:
    buckets: dict[str, list] = {}
    for card in cards:
        buckets.setdefault(keyfn(card), []).append(card)

    def rank(key: str) -> tuple:
        if key == "":
            return (2, "")
        return (0, order.index(key)) if key in order else (1, key)

    return [
        GroupSection(
            key=f"{prefix}:{key}",
            label=key or "(none)",
            subtitle="",
            children=tuple(sorted(buckets[key], key=_card_sort_key)),
        )
        for key in sorted(buckets, key=rank)
    ]


def sections_for(cards, lens: str, tree: "Tree | None" = None) -> list[GroupSection]:
    """Project cards into ordered, counted sections for a grouped-list lens."""
    cards = list(cards)
    if lens == "readiness":
        return [
            GroupSection(key=f"readiness:{g.key}", label=g.label, subtitle="", children=g.cards)
            for g in backlog.readiness_groups(cards) if g.cards
        ]
    if lens == "topic":
        tree = tree if tree is not None else build_tree_from_cards(cards)
        return [
            GroupSection(
                key=f"topic:{group.topic}",
                label=group.topic or "Unsorted",
                subtitle="",
                children=group.children,
            )
            for group in tree.topics if group.children
        ]
    if lens == "status":
        return _sections_by_field(cards, lambda c: c.status or "", ("open", "claimed"), "status")
    if lens == "priority":
        return _sections_by_field(cards, lambda c: c.priority or "", _PRIORITY_ORDER, "priority")
    return []


def build_tree(root: Path) -> Tree:
    """Read active cards and project every one into its topic or Unsorted."""
    return build_tree_from_cards(backlog.load_active_cards(root))


def build_tree_from_cards(cards: list[backlog.Card]) -> Tree:
    by_topic: dict[str, list[backlog.Card]] = {}
    for card in cards:
        by_topic.setdefault(card.topic, []).append(card)
    topics = [
        TopicGroup(topic=topic, children=tuple(sorted(cards_, key=_card_sort_key)))
        for topic, cards_ in sorted(by_topic.items(), key=lambda item: (item[0] == "", item[0]))
    ]
    return Tree(topics=tuple(topics), readiness=backlog.readiness_groups(cards))


def _card_to_dict(card: backlog.Card) -> dict:
    return {
        "name": card.name,
        "title": card.title,
        "status": card.status,
        "priority": card.priority,
        "topic": card.topic,
        "tier": card.tier,
        "readiness": card.readiness or "unclassified",
        "readiness_queue": backlog.readiness_queue(card),
        "readiness_reason": card.readiness_reason,
        "autonomy": card.autonomy,
    }


def to_dict(tree: Tree) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "readiness": [
            {"key": group.key, "label": group.label, "count": len(group.cards)}
            for group in tree.readiness
        ],
        "topics": [
            {
                "topic": group.topic,
                "count": len(group.children),
                "children": [_card_to_dict(card) for card in group.children],
            }
            for group in tree.topics
        ],
    }


def render_json(tree: Tree) -> str:
    return json.dumps(to_dict(tree), indent=2) + "\n"


def _format_child(card: backlog.Card) -> str:
    line = (
        f"    {card.name}  [{card.status}]  priority={card.priority or '-'} "
        f"tier={card.tier or '-'} readiness={backlog.readiness_label(card)}"
    )
    if card.readiness_reason:
        line += f" reason={card.readiness_reason}"
    return line


def render_text(tree: Tree) -> str:
    """Render readiness counts followed by one section per topic."""
    if not any(group.cards for group in tree.readiness):
        return "No open backlog cards.\n"
    lines: list[str] = ["Readiness queues"]
    lines.extend(f"  {group.label}: {len(group.cards)}" for group in tree.readiness)
    lines.append("")
    for group in tree.topics:
        lines.append(f"{group.topic or 'Unsorted'} ({len(group.children)} open)")
        lines.extend(_format_child(card) for card in group.children)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Receipts shelf — `.horus/research/`, newest-first, read-only.
# ---------------------------------------------------------------------------

_DATED_RECEIPT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")


@dataclass(frozen=True)
class Receipt:
    path: Path
    date: str
    title: str


def _receipt_title(path: Path, slug: str) -> str:
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        body = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return slug.replace("-", " ")


def list_receipts(root: Path) -> list[Receipt]:
    research_dir = root / ".horus" / "research"
    if not research_dir.is_dir():
        return []
    receipts: list[Receipt] = []
    for path in sorted(research_dir.glob("*.md")):
        if not path.is_file():
            continue
        match = _DATED_RECEIPT_RE.match(path.stem)
        date, slug = (match.group(1), match.group(2)) if match else ("", path.stem)
        receipts.append(Receipt(path=path, date=date, title=_receipt_title(path, slug)))
    receipts.sort(key=lambda receipt: (receipt.date, receipt.path.name), reverse=True)
    return receipts
