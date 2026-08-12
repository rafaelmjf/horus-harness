---
status: open
priority: high
readiness: ready
autonomy: attended
created: 2026-08-12
created_by: owner
type: feature
topic: backlog-model
parallel: unsafe
tier: large
surface: "horus/backlog.py, horus/backlog_tree.py, horus/routines.py, horus/templates.py, horus/terminal_tui.py, horus/capabilities.py, horus/cli.py, .claude/skills/*, .horus/PRD.md, .horus/backlog/*"
depends-on: d-backlog-model-topics-over-facets
---

# retire-facets-for-topics — full teardown of the vision/facet apparatus, replaced by emergent topics

**This card is the implementation brief for a dispatched Codex session.** It executes the
decision recorded in `d-backlog-model-topics-over-facets` (Option 3, owner 2026-08-09) at
its full extent: retire `vision_facet`, `phase`, vision-branches, and `facet_standings`
entirely, and stand up **topics** — a free-form, emergent grouping created at `consolidate`
— as the only card-grouping concept. The Vision is *not* deleted; it is reconceived as an
emergent section (see the sibling card `emerging-vision-mechanism`).

## Ground truth before starting

- Sync first (`git fetch --all --prune`), branch off `main`, PR to merge. Never commit to `main`.
- **Topics are 100% unbuilt in code today.** The only trace is the `topic:` frontmatter key on
  the discussion card. `brainstorm.py`'s "topic" is an unrelated concept (a subject to
  brainstorm about) — do not touch it.
- The whole active backlog is shelved except the bug `codex-isolated-config-leak` and the
  discussion card. You have a clean field.
- Bound every phase to a green, committed-and-pushed checkpoint. Reproduce the gate yourself
  (`python -m pytest` / the repo's suite) — do not trust a prose "tests pass".

## What "topic" means (the target model)

- A card carries an optional free-form `topic: <slug>` in frontmatter. No closed set, no
  definition-of-done contract at creation time. A card with no topic buckets to `Unsorted` —
  nothing ever silently disappears.
- A **topic emerges at `consolidate`**: a ledger check groups active + shipped cards by their
  `topic:` slug and reports each topic with its open/shipped counts. A topic is just "a slug
  ≥1 card shares"; there is no promotion-to-facet step anymore (that graduation moves up a
  level — to the Vision — via `emerging-vision-mechanism`).
- A **discussion card** (`type: discussion`) can carry a topic with no work cards: it records a
  conclusion under a topic. Topics group work cards *and* discussion cards alike.

## Ordered phases

Each phase is one PR-sized checkpoint, run start to finish — **no stops.** Every decision the
plan once deferred to the owner is now fixed below (owner, 2026-08-12): retire the whole
facet-coupled skill suite, a concrete emergent-Vision spec, and archive the branch cards.

### Phase 0 — Card data model (`backlog.py`, `templates.py`, existing cards)
- `backlog.py`: add `topic: str` to `Card` (default `""`), parse it (mirror the
  `vision_facet` parse at :249). **Remove** the `vision_facet` field (:161), the `phase`
  field (:162) and `DEFAULT_PHASE` (:93), and the `phase`/`vision_facet` parse lines. Keep
  the parser tolerant of stray legacy keys (ignore, don't error) so old cards still load.
- Remove the phase-aware branches in readiness/shelve logic (the `phase: explore` shipped-rate
  commentary at :79 and :632 — the escape-hatch justification goes with the hatch).
- `templates.py`: drop `vision_facet`/`phase` from the card template; add `topic`.
- Migrate every card in `.horus/backlog/` (active + shelved + archive): strip `vision_facet`,
  `phase`, and `branch:` keys; add `topic:` where the grouping is obvious (leave `""` when not).
- Gate: `pytest tests/test_backlog.py` green; `horus backlog list` still renders.

### Phase 1 — Grouping projection (`backlog_tree.py`, tests)
- Replace `FacetGroup` → `TopicGroup`, `Tree.facets` → `Tree.topics`, `build_tree_from_cards`
  facet grouping (:274–281) → group `leftover` by `card.topic`.
- **Remove the branch machinery entirely**: `BranchGroup`, `BRANCH_FIELD`, `_convergence_line`,
  the umbrella resolution in `build_tree_from_cards` (:242–268), and the branch sections in
  `sections_for`/`to_dict`/`render_text`/`render_json`. Full teardown means vision-branches go.
- Group-by lens: `GROUP_BY_LENSES` `"facet"`→`"topic"`; `GROUP_BY_LABELS` accordingly;
  `DEFAULT_GROUP_BY = "topic"`.
- Gate: `pytest tests/test_backlog_tree.py`; `horus backlog --tree` renders topics.

### Phase 2 — Consolidate read-out / the emergence ledger (`routines.py`, tests)
- **Remove** `_vision_facets`, `_norm_facet`, `FacetStandings`, `facet_standings` (:582–633+).
- Add `topic_standings(root)`: group active + shipped cards by `topic:`, return each topic
  with (open, shipped) counts and the `Unsorted` bucket. This is the emergence ledger —
  `consolidate` prints it. No DoD, no drift-against-facet warning.
- Wire it into the `consolidate` read-out where `facet_standings` was consumed.
- Gate: `pytest tests/test_routines.py` (large — expect many facet assertions to rewrite as
  topic assertions); `horus consolidate` prints the topic read-out.

### Phase 3 — Surfaces (`terminal_tui.py`, `capabilities.py`, `cli.py`, tests)
- `terminal_tui.py`: the "Direction view" consuming `facet_standings` → consume
  `topic_standings`; the `"facet"` lens label → `"topic"`.
- `capabilities.py`: drop `vision`/facet fields from the output (this also closes the
  `next_action` defect "fleet mode missing vision" — there is no vision facet to miss).
- `cli.py`: any `--tree`/facet wording → topic.
- Gate: `pytest tests/test_terminal_tui.py tests/test_capabilities.py`; TUI Direction view
  renders topics; `horus capabilities` clean.

### Phase 4 — Skills teardown (`.claude/skills/*`, `horus/skills.py`)
**Retire the entire facet-coupled divergence/convergence/audit suite** (owner, 2026-08-12).
- Delete these directories under `.claude/skills/`: `product-audit`, `roadmap-branches`,
  `scope-cards`, `market-scan`, `pathfinder`, `wildcard`, `explore-converge-lifecycle` (and any
  `convergence`/`roadmap-convergence` remnant).
- Keep `backlog-refine` and `backlog-librarian`; strip `facet`/`vision_facet`/`branch`/
  `convergence` vocabulary from their text only — grooming logic stays.
- Repoint `horus-consolidate` skill text from facet standings to the topic read-out (the code
  half is Phase 2).
- `horus/skills.py` (~106 facet refs): remove registry entries/descriptions for the retired
  skills and any router that sequences them (e.g. pathfinder); grep
  `facet|vision_facet|convergen|divergen` and remove/rewrite each remaining hit.
- The future replacement is carded separately (`rework-direction-skills-onto-topics`) — do NOT
  build it here.
- Gate: `pytest tests/test_skills.py`; `horus skill list` clean; grep of `.claude/skills/` and
  `horus/skills.py` for `facet|vision_facet|convergen` returns nothing.

### Phase 5 — PRD.md + emerging Vision (`.horus/PRD.md`, `routines.py`, `templates.py`)
Implement `emerging-vision-mechanism` with these fixed decisions:
- **Seed (kept verbatim):** the opening Vision prose (PRD.md:16, :18, :33) minus the single
  sentence introducing the facet table ("The Vision resolves into named **facets**…"). Delete
  the facet table (:20–29) and the divergence/convergence paragraph (:31).
- **Emergent block:** `consolidate` regenerates a "Directions so far" list from `topic_standings`
  between stable markers in `## Vision` (`<!-- directions:auto -->`…`<!-- /directions:auto -->`)
  so the seed is never clobbered. One line per topic with **≥1 shipped card**: topic name + a
  plain "where it stands" from open/shipped counts. No DoD. Zero-shipped topics are not rendered.
- Remove the facet/branch/convergence Rules (:280–282) and residual facet prose; keep durable
  non-facet rules. Apply the same edits to the `templates.py` PRD template.
- Refresh frontmatter (`current_focus`, `next_action`, `next_prompt`, `last_updated`).
- Gate: `horus consolidate` regenerates the directions block, the seed survives untouched, and a
  zero-shipped topic does not appear.

### Phase 6 — Vision-branch card cleanup (`.horus/backlog/`)
**Archive** (owner, 2026-08-12). Move the `vision-branch-x3..x6` umbrellas and their
`x4-*/x5-*/x6-*` children to `.horus/backlog/archive/` — parked branches of the retired model,
kept as history, not re-homed under topics. Relocate only; strip no content.

## Acceptance
- No `vision_facet`, `phase`, `branch`, or `facet_standings` symbol remains in `horus/*.py`
  (grep clean); `topic` grouping works end to end (`horus backlog --tree`, TUI, `consolidate`).
- Full suite green on the final SHA. Live probes: `horus backlog --tree`, `horus consolidate`,
  TUI Direction view all render topics with no facet vocabulary.
- No retired skill remains under `.claude/skills/`; `## Vision` shows seed + regenerated
  directions block; the branch cards are archived.

## Source
Owner decision 2026-08-12 (full teardown) implementing `d-backlog-model-topics-over-facets`.
