---
status: shipped
priority: high
created: 2026-07-17
vision_facet: "Continuity core"
phase: converge
tier: sonnet
type: feature
parallel: safe
surface: close/resume/dispatch signals (deterministic parallel-delivery detection)
shipped_pr: 301
shipped_sha: 03dbd8a
---

# parallel-session-continuity-reconciliation — two sessions, one continuity

**Why (owner, 2026-07-17):** a scheduled session dispatched in parallel (same
account) delivered PR #287 while the supervisor session was mid-campaign on the
same repo. Delivery safety held (branch, PR, green required checks), but there is
no way to *reconcile continuity* between two concurrent writers: the parallel PR
sat invisible to the active session's closure until the owner pointed at it by
hand, and the supervisor then had to merge it and re-close so its own frontmatter
stayed on top. Canonical PRD frontmatter is last-writer-wins with no warning that
a sibling exists.

## Idea (cheapest rung first — deterministic signal, no locking)

Extend the existing pending-delivery detection so closure and resume *name
parallel deliveries explicitly*: at `close --check` / `resume`, detect (a) open or
freshly-merged sibling PRs on the same repo not yet covered by canonical
continuity, and (b) another live registered session/worker on the same project,
and print them as "parallel delivery pending: PR #N / live session <id>" instead
of the generic pending-commit count. The closing session then folds the sibling's
delivery into Shipped before sealing frontmatter — supervisor stays the canonical
continuity owner (existing rule), the signal just makes the sibling impossible to
miss.

**Acceptance:** when a PR merged (or opened) by a parallel session is pending at a
continuity boundary, `horus close --check` names that exact PR/merge commit as an
unconsolidated parallel delivery, and resume surfaces the same signal to a fresh
session.

## Non-goals

- No session locks/mutexes and no auto-merge of continuity prose — advisory
  signal only, per the controls ladder (promote only after another field failure).
- Not the scheduled-dispatch feature itself (separate card if/when the owner
  files it); this is only the reconciliation signal.

## Reviews

- 2026-07-17 — priority medium→high; joins the X3 away-mode kit. Second incident
  in 24h: PR #289 (scheduled parallel session) again needed the owner to point at
  the sibling delivery by hand before the supervisor merged and re-folded
  continuity. Scheduled autonomous dispatch (vision-branch-x3, now the primary
  thread) makes sibling deliveries the NORM, not the exception — the deterministic
  parallel-delivery signal must exist before the owner is away (2026-07-22).
