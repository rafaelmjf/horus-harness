---
status: retired
priority: medium
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: delegation-rubric (skills.py), horus/cli.py (capabilities surface), dispatch-decision
shipped:
---

> Retired 2026-07-14 (owner triage): live counts already expose trust depth and the
> delegation rubric permits scoped calibration of unproven tiers. Exploration should
> happen opportunistically on fair low-risk tasks, not become another product surface,
> unless a concrete selection failure proves the current signal insufficient.

# Surface under-sampled models — counter the survivorship trap in dispatch

**Owner insight (2026-07-12):** nearly every run so far went to Sonnet-5 and came back
clean, which makes it *look* like a clear winner — but that's survivorship. Without
deliberately delegating well-matched tasks to cheaper/lower or GPT models, we can never
expand the pricing/capability picture. The dispatch guidance must balance **exploit**
(use the proven model) with **explore** (gather data on under-sampled ones).

## Scope

- The `delegation-rubric` already nudges "least-proven → prioritise well-matched scoped
  tasks" — make it **active and visible**, not just prose:
  - Surface an **under-sampled** signal in `capabilities --matrix`/`--models` (e.g. flag
    models with few closed datums relative to the roster), so the agent SEES which
    models need data at decision time.
  - In the rubric / `dispatch-decision`, when a task is well-matched to an
    under-sampled model, recommend it as an **exploratory** dispatch (clearly labeled
    explore-not-exploit), so the owner can choose to spend a low-risk task on data.
- Keep it **advisory** — it recommends an exploratory candidate; it never auto-routes.
  Respect budget (`horus usage check`) and task-fit (a fair test, not a rigged failure).

## Gated by

`model-availability-lifecycle` — do NOT recommend exploring a model that's about to be
retired (wasted data). Feeds `model-ranking-synthesis` (a ranking on exploited-only
data is biased; exploration widens the base).

## Verification

A roster fixture with a lop-sided datum distribution surfaces the under-sampled models;
the rubric/dispatch-decision output labels an exploratory recommendation distinctly from
an exploit one; no auto-route. CI green.
