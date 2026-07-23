---
status: open
priority: medium
created: 2026-07-23
created_by: agent
readiness: shaping
readiness_reason: "The advisory authority/output contract and whether read-only runs still need isolated worktrees require a focused probe."
phase: explore
type: bug
vision_facet: "Autonomous dispatch"
---

# autonomous-advisory-dispatch-posture — schedule zero-blast skills without a fake delivery card

## Why

`wildcard` and `backlog-librarian` both claim they can run as scheduled,
zero-blast-radius advisory jobs. Interactive use works, but the unattended
substrate only understands delivery work:

- `--unattended` requires an envelope.
- An envelope requires an active backlog card.
- Unattended runs become workers with an `auto/<card>` worktree.
- Delivery outcomes assume branch/commit/PR evidence.

That contract is honest for implementation cards, but not for an advisory skill
whose only output is a proposal, digest, or run log. `backlog-librarian` is now
archived, so it cannot itself be the active card authorizing later runs; using
an unrelated card would misstate what the envelope authorized.

## Rough shape

Add one bounded `advisory` dispatch intent to the existing envelope/run
substrate:

- Bind authority to an exact project-local skill name/version, account, tier,
  effort, expiry, and maximum runs.
- Preserve usage gates, detached tmux visibility, revocation, and attempt limits.
- Record `advisory-complete|failed`, never `delivery-ready`.
- Grant no branch, commit, PR, merge, card-edit, or continuity authority.
- Decide whether v1 is strictly read-only with output only in the run log, or
  permits one explicitly bounded receipt path such as `.horus/audits/`.
- Reuse `horus schedule run`; add no scheduler or recurrence engine.

## Acceptance direction

A scheduled `wildcard` or `backlog-librarian` run can execute under an exact
owner-created envelope without inventing an implementation card or receiving
delivery authority. Attempts to write outside the declared output boundary are
refused, and Mission Control shows the result as advisory—not delivered work.

## Open questions

- One strictly read-only intent, or separate `read-only` and `receipt-only` forms?
- Is skill name/version sufficient, or must the envelope also pin the prompt?
- Does an advisory run still merit an isolated worktree for containment?
- Where does the owner review the output: run log, receipt shelf, or both?

## Non-goals

- No arbitrary unattended prompts.
- No autonomous acceptance or backlog mutation.
- No merge/supervision authority.
- No new session-mode axis.
- No recurring scheduler.

## Source

Live `wildcard` run, 2026-07-23, grounded in the scheduled claims of `wildcard`
and `backlog-librarian` versus the current `horus run --unattended` envelope,
active-card, worker, and worktree requirements. Owner accepted the proposal on
2026-07-23. Related: `wildcard`, `backlog-librarian`,
`autotest-e2e-away-mode-drill`, `dispatch-receipt-seam`.
