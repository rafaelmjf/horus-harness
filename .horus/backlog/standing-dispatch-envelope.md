---
status: open
priority: high
created: 2026-07-17
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
phase: converge
tier: opus
type: feature
parallel: unsafe
created_by: owner
surface: PRD.md Rules (delegation amendment), horus/run_executor.py + new horus/schedule.py + new horus/supervise.py consent checks, ~/.horus/ machine-local envelope store, dispatch-decision/horus-execution skills
---

# standing-dispatch-envelope — bounded pre-authorization for unattended dispatch

**Why (owner decision pending design, 2026-07-17):** the delegation rule requires
explicit owner approval of the *exact envelope per launch* — correct for attended
work, impossible for an unattended loop (owner away 2026-07-22, 6 days). The X3
loop must not silently route around that rule: the fix is a **standing envelope** —
a bounded, owner-created authorization artifact that scheduled dispatch and
supervision *validate against and refuse to exceed*. This is item 0 of the X3 kit:
`schedule-local-dispatcher` and `supervise-verify-merge-close` both check it before
acting; nothing unattended runs without one.

## Idea

A machine-local envelope record (never in git — it names accounts) the owner
creates explicitly (e.g. `horus envelope create`), carrying at minimum:

- **Card whitelist** — exact card names (or a named vision branch) this envelope
  authorizes; nothing outside it is schedulable.
- **Account set + usage floor** — which isolated accounts may be used, with a
  reserve floor (e.g. "stop dispatching below 30% remaining in the window").
- **Model-tier ceiling + effort cap** — the maximum tier a scheduled run may use;
  tier comes from the card, capped here.
- **Attempt allowance** — max attempts per card and max total dispatches per day,
  so a bouncing worker cannot burn the trip's capacity.
- **Expiry** — envelopes are time-boxed (e.g. the trip window) and die at expiry;
  no evergreen standing authority.
- **Merge authority flag** — whether `horus supervise` may merge on green gates,
  or must stop at verify+escalate (the away-mode cut-line default).

Refusal semantics: `horus schedule` refuses a dispatch outside the active
envelope; `horus supervise` refuses to merge beyond it; both name the violated
bound. The envelope is read at fire time, so cancelling it (`horus envelope
revoke`) instantly grounds all pending scheduled work — the owner's kill switch.

## Acceptance

- The delegation Rules amendment is written: per-launch approval OR an explicit,
  bounded, expiring standing envelope; changing any bound requires a new envelope.
- A scheduled dispatch inside the envelope launches; one outside it (wrong card,
  exhausted attempts, account below floor, expired envelope) is refused with the
  exact violated bound, and the refusal is visible in `horus schedule list` and
  the escalation channel.
- Revoking the envelope grounds all pending scheduled dispatches without killing
  live attached sessions.
- No envelope content (accounts, thresholds) is ever committed to a project repo.
- Tests cover: in-bounds launch, each refusal class, expiry, revocation, and the
  merge-authority flag gating `horus supervise`.

## Non-goals

- Not a router or policy engine — the envelope only *bounds*; card/tier/account
  selection still happens in the cockpit contract with the owner (or per the
  card's stamps) before scheduling.
- No auto-renewal, no learning, no spend estimation — hard bounds and refusals
  only, per the calibration rules (never estimate task usage, never auto-route).

## Reviews

- 2026-07-17 — **Built; two design changes and two deferrals.** (1) The guard binds
  at `horus run` (`cli._envelope_guard`), not in `schedule.py`/`supervise.py` as this
  card's `surface` line proposed — a wrapper-level check is bypassed by any cron entry
  or dispatcher bug calling `horus run` directly, so the bound sits where the worker
  launches. Items 2/4 become thin callers and inherit it for free. (2) The tier bound
  is an **allow-list of `tier:` labels, not an ordered ceiling**: `vendor-neutral-delegation-tiers`
  is about to replace opus/sonnet with low/medium/high/frontier, and an allow-list bounds
  exactly as hard without this module owning a total order that card will redefine.
  Deferred, genuinely blocked on later kit items: refusals are visible in `horus envelope
  show`/`list` but not yet in `horus schedule list` (item 2) or the escalation channel
  (item 3) — both should surface the `Refusal.bound` string, which is machine-readable
  for exactly that. Known seam for `vendor-neutral-delegation-tiers` to close: the
  envelope bounds the **card's** tier, while `--model` still passes through unbounded
  (model→tier mapping is that card's to own).
