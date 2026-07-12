"""`horus fleet --backlog` — deterministic, read-only fleet-wide backlog roll-up.

An agent resuming fleet-wide work currently derives "what's open, where" by
opening every registered project's PRD/backlog by hand. This module instead
reads the registry (``projects`` in ``~/.horus/config.toml``) and each
project's ``.horus/backlog/`` cards directly, and renders a grouped,
deterministically sorted view — the fleet-resume input for that hand pass.

Same discipline as ``horus/capabilities.py`` and ``horus fleet``: read-only,
no network/fetch, deterministic ordering. A project still on the inline PRD
``## Backlog`` section (not yet migrated per PR #164's card-per-file standard)
or missing ``.horus/backlog/`` entirely degrades to a skip-with-note row
instead of crashing the whole roll-up.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from horus import backlog, backlog_migrate, frontmatter

SCHEMA_VERSION = 1

# Known priority values in urgency order (see `.horus/backlog/*.md` in the
# wild: now/next/high/medium/low plus the roadmap-derived "later"/"deferred").
# Priority is a free-form field (see horus/backlog.py), so anything else sorts
# after these, alphabetically, rather than raising on an unrecognized value.
_PRIORITY_RANK = {"now": 0, "next": 1, "high": 2, "medium": 3, "low": 4, "later": 5, "deferred": 6}


def _priority_sort_key(priority: str) -> tuple[int, str]:
    return (_PRIORITY_RANK.get(priority, len(_PRIORITY_RANK)), priority)


@dataclass
class ProjectRollup:
    name: str
    path: str
    mode: str  # "cards" | "inline" | "none" | "unreadable"
    note: str = ""
    cards: list[backlog.Card] = field(default_factory=list)


def _card_to_dict(card: backlog.Card) -> dict:
    return {
        "name": card.name,
        "title": card.title,
        "status": card.status,
        "priority": card.priority,
        "tier": card.tier,
        "type": card.type,
        "surface": list(card.surface),
        "shipped_pr": card.shipped_pr or None,
        "shipped_sha": card.shipped_sha or None,
    }


def load_project_rollup(path_str: str, *, include_shipped: bool = False) -> ProjectRollup:
    """One project's backlog roll-up, read fresh from disk. Never raises — a
    project whose path has vanished, whose ``.horus/`` is gone, or whose cards
    fail to parse degrades to an ``"unreadable"`` row with a note rather than
    aborting the fleet-wide view (the projects-section resilience rule)."""
    root = Path(path_str)
    name = root.name
    try:
        if not root.is_dir():
            return ProjectRollup(name, str(root), "unreadable", note="project path not found")
        if not (root / ".horus").is_dir():
            return ProjectRollup(name, str(root), "unreadable", note="no .horus/ found")

        if backlog.backlog_dir(root).is_dir():
            # `status: done` is legacy lifecycle drift, not open work; shipped
            # cards are deliberately retained but excluded from active views.
            excluded = {"done"}
            if not include_shipped:
                excluded.add("shipped")
            cards = [c for c in backlog.load_cards(root) if c.status not in excluded]
            return ProjectRollup(name, str(root), "cards", cards=cards)

        if frontmatter.has_prd(root):
            count = backlog_migrate.inline_backlog_item_count(root)
            if count:
                note = (
                    f"inline '## Backlog' not yet migrated to cards ({count} item(s)); "
                    "run `horus backlog migrate --apply`"
                )
                return ProjectRollup(name, str(root), "inline", note=note)
            if count is None:
                return ProjectRollup(name, str(root), "none", note="no '## Backlog' section in PRD.md")
            return ProjectRollup(name, str(root), "cards", note="no open cards")

        return ProjectRollup(name, str(root), "none", note="no .horus/backlog/ (pre-v3 project?)")
    except Exception as exc:  # noqa: BLE001 — one project's row must never sink the fleet view
        return ProjectRollup(name, str(root), "unreadable", note=f"error reading backlog: {exc}")


def load_fleet_rollup(project_paths: list[str], *, include_shipped: bool = False) -> list[ProjectRollup]:
    """Every registered project's roll-up, sorted by name for determinism."""
    rollups = [load_project_rollup(p, include_shipped=include_shipped) for p in project_paths]
    rollups.sort(key=lambda r: r.name.casefold())
    return rollups


def apply_filters(rollups: list[ProjectRollup], *, type_filter: str = "") -> list[ProjectRollup]:
    """Filter each project's cards to `type_filter` (if given) and sort them by
    priority then name. Returns new rollups; input is left untouched."""
    result = []
    for r in rollups:
        cards = r.cards
        if type_filter:
            cards = [c for c in cards if c.type == type_filter]
        cards = sorted(cards, key=lambda c: (_priority_sort_key(c.priority), c.name))
        result.append(replace(r, cards=cards))
    return result


def to_dict(rollups: list[ProjectRollup], *, type_filter: str = "", project_filter: str = "") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "filters": {"type": type_filter or None, "project": project_filter or None},
        "projects": [
            {
                "name": r.name,
                "path": r.path,
                "mode": r.mode,
                "note": r.note,
                "cards": [_card_to_dict(c) for c in r.cards],
            }
            for r in rollups
        ],
    }


def render_json(rollups: list[ProjectRollup], *, type_filter: str = "", project_filter: str = "") -> str:
    """Deterministic JSON text: stable key/list ordering, no timestamps."""
    return json.dumps(to_dict(rollups, type_filter=type_filter, project_filter=project_filter), indent=2) + "\n"


def _format_card(card: backlog.Card) -> list[str]:
    surface = ", ".join(card.surface) if card.surface else "unverified"
    return [
        f"  {card.name}  [{card.status}]  priority={card.priority or '-'} "
        f"tier={card.tier or '-'} type={card.type}",
        f"    {card.title}",
        f"    surface: {surface}",
    ]


def render_text(rollups: list[ProjectRollup]) -> str:
    """Human-readable grouped roll-up: one section per project, cards sorted
    within it (callers should pass rollups already through `apply_filters`)."""
    lines: list[str] = []
    for r in rollups:
        header = f"{r.name} ({len(r.cards)} open card(s))" if r.mode == "cards" else r.name
        lines.append(header)
        if r.note:
            lines.append(f"  note: {r.note}")
        for card in r.cards:
            lines.extend(_format_card(card))
        lines.append("")
    if not lines:
        return "No fleet projects registered.\n"
    return "\n".join(lines).rstrip("\n") + "\n"
