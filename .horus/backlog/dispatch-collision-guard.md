---
status: open
priority: medium
created: 2026-07-24
created_by: claude
readiness: shaping
readiness_reason: "The claim signal (derive from open branch/PR referencing the slug vs a written marker vs the schedule ledger) and the enforcement point (pre-dispatch refuse vs advisory warn) are undecided; refine before build. Escalate to high the moment two concurrent dispatches run against one backlog."
phase: explore
type: feature
vision_facet: "Autonomous dispatch"
---

# dispatch-collision-guard — stop two concurrent agents from building the same card

## Why — the selection-moment blind spot the continuity cards assume away

`concurrency-safe-continuity` and `continuity-sync-friction` both attack the MERGE
moment: what happens to shared `PRD.md` state when parallel branches land. There is a
distinct, earlier failure — the SELECTION moment — that no card covers. Two concurrently
active agents both read the backlog, both see the same Ready—Eligible card, and both
build it on separate branches. Git never conflicts (different work), the freshness gate
never fires (both continuities are fresh), and the collision only surfaces at the second
merge, after the tokens are already spent on a redundant, possibly contradictory PR.

`concurrency-safe-continuity` explicitly assumes this away — "backlog cards stay fine
(unique files, append-mostly)." True for merging cards; false for selecting them. The
collision becomes live the instant the owner runs the plan already on the board:
`fleet-sourced-autonomous-batch` (high, trip-timed) wants ≥3 cards running across ≥2
projects, and the C-primary direction is parallel away-mode dispatch.

## Rough shape

- Before a dispatch/selection claims a card, check whether the card is already IN FLIGHT
  and refuse or warn if so.
- Derive "in flight" from durable facts that already exist rather than new mutable state
  in the card (a written marker just recreates the frontmatter-conflict problem):
  - an open branch or PR whose name/body references the card slug;
  - optionally the on-disk schedule ledger (a pending/running scheduled run bound to it).
- Autonomous-safe: read-only advisory by default. The stronger form — a hard pre-dispatch
  refuse — is an owner call because it changes dispatch semantics.

## Open questions

- Claim signal precision: slug in branch name is cheap but relies on naming discipline;
  PR-body reference is richer but needs a convention. Pick the cheapest reliable one.
- Enforcement point: `horus run`/dispatch pre-check, or a supervisor pre-flight, or both.
- Does worktree isolation change the branch-existence check for `.horus/` specifically
  (cross-links to `concurrency-safe-continuity`'s open question)?
- Interaction with `fleet-sourced-autonomous-batch`: collisions there are cross-PROJECT,
  so the check is per-backlog per-repo, not fleet-global — scope it to one repo first.

## Non-goals

- No distributed lock service or runtime daemon (repo-local + serverless invariant holds).
- No merge-time continuity format change (that is `concurrency-safe-continuity`).
- No post-hoc backlog-coherence audit (that is `backlog-librarian`).
- No claim marker that itself becomes a write-conflict hotspot.

## Source

Wildcard run 2 (2026-07-24), owner-framed on parallel-agent continuity conflicts.
Distinct from `concurrency-safe-continuity` (merge-time format) and `continuity-sync-friction`
(sequential fetch-first) — it guards the selection moment upstream of both. Related:
`fleet-sourced-autonomous-batch`, `autonomous-advisory-dispatch-posture`, `dispatch-receipt-seam`.
