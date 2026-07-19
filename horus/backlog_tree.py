"""`horus backlog --tree` — the canonical branch/facet projection of a
project's active backlog cards, read once here and rendered by both the CLI
(`horus/cli.py`) and the phone-width TUI (`horus/terminal_tui.py`). Per the
repo's TUI rule, this is the ONLY place that groups cards by `branch:` — every
renderer consumes this projection rather than re-deriving it.

A "vision branch" is a divergence umbrella: a backlog card whose filename stem
other cards reference via their own `branch:` frontmatter key (see
`.horus/backlog/vision-branch-x3-scheduling-and-autonomous-execution.md` for
the convention). Active cards carrying a matching `branch:` value become that
umbrella's children; the umbrella card itself never appears as a plain card —
it supplies the group's title and convergence line instead. Every other active
card (no `branch:`, or a `branch:` that does not resolve to a card) groups by
`vision_facet` — `""` bucketing to "Unsorted" so nothing silently disappears.

A project with no `branch:` keys anywhere degrades to a single `Unsorted`-ish
set of facet groups spanning every card — the same population `horus backlog
list` shows today, just wrapped in the tree shape (forward-readable: an old
project with no branches renders identically in substance to the flat view).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from horus import backlog, frontmatter

SCHEMA_VERSION = 2

BRANCH_FIELD = "branch"

_CONVERGED_WHEN_RE = re.compile(r"converged\s+when\s*:\s*(.+)", re.IGNORECASE)


def _card_sort_key(card: backlog.Card) -> tuple:
    return backlog.readiness_sort_key(card)


@dataclass(frozen=True)
class BranchGroup:
    branch: str  # the `branch:` slug — also the umbrella card's filename stem, when it resolves
    title: str  # umbrella card's `# ` title, or the bare slug when the umbrella card is missing
    convergence: str  # best-effort convergence criterion pulled from the umbrella card's body
    resolved: bool  # whether `branch` matched an actual backlog card (unresolved still renders)
    children: tuple[backlog.Card, ...] = ()


@dataclass(frozen=True)
class FacetGroup:
    facet: str  # `vision_facet`, or "" for cards that name neither a branch nor a facet
    children: tuple[backlog.Card, ...] = ()


@dataclass(frozen=True)
class Tree:
    branches: tuple[BranchGroup, ...] = field(default_factory=tuple)
    facets: tuple[FacetGroup, ...] = field(default_factory=tuple)
    readiness: tuple[backlog.ReadinessGroup, ...] = field(default_factory=tuple)


def _body_text(path: Path) -> str:
    try:
        return frontmatter.parse(path.read_text(encoding="utf-8")).body
    except OSError:
        return ""


def _convergence_line(card: backlog.Card) -> str:
    """Best-effort one-line convergence criterion for an umbrella card: an
    explicit `Converged when: ...` line anywhere in the body (the phrasing
    `roadmap-branches` receipts use), falling back to the first non-empty line
    of an `## Acceptance` section (the phrasing hand-authored umbrella cards
    use, e.g. vision-branch-x3). Empty when neither is present — callers must
    tolerate a blank convergence line."""
    body = _body_text(card.path)
    match = _CONVERGED_WHEN_RE.search(body)
    if match:
        return match.group(1).strip()
    lines = body.splitlines()
    in_acceptance = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_acceptance:
                break
            in_acceptance = stripped[3:].strip().lower().startswith("acceptance")
            continue
        if in_acceptance and stripped:
            return stripped.lstrip("-*").strip()
    return ""


def build_tree(root: Path) -> Tree:
    """Read `.horus/backlog/` fresh and project it into branch umbrellas (with
    their children) plus facet groups for everything left over."""
    cards = backlog.load_active_cards(root)
    by_name = {card.name: card for card in cards}

    branch_of: dict[str, str] = {}
    slugs: list[str] = []
    for card in cards:
        slug = card.field_value(BRANCH_FIELD).strip()
        if not slug:
            continue
        branch_of[card.name] = slug
        if slug not in slugs:
            slugs.append(slug)
    slugs.sort()

    umbrella_names = {slug for slug in slugs if slug in by_name}

    branches: list[BranchGroup] = []
    for slug in slugs:
        umbrella = by_name.get(slug)
        children = tuple(sorted(
            (c for c in cards if branch_of.get(c.name) == slug and c.name != slug),
            key=_card_sort_key,
        ))
        branches.append(BranchGroup(
            branch=slug,
            title=umbrella.title if umbrella is not None else slug,
            convergence=_convergence_line(umbrella) if umbrella is not None else "",
            resolved=umbrella is not None,
            children=children,
        ))

    leftover = [
        card for card in cards
        if card.name not in umbrella_names and not branch_of.get(card.name)
    ]
    by_facet: dict[str, list[backlog.Card]] = {}
    for card in leftover:
        by_facet.setdefault(card.vision_facet, []).append(card)

    facets = [
        FacetGroup(facet=facet, children=tuple(sorted(cards_, key=_card_sort_key)))
        for facet, cards_ in sorted(by_facet.items(), key=lambda kv: (kv[0] == "", kv[0]))
    ]

    return Tree(
        branches=tuple(branches),
        facets=tuple(facets),
        readiness=backlog.readiness_groups(cards),
    )


def _card_to_dict(card: backlog.Card) -> dict:
    return {
        "name": card.name,
        "title": card.title,
        "status": card.status,
        "priority": card.priority,
        "phase": card.phase,
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
            {
                "key": group.key,
                "label": group.label,
                "count": len(group.cards),
            }
            for group in tree.readiness
        ],
        "branches": [
            {
                "branch": group.branch,
                "title": group.title,
                "convergence": group.convergence,
                "resolved": group.resolved,
                "count": len(group.children),
                "children": [_card_to_dict(c) for c in group.children],
            }
            for group in tree.branches
        ],
        "facets": [
            {
                "facet": group.facet,
                "count": len(group.children),
                "children": [_card_to_dict(c) for c in group.children],
            }
            for group in tree.facets
        ],
    }


def render_json(tree: Tree) -> str:
    """Deterministic JSON text: stable key/list ordering, no timestamps."""
    return json.dumps(to_dict(tree), indent=2) + "\n"


def _format_child(card: backlog.Card) -> str:
    line = (
        f"    {card.name}  [{card.status}]  priority={card.priority or '-'} "
        f"phase={card.phase} tier={card.tier or '-'} readiness={backlog.readiness_label(card)}"
    )
    if card.readiness_reason:
        line += f" reason={card.readiness_reason}"
    return line


def render_text(tree: Tree) -> str:
    """Human-readable indented tree: one section per branch umbrella, then one
    per facet — the phone-width TUI renders the same projection, just with
    collapse/expand instead of always-expanded text."""
    if not any(group.cards for group in tree.readiness):
        return "No open backlog cards.\n"
    lines: list[str] = ["Readiness queues"]
    lines.extend(f"  {group.label}: {len(group.cards)}" for group in tree.readiness)
    lines.append("")
    for group in tree.branches:
        note = "" if group.resolved else " (no matching umbrella card)"
        lines.append(f"{group.title} ({len(group.children)} open){note}")
        if group.convergence:
            lines.append(f"  converges: {group.convergence}")
        for card in group.children:
            lines.append(_format_child(card))
        lines.append("")
    for group in tree.facets:
        label = group.facet or "Unsorted"
        lines.append(f"{label} ({len(group.children)} open)")
        for card in group.children:
            lines.append(_format_child(card))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Receipts shelf — `.horus/research/`, newest-first, read-only.
# ---------------------------------------------------------------------------

_DATED_RECEIPT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")


@dataclass(frozen=True)
class Receipt:
    path: Path
    date: str  # "YYYY-MM-DD", or "" when the filename carries no date prefix
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
    """`.horus/research/*.md`, newest-first by filename date prefix; files
    without a recognizable `YYYY-MM-DD-` prefix sort after every dated one
    (still listed, never dropped)."""
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
    receipts.sort(key=lambda r: (r.date, r.path.name), reverse=True)
    return receipts
