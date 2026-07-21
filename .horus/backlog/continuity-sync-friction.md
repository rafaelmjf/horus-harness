---
status: open
priority: medium
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "Problem and live evidence are clear; the fix space is deliberately left OPEN (cheap auto-fetch vs deeper format changes) to explore before committing. Refine into concrete increments when picked up."
phase: explore
type: chore
vision_facet: "Continuity core"
---

# continuity-sync-friction — reduce cross-session/cross-machine friction in git-synced continuity

## Why — observed live, 2026-07-21

Continuity is git-synced, which has been a good remote-sync option — but this session
hit two **distinct** frictions worth fixing:

1. **Session-start staleness.** Local `main` was 5 commits behind; the SessionStart hook
   *warned* but fetch-first is advisory, so continuity read at start was stale and cards
   left by other sessions (`codex-identity-guard`, `close-check-unclassified-cards-advisory`)
   were not visible until an explicit fetch mid-session.
2. **PRD frontmatter hand-merge.** Because upstream closures had advanced `PRD.md`, this
   session's frontmatter update had to be re-based on the fresh version and hand-merged —
   preserving prior must-not-lose items (the unmapped `codex-codex-work` dir decision, the
   untested `skill install --user`) while appending the new pointer. The single-line
   `next_prompt`/`current_focus`/`next_action` fields make this a whole-line reconciliation
   every time.

Root reads (to validate, not lock): (1) is purely that fetch-first is advisory, not
enacted. (2) is partly that `next_prompt` carries durable *open decisions* that lack
another home — forcing preserve-and-append — and partly that the volatile pointer shares a
file with the rarely-changing PRD body.

## Intended outcome (open — explore before committing)

Less *avoidable* friction reading and updating continuity across sessions/machines, WITHOUT
decoupling continuity from the repo (repo-local + serverless stays the invariant, and the
occasional hand-merge is an acceptable price). Keep the parts that already scale — per-file
backlog cards conflicted zero times.

## Candidate directions (sketches, NOT decisions)

- **Enact fetch-first:** SessionStart hook actually runs `git fetch` (read-only) and
  auto-`ff-only` pulls when the tree is clean with no local commits, instead of only
  warning. Looks cheap + high-value.
- **Give open decisions a durable home** so `next_prompt` becomes a disposable
  last-writer-wins pointer rather than an accreting register (cards, or an "open decisions"
  list under `## Rules`).
- **Split the volatile pointer** out of `PRD.md` into its own small file, so the hot part
  does not drag the cold PRD body into every merge.
- **Tooling:** `horus resume` surfaces exactly what changed in `.horus/` upstream (new
  cards, frontmatter drift) so reconciliation is not hand-diffed.

## Open questions / to explore

- Which directions are worth doing, and in what order.
- Whether open-decisions get their own register or simply become cards.
- Interaction with the freshness gate.
- **Explicitly the sequential on-ramp to `concurrency-safe-continuity`** — design any fix
  here so it does not have to be redone under parallel multi-agent development.

## Source

In-session process review, 2026-07-21, prompted by the friction during this session's own
landing. Research receipt `.horus/research/2026-07-21-mobile-agent-session-access.md`.
Related: `close-check-unclassified-cards-advisory`, `concurrency-safe-continuity`.
