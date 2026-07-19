---
status: open
priority: medium
readiness: ready
autonomy: eligible
created: 2026-07-19
last_refined: 2026-07-19
vision_facet: "PO lifecycle"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: owner
surface: horus/backlog.py (readiness/autonomy/last_refined parse), horus/backlog_tree.py, horus/cli.py (backlog list/migration), horus/terminal_tui.py (backlog pane), horus/routines.py (consolidate read-out counts), scheduler candidate gates
---

# backlog-readiness-disposition — machine-readable readiness and autonomy

**Why (owner, 2026-07-19 refinement calibration):** one optional `deferred:` field could
not distinguish work that is active but still being shaped, blocked on evidence, ready
for attended execution, or safe for an approved autonomous envelope. The first full
curation pass therefore produced a unified four-way readiness model plus an orthogonal
autonomy decision. Tooling must consume that state so backlog counts, the TUI, cockpit,
and scheduler stop treating every open card as actionable.

## Contract (owner-approved)

```yaml
readiness: ready | shaping | gated | deferred
readiness_reason: "required for shaping, gated, and deferred"
autonomy: eligible | attended  # required only for Ready
```

- Ready means decision-complete now. `eligible` permits scheduling only under a valid
  owner envelope; `attended` requires the owner during execution or verification.
- Shaping is active owner/LLM work whose next action is research, review, brainstorm,
  scoping, refinement, or an exploratory probe.
- Gated names a concrete dependency, event, or evidence source; use `depends-on` too
  when the gate is another card.
- Deferred is deliberately inactive until an explicit trigger or owner review.
- Missing readiness is **Unclassified**, never Ready and never scheduler-eligible.
- `phase` and `priority` stay orthogonal; priority is importance when active.
- `last_refined` remains an optional evidence stamp, not a readiness inference.

## How

- Parse the fields into the Card model and preserve them through every writer.
- Render six honest queues: Ready—Autonomous eligible, Ready—Attended, Shaping,
  Gated, Deferred, and Unclassified, including reasons where required.
- Add an assisted migration path that proposes classifications through
  `backlog-refine`; never auto-rewrite an existing repository.
- Make list/tree/TUI/consolidate report the same counts and ordering.
- Make every scheduler/arming consumer accept only Ready—Eligible. Attended Ready is
  actionable but never autonomous; every other class is rejected with its reason.
- Remove the superseded `deferred:` special-field behavior rather than supporting two
  rival disposition systems.

## Acceptance

- All six queues render consistently in CLI and TUI with the approved 36-card fixture.
- Validation requires `readiness_reason` on non-Ready cards and `autonomy` exactly on
  Ready cards; malformed combinations warn without silently inferring eligibility.
- Scheduler arming accepts Ready—Eligible and rejects the other five classes with an
  actionable explanation.
- Missing readiness remains Unclassified and no migration writes without approval.
- Gate: full suite green on the exact SHA. Probe: move one fixture card through
  Shaping → Ready—Attended → Ready—Eligible and observe CLI/TUI/scheduler behavior at
  each state.

## Non-goals

- No new lifecycle status values; `status` remains open/claimed/shipped/done.
- No automatic readiness promotion, date expiry, model selection, or dispatch.
- No global repository rewrite during upgrade.

## Source

Two attended backlog-refinement sessions, 2026-07-19. The second pass replaced the
temporary deferred-only proposal before its tooling shipped.
