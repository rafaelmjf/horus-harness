---
name: cockpit-autonomous-dispatch-contract
description: >-
  Owner-invoked cockpit WORKFLOW that sequences the full autonomous-dispatch loop
  from a portfolio cockpit session (horus-agent): discover fleet backlog → pick a
  card → ready-gate its scope → decide mode/account/model/verification →
  dispatch now or schedule it (attachable + worktree, right account) → schedule a
  `horus supervise` to verify/merge/close or escalate. Use when the owner opens a
  cockpit and says "check the backlog, pick something, launch it (scheduled if
  asked) and have a supervisor close it out or ping me", or says
  "autonomous dispatch", "run the away-mode loop", "schedule and supervise a card".
  A THIN sequencer over existing machinery — it composes `dispatch-decision`
  (mode/account/tier/depth), `backlog-refine`/`scope-cards`/`pathfinder`/`roadmap-branches`
  (ready-gate), and the `horus envelope`/`schedule`/`run`/`supervise`/`notify`
  commands; it never re-implements them. Advisory and owner-gated at EVERY step:
  it proposes, the owner confirms each gate. It never selects a model, routes an
  account, or launches anything without the explicit consent envelope. Not
  continuous monitoring; single-machine, non-recurring dispatch only.
---

<!-- horus-skill-version: 5 -->

# Cockpit autonomous-dispatch contract

The pieces of the owner's loop exist as separate commands and skills; this ties them
into ONE contract a cockpit session follows to run scheduled, cross-account dispatch
with independent supervision. It is a **sequencer**, not new capability: every step
is an existing command or skill, and every step is **owner-gated** — the skill
*proposes*, the owner *confirms*. It never auto-ranks, auto-routes an account,
selects a model, or launches without the explicit consent envelope. Substrate rule:
harness owns capability, this skill lives in horus-harness, and horus-agent (which
never grows code) references it as its autonomous-dispatch entry point.

Run it from a **cockpit** session (horus-agent), fetch-first. The away-mode kit it
drives: `horus envelope`, `horus schedule`, `horus run --unattended`,
`horus supervise`, `horus notify`.

## The contract — seven gates, each owner-confirmed

### 1. Discover
Enumerate active work across the fleet, remote-authoritative:
`horus fleet --backlog --stdout` (or `horus resume --preflight --fleet`). Note any
**parallel-delivery** signal it surfaces (open sibling PRs, live co-sessions,
unconsolidated merges) — a card already in flight is not a candidate.

### 2. Pick
The owner selects, or the skill *proposes* a ranking by `priority` then age. Never
auto-pick.

### 3. Ready-gate (is the card dispatch-ready?)
Judge the card against **the execution-ready card contract in `backlog-refine`** —
that section is the single authority; do not maintain a rival checklist here. A
candidate must be `readiness: ready` and `autonomy: eligible`; missing readiness is
Unclassified and never scheduler-eligible. `autonomy: attended`, Shaping, Gated,
Deferred, and vision-branch umbrellas are not unattended candidates. If the
direction holds but the card is thin or Unclassified, STOP and route it through
`backlog-refine`. If the direction itself is unclear, use the full `pathfinder`
chain (`roadmap-branches` → `scope-cards` → `backlog-refine`). A fresh unattended
worker gets only the card, so the final contract must already be durable.

### 4. Decide
Invoke **`dispatch-decision`** for the recommendation: `inline-here` vs
`dispatched-worker` vs `dispatched-plan`, an isolated **account** routed AWAY from the
overseer (gated on `horus usage check --account <alias>` — never the account running
this cockpit), a tier→**model**, a verification depth, and the consent-envelope shape.
State plainly whether the card is *well-scoped-for-an-agent* or *needs-owner-supervision*.
This skill emits the recommendation; it never selects the model or account itself.

### 5. Authorize the standing envelope (the hard gate)
Nothing unattended runs without a bounded, expiring envelope. Create it explicitly:

```
horus envelope create <name> --expires <date> \
  --card <card> [--branch <vision-branch>] \
  --account <alias> --tier <tier> --effort <effort> \
  --usage-floor <pct> --max-attempts <n> --max-dispatches-per-day <n> \
  [--allow-merge]        # OMIT for verify+escalate-only (the safe default)
```

`--allow-merge` is the ONLY thing that lets a later `horus supervise` merge unattended;
omit it and the loop verifies + escalates but never merges. The envelope BOUNDS only —
it never selects the card, account, or model. Show the owner the exact envelope
(agent + model + account + effort + bounded task + usage evidence + acceptance gate +
dividend) and get approval before creating it. `horus envelope revoke <name>` grounds
pending work instantly.

**Why the default is verify+escalate, and what a brief must name.** The away-mode
drill ran two legs and answered its own readiness question: every required check
passed on both while both overwrote PRD continuity, in a surface no card named.
`--allow-merge` was correctly withheld. A worker records delivery facts — the SHA,
the PR, what the gate emitted — never a verdict on its own work; the supervisor
owns canonical continuity. That failure mode is addressable by instruction: the same
model and effort left `.horus/` untouched across a ten-step release once the brief
named it a hard constraint. **So name the off-limits surfaces explicitly in every
brief.** An unstated expectation is not a worker defect — but one clean run shows a
model can follow a runbook once, not that unattended release is safe.

### 6. Dispatch or schedule
Launch now, or schedule a one-shot on THIS machine (never cloud, never recurring):

```
# now:
horus run --unattended --envelope <name> --card <card> --account <alias> \
  --worktree auto/<card> --expect-delivery
# or later (away-mode):
horus schedule run --at '<+2h | 2026-07-22 09:00>' -- \
  'run <card>' --unattended --envelope <name> --card <card> --account <alias> --expect-delivery
```

`--unattended` already implies the attachable + `auto/<card>` worktree posture. Away-mode
needs linger (`loginctl enable-linger $USER`) so timers fire logged-out.

### 7. Pair a supervisor
Schedule a `horus supervise` after the worker's expected finish — the independent
accept/escalate gate (required CI on the exact SHA + freshness + the live probe):

```
horus schedule run --at '<after the worker>' -- \
  supervise --path <repo> '<session-or-pr>' --probe '<owner-authored live probe>'
```

`--probe` is REQUIRED for an authorized merge (owner-authored, machine-local — never a
committed command); without it supervise refuses to merge and escalates. On a red gate
it escalates through `horus notify` and halts scheduled dispatches that `depend-on` the
failed card. Verify the sink first: `horus notify show` / `horus notify test`.

## The loop back to the cockpit
A scheduled supervisor closes the loop without a human: on accept it merges + closes +
ships the card (so it drops out of step-1 discovery); on a problem it escalates via
`horus notify` and the next cockpit session sees the sibling via `horus resume` +
the parallel-delivery signal. Owner reads escalations on their phone; TUI + horus-agent
stay the work surface.

## Boundaries
- **Proposes, never performs.** Every gate above is presented for owner confirmation;
  the skill writes nothing and launches nothing on its own.
- **Never selects a model or routes an account** — that is `dispatch-decision`'s data
  and the owner's call; this skill only sequences.
- **Single machine, non-recurring.** Cloud dispatch and recurring timers are out of
  scope (the vision keeps the distributed execution plane out of scope).
- **Merge is opt-in** (`--allow-merge` on the envelope) and always gated behind a live
  probe; the default posture is verify + escalate only.

