---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Decide which shared artifact carries the render-confirm-before-merge discipline (managed block vs merge-release-owner-gate scope) and sweep for other corrections living only in one agent's memory."
phase: converge
type: bug
vision_facet: "Introspection & self-improvement"
---

# process-fixes-live-in-process-not-memory — shared artifacts, not one agent's recall

## Why

**Owner rule (2026-07-20, general to all Horus projects):** a mistake that is an
error in the process must be fixed in the process itself — skills, managed
blocks, PRD Rules, cards — never only in an agent's private memory, because
agent memories are not shared across agents and accounts. Observed instance:
after auto-merging a format-contract change without a rendered confirmation
(the `merge-release-owner-gate` failure class, evidence in that card's
Reviews), the corrective "render-confirm before merging contract changes"
discipline was written into the Claude agent's memory — invisible to Codex,
other accounts, and other machines.

## Intended outcome

The render-confirm-before-merge discipline lives in a shared process artifact
(candidates: the managed-block working discipline, or folded into
`merge-release-owner-gate`'s scope as the interim instruction rung), and a
short sweep confirms no other 2026-07-20 calibration correction exists only in
agent memory (the questionnaire format and receipt spines already live in the
skills — verify, don't assume).

## Non-goals

- No new memory-sync machinery; the fix is putting rules where they already
  travel (repo artifacts).
- Agent memory may still carry pointers/copies — it just can't be the only home.

## Source

Owner correction 2026-07-20 in the calibration session;
`merge-release-owner-gate` Reviews entry of the same date.
