---
status: open
priority: medium
created: 2026-07-17
tier: opus
type: feature
parallel: unsafe
phase: converge
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
created_by: owner
depends-on: unattended-escalation-channel, standing-dispatch-envelope
surface: new `horus supervise` subcommand; horus/cli.py; new horus/supervise.py; composes horus/mergewatch.py + horus/closure.py + horus/delivery.py + horus/registry.py + gh pr merge + horus/backlog.py (ship)
---

# supervise-verify-merge-close — unattended verify → merge → close → escalate for a dispatched card

**Why (owner, 2026-07-17):** a *scheduled* dispatch has no live supervisor watching it. The
owner wants a scheduled supervisor run that, after a worker finishes, **independently
verifies** the delivery and then either accepts it (merge + close + ship the card) or
**escalates** a problem — never trusting the worker's own "done". The harness already agrees:
`delivery-ready` is *"evidence for review, never acceptance or merge authority"*
(`horus/delivery.py:88-91`), and AGENTS.md's discipline is *"reproduce the gate; never trust
the report — watch a required CI check go green on the exact commit, plus one live probe."*
The verify primitives exist but nothing composes them into an unattended accept/merge flow,
and **there is no `horus merge`** (real merge = `gh pr merge`; `integration.integrate()`
auto-merge is wired to onboarding only). Part of the
`vision-branch-x3-scheduling-and-autonomous-execution` divergence.

## Idea

A `horus supervise <session-id|pr>` verb that runs the acceptance gate unattended:

1. Resolve the worker's delivery from the registry + post-hoc receipt (`horus sessions
   --json`, `horus/delivery.py:293-359`); require `--expect-delivery` was set and a
   `dispatch_base_sha` is pinned.
2. **Verify deterministically:** `horus merge-watch <pr|sha>` (required CI green on the exact
   head SHA, exit 0/1/2, `horus/mergewatch.py:315`) + `horus close --check --base-ref <base>`
   (freshness/continuity gate, `horus/closure.py:160-218`) + one live probe of the changed
   surface.
3. **On green:** `gh pr merge` (respecting the project's integration mode), then
   `horus close --commit --push` (supervisor owns canonical continuity — AGENTS.md) and
   `horus backlog ship <card> --pr <n> --sha <sha>` to archive the card.
4. **On red / uncertain:** do NOT merge; escalate via `unattended-escalation-channel` with the
   failing signal (which gate, which SHA, the receipt).

## Acceptance

- Given a delivered worker PR with required CI green, `horus supervise` merges it, closes
  continuity, and ships the card — with no human in the loop — and its exit code reflects
  accept vs escalate.
- Given a PR with a red required check or a failed freshness gate, it merges nothing and
  emits an escalation.
- It refuses to accept on worker self-report alone (no `--expect-delivery` / no pinned base
  → escalate, don't guess).
- **Andon:** an escalation halts every scheduled dispatch whose card `depends-on`
  (transitively) the failed card — no dependent work fires on top of a red base;
  independent scheduled work is unaffected. The halt is visible in
  `horus schedule list` with the blocking reason.

## Preconditions (not open questions)

- **The headless live-probe definition must be settled BEFORE implementation** —
  what deterministic probe of the changed surface a supervisor can run per project
  type (start with: this repo's pytest-required checks + one `horus <verb>` smoke
  of the changed surface). Until settled, this card ships verify+escalate-only:
  it may classify and escalate but NOT merge (the away-mode cut line, 2026-07-17).

## Open questions

- Should merge stay `gh pr merge` here, or should `integration.integrate()` be generalised
  beyond onboarding and reused? (Prefer reuse to avoid a second merge path.)
- Idempotency / re-run safety if a supervise run is itself scheduled and fires twice.

## Notes

- This is the step-10 glue in the branch card. `parallel: unsafe` (shares `horus/cli.py`).
  Depends on `unattended-escalation-channel` for the escalation path.
