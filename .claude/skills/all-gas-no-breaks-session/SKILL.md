---
name: all-gas-no-breaks-session
description: >-
  The minimal-orchestration posture loaded only when the owner launches an `All Gas
  No Breaks` session. Work directly on the authorized request or resume handoff,
  avoid automatic Horus process skills and ceremony, and preserve deterministic
  delivery safety. This mode never removes hard-boundary continuity: consolidate
  before a release and at session closure, pause, or handoff. Do not invoke this
  skill from task shape alone; the launch-mode selection is its trigger.
---

<!-- horus-skill-version: 1 -->

# All Gas No Breaks session

Work directly. The owner selected this mode to remove orchestration overhead, not
to expand your authority.

## Start and execute

- Obey repository instructions, fetch and verify remote state, then read only the
  minimum project context needed for the request.
- Treat the current request or authored resume handoff as authorization to proceed;
  do not stop for a preflight summary or permission ceremony.
- Prefer direct inspection, editing, and testing. Do not manufacture backlog cards,
  execution plans, audits, retrospectives, or session notes.
- Do not load Horus decision, dispatch, planning, curation, or grooming skills unless
  the owner explicitly requests that workflow. Delegation remains owner-invoked.

## Keep the useful rails

- Follow the repository's branch and delivery policy. Keep recoverable pushed
  checkpoints when work spans more than one meaningful step.
- Reproduce the deterministic gate on the exact commit and perform one proportional
  live probe of the changed surface before calling work done.
- Minimal orchestration is not broader permission: do not infer authority for
  destructive operations, delegation, merge, release, deployment, or external side
  effects that the owner did not grant.

## Hard boundaries still consolidate

A release, session closure, pause, or agent/account/machine handoff is a hard
continuity boundary. At that boundary invoke `horus-consolidate`, fold the durable
campaign outcome into the project's canonical continuity, and run the repository's
normal close flow. Do this once at the boundary, never between ordinary fixes merely
because a commit or PR finished. If releasing, consolidate before publishing so the
release and hosted deployment carry current continuity.

## v2 six-lane projects (fallback)

Use the same direct posture. At a hard boundary, `horus-consolidate` updates the v2
lanes instead of `PRD.md`; the boundary is mandatory even though intermediate
ceremony remains suppressed.
