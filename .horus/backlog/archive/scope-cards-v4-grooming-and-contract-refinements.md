---
status: shipped
priority: high
created: 2026-07-19
last_refined: 2026-07-19
vision_facet: "PO lifecycle"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: owner
surface: horus/skills.py (_SCOPE_CARDS_SKILL, _PATHFINDER_SKILL), tests/test_skills.py, .claude/skills + .agents/skills projections
shipped_pr: 354
shipped_sha: 3c2e4f97e4c950ca7de372ecbe4602e9b826ecc0
---

# scope-cards-v4-grooming-and-contract-refinements — what the first live run taught

**Why (first live pathfinder-v5 run, horus-harness, 2026-07-19):** the polish pass ran
the new triage gate for real — it correctly routed a grooming need OUT of the five-step
chain — and then audited all 34 open cards against the day-old dispatchable-card
contract. Four gaps surfaced; all are cheap skill-text fixes that should ship before
the next release projects the v3 contract to the fleet.

## How — the four revisions (scope-cards v3→4, plus one pathfinder touch)

1. **Grooming mode is referenced but not specified.** Pathfinder v5's triage says
   "`scope-cards` standalone grooms individual thin cards", but scope-cards' Input
   section is branch-shaped only. Add a short "Grooming an existing backlog" section:
   input = existing open cards; bar = the same contract; deterministic field audit
   first (surface/parallel/tier/facet/acceptance markers), judgment second; per-item
   owner gate unchanged; batch mechanical fixes into one approval, never batch
   judgment calls.
2. **The contract is stricter than the Vision's own breathing rule.** 12 live `explore`
   branch children legitimately carry no `vision_facet` (umbrella `branch:` stamp
   instead). State: `vision_facet` required for `converge` cards; `explore` cards may
   substitute a `branch:` stamp until the direction earns a facet or dies.
3. **Umbrella cards carry `## Convergence criterion`, not `## Acceptance`.** The live
   x4/x5 umbrellas are correct; the contract never says so. One line legitimizing it.
4. **Probe retrofit policy.** Only NEW cards owe a probe at scoping time; existing
   cards get theirs named when armed for dispatch (the ready-gate checks) or next
   substantively edited. Blanket retrofits are ceremony — write the policy down so a
   future grooming pass doesn't "fix" 17 cards nobody will dispatch.

Also stamp the future producer duty: when the `order:` field ships (decided 2026-07-19,
sparse ints — see [[tui-backlog-refine-and-order]]), scope-cards stamps an
owner-approved branch order at transcription time. Reference only; do not build the
field here.

## Acceptance

- scope-cards v4 carries the grooming-mode section, the facet/umbrella exceptions, and
  the probe-retrofit policy; pathfinder's triage route-out matches the new section name.
- Gate: full suite green on the exact SHA (version pins + drift-guard test updated).
- Probe: both installed projections (`.claude`/`.agents`) show v4 and are identical;
  a grep for "Grooming an existing backlog" hits in both.

## Non-goals

- No `order:` field implementation (that lands with [[tui-backlog-refine-and-order]]).
- No new audit tooling — the deterministic field audit stays a session script until
  the refine pass builds it properly.

## Source

First live pathfinder-v5 run on horus-harness, 2026-07-19 (this repo, polish-pass
session); no receipt file — the run's findings are recorded here and in the PR.
