---
status: open
priority: low
created: 2026-07-24
created_by: claude
readiness: shaping
readiness_reason: "Freshly minted, not yet through backlog-refine. Shaped FOR autonomous execution: deterministic source of truth (backlog.readiness_counts) already exists, no owner taste-decision embedded, pass/fail verifiable by a unit test + CI. Promote to Ready—Autonomous eligible at the owner's refine gate; nothing here needs owner input to build."
phase: converge
type: chore
tier: small
parallel: safe
vision_facet: "Continuity core"
---

# prd-readiness-count-check — keep the PRD readiness-breakdown counts honest automatically

## Why — a self-detection gap found by living it (2026-07-24)

The PRD's `## Backlog` "Readiness breakdown" line hand-writes the counts per queue —
`Shaping (N)`, `Deferred (N)`, `Gated (N)`, … Every card added or reclassified forces
a manual edit of those parenthetical numbers, and they silently drift when someone
forgets (observed live this session while adding wildcard cards). This is the audit's
own self-detection complaint in miniature — "drift detection relies on the owner
noticing" — on the very file that steers resume. The counts are already computed
deterministically by `horus/backlog.py::readiness_counts()`; nothing reconciles the
prose against them.

## Rough shape (autonomous, deterministic)

- Parse the queue-count tokens out of the "Readiness breakdown" line (e.g. `Shaping (N)`).
- Compare against `readiness_counts(load_cards())`.
- Two modes, both decided (no owner taste call):
  - **check:** a `horus consolidate` / `close --check` advisory that fails/warns when a
    stated count ≠ the computed count;
  - **fix:** rewrite only the numeric tokens in place, leaving the editorial prose
    ("now includes the owner-attended … experiment") untouched.
- Verification gate: a unit test that (a) detects a deliberately-wrong count and (b)
  confirms fix restores it without touching surrounding prose; plus the existing suite green.

## Non-goals

- Do NOT auto-generate the whole line — the editorial annotations are human-authored and
  must survive; only the `(N)` count tokens are managed.
- No change to `readiness_counts()` semantics or the queue taxonomy.
- Not a general prose linter (that axis is `managed-instruction-drift-lint`); this is a
  single-line count reconciliation against an existing source of truth.

## Source

Wildcard run 3 (2026-07-24), owner constraint: autonomously implementable without owner
input. Grounded in this session's live drift + `continuity-sync-friction` (PRD frontmatter
as a shared hotspot) + the 07-20 audit's self-detection gap. Uses existing
`backlog.readiness_counts()`. Related: `continuity-sync-friction`, `close-check-unclassified-cards-advisory`.
