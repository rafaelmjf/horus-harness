---
status: open
priority: low
created: 2026-07-18
tier: sonnet
type: chore
parallel: unsafe
created_by: owner
surface: docs/away-mode-rehearsal.md (new throwaway file — no source touched)
---

# rehearsal-mergeable — throwaway fixture for the X3 away-loop e2e rehearsal

**THROWAWAY.** This card exists only to give the `x3-away-mode-kit-e2e-rehearsal`
loop a real, genuinely-mergeable, zero-risk change to dispatch. Delete this card (and
the file it creates) once the rehearsal is done.

## What the worker should do

Create a new file `docs/away-mode-rehearsal.md` containing exactly one line:

```
X3 away-mode e2e rehearsal marker — <UTC timestamp of this run>.
```

That is the whole change. A brand-new file touches no existing code, cannot conflict,
and passes `pytest` trivially — so the PR is genuinely safe to merge unattended.

## How the rehearsal uses this card (two passes)

- **Pass A — escalate (no `--allow-merge`):** dispatch this card, then deliberately
  turn its gate red (e.g. push one extra commit to the worker branch that adds a
  failing test, or point `supervise` at the run before CI is green). `horus supervise`
  must reproduce the red gate, refuse, and **escalate to `@horus_agent_rmjf_bot`**;
  the scheduled `rehearsal-dependent` dispatch (which `depends-on` this card) must go
  **disarmed** in `horus schedule list` (the andon).
- **Pass B — merge (`--allow-merge` + `--probe`):** dispatch this card clean on an
  envelope created with `--allow-merge`, and `supervise --probe 'python -m pytest -q'`.
  On green CI + passing probe it must **merge + close + ship** with no human mid-run.

## Acceptance

- Pass A produces a real Telegram escalation and a visible dependent halt.
- Pass B merges the one-line-doc PR unattended and archives this card.
- Any divergence from designed behavior becomes its own bug card (the rehearsal's
  real output). Then delete this fixture and `docs/away-mode-rehearsal.md`.

## Non-goals

- Not real backlog work. Do not build on `docs/away-mode-rehearsal.md`.
