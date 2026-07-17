---
status: open
priority: low
created: 2026-07-18
tier: sonnet
type: chore
parallel: unsafe
created_by: owner
depends-on: rehearsal-mergeable
surface: none — no-op fixture; exists only to be halted by the andon
---

# rehearsal-dependent — throwaway fixture to observe the andon halt

**THROWAWAY.** This card exists only so the `x3-away-mode-kit-e2e-rehearsal` can watch
the andon fire. It `depends-on: rehearsal-mergeable`. Delete it once the rehearsal is
done.

## What the worker should do

Nothing of substance. If this card is ever actually dispatched (it should not be during
Pass A), it may create `docs/away-mode-rehearsal-dependent.md` with a single line. But
the whole point is that it **never runs**: when `rehearsal-mergeable`'s gate goes red in
Pass A, `horus supervise`'s andon must disarm this card's scheduled dispatch before it
fires.

## Acceptance

- With `rehearsal-mergeable` red in Pass A, this card's scheduled dispatch appears
  **disarmed / blocked** in `horus schedule list` and never launches a worker.
- Delete this fixture after the rehearsal.

## Non-goals

- Not real backlog work.
