"""The launch surface for an owner-attended backlog refine + order pass.

The LLM contract lives entirely in the bundled `backlog-refine` skill (picture
first, one card per decision, Ready last, sparse `order:` values). This module is
only the thin trigger both surfaces share:

- `horus backlog refine` prints the prompt (pipe it into `horus open --prompt`);
- the TUI's backlog pane runs it through the existing accounts -> launch pipeline.

One prompt builder, two consumers, so the launch text cannot drift between them.

**Why the prompt carries live delivery state.** A refine pass judges what is open
work, and the backlog file alone cannot answer that: other sessions open bug PRs
and leave branches unmerged, so a card whose fix is already sitting on an open PR
still reads as untouched. `gh pr list` shows only OPEN PRs and nothing inspects
branches, which is the same blind spot that cost this repo time twice on
2026-07-26 (see `closure.unmerged_branch_findings`). So the prompt embeds the
deterministic facts — open PRs, unmerged remote branches, continuity freshness —
rather than instructing the session to go look and hoping it does. Every probe is
best-effort and degrades to a stated "unknown", never to a false all-clear.

This module reads; it never writes a card. `order:` values are written by the
attended pass itself, with the owner approving each one — the same way `readiness`
is written today.
"""

from __future__ import annotations

from pathlib import Path

from horus import backlog, closure, integration, routines
from horus.continuity import Finding

SKILL_NAME = "backlog-refine"

# `gh pr list` on a launch keypress: bounded low so a slow network delays a spawn
# by ~a second, not the ten a default timeout would allow. A timeout reports
# "unknown", which the prompt states plainly.
_PR_TIMEOUT = 4.0

_UNKNOWN_PRS = (
    "unknown — `gh` is unavailable, unauthenticated, or timed out. Check open PRs "
    "yourself before trusting the picture."
)


def _pr_lines(root: Path) -> list[str]:
    prs = integration.open_prs(root, timeout=_PR_TIMEOUT)
    if prs is None:
        return [f"- Open PRs: {_UNKNOWN_PRS}"]
    if not prs:
        return ["- Open PRs: none."]
    lines = [f"- Open PRs ({len(prs)}) — a card answered by one of these is not open work:"]
    for pr in prs:
        number = f"#{pr['number']}" if pr["number"] else pr["url"]
        lines.append(f"    - {number} {pr['title']} [head: {pr['branch']}]")
    return lines


def _branch_lines(root: Path) -> list[str]:
    findings = closure.unmerged_branch_findings(root)
    if not findings:
        return ["- Unmerged remote branches: none (or unknowable without a fetch)."]
    return [f"- {finding.message}" for finding in findings]


def _continuity_lines(root: Path) -> list[str]:
    stale = [f for f in routines.freshness_signals(root) if f.level in ("warn", "fail")]
    if not stale:
        return ["- Continuity: no staleness signals — PRD.md frontmatter looks current."]
    lines = [
        "- Continuity is STALE. Consolidate first, so the picture rests on current "
        "state rather than on prose the last session left behind:"
    ]
    lines.extend(f"    - {finding.message}" for finding in stale)
    return lines


def delivery_state(root: Path) -> list[str]:
    """The deterministic pre-pass state block, as rendered lines (no trailing
    newline). Split out from :func:`refine_prompt` so a caller can show the same
    facts without the instructions, and so each probe is testable in isolation."""
    return _pr_lines(root) + _branch_lines(root) + _continuity_lines(root)


def order_state(cards: list[backlog.Card] | tuple[backlog.Card, ...]) -> list[str]:
    """How far the existing backlog is already sequenced, per readiness queue."""
    ordered = [card for card in cards if card.order is not None]
    if not ordered:
        return [
            f"- Sequence: no card carries `order:` yet — all {len(cards)} sit in the "
            "unsequenced pool."
        ]
    lines = [f"- Sequence: {len(ordered)} of {len(cards)} cards carry `order:`."]
    for group in backlog.readiness_groups(list(cards)):
        stamped = [card for card in group.cards if card.order is not None]
        if not stamped:
            continue
        shown = ", ".join(f"{card.order} {card.name}" for card in stamped)
        lines.append(f"    - {group.label}: {shown}")
    return lines


def findings(root: Path) -> list[Finding]:
    """Order-stamp warnings for this project's active cards — the same check
    `consolidate` and `close --check` run, exposed for the launch surfaces."""
    return backlog.order_findings(backlog.load_active_cards(root))


def refine_prompt(root: Path) -> str:
    """The launch prompt for an attended refine + order pass over `root`'s backlog.

    Orientation and live state only. It names the skill and hands over: the skill
    owns the picture, the per-card questionnaire, the owner gates, and the ordering
    rules, and duplicating any of that here would create a second contract to drift.
    """
    cards = backlog.load_active_cards(root)
    counts = backlog.readiness_counts(cards)
    ready, rest = backlog.readiness_count_summary(counts)
    warnings = [f"    - {finding.message}" for finding in backlog.order_findings(cards)]
    # Resolve before naming the project: a relative root (`horus backlog refine` run
    # as `.`) has an empty `.name` and the prompt read "Refine and order the  backlog".
    project = Path(root).resolve().name or "this project"

    lines = [
        f"Refine and order the {project} backlog with me. Invoke the "
        f"`{SKILL_NAME}` skill and follow it — it owns the picture, the one-card-at-a-time "
        "questionnaire, the readiness contract, and the ordering rules. Do not "
        "improvise a different flow, and change nothing I have not approved.",
        "",
        f"Backlog: {len(cards)} active cards in `.horus/{backlog.BACKLOG_DIR}/`.",
        f"  {ready}",
        f"  {rest}",
        "",
        "## Live state, read deterministically at launch",
        "",
        "Reconcile these against the cards BEFORE presenting the picture. Sync first "
        "(`git fetch --all --prune`) — the branch read below is only as current as the "
        "last fetch.",
        "",
    ]
    lines.extend(delivery_state(root))
    lines.extend(order_state(cards))
    if warnings:
        lines.append("- Existing `order:` stamps need attention:")
        lines.extend(warnings)
    lines.extend([
        "",
        "## Ordering",
        "",
        "Approved order lands as sparse integer `order:` frontmatter (gaps of 10, so a "
        "later insert at 15 renumbers nothing). It sequences cards WITHIN a readiness "
        "queue; unstamped cards stay in the unsequenced pool after the stamped ones. "
        "Say per card when a `depends-on`, branch grouping, priority, or "
        "`surface`/`parallel` collision forced a position. Ordering is planning I "
        "approve, never authority to run anything.",
    ])
    return "\n".join(lines) + "\n"
