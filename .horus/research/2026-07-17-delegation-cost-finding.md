# Delegation cost finding — dispatch did not save cost; it raised it

**Date:** 2026-07-17
**Type:** empirical finding / retrospective (owner-directed measurement)
**Status:** durable background context. Referenced from `PRD.md` (Shipped correction + the
delegation Rule). Not a facet or a spec — a data point that constrains how we reason about
delegation cost.

## One-line conclusion

On this session's evidence, **delegation is not a cost lever — it is a time-shift /
capacity-arbitrage / parallelism lever.** Dispatching well-scoped cards to fresh headless
workers *raised* total consumption versus doing the same class of work inline, even with
mid-tier (sonnet/medium) workers. Opus/high workers would raise it further.

## What we measured

Two comparable bodies of work in one session, same machine, same codebase:

- **Inline (work account, opus/high):** shipped X3 away-mode kit items 3–6 — the `notify`
  module, the `supervise` module + `schedule.halt` andon, the `closure` parallel-delivery
  signal, and the `cockpit-autonomous-dispatch-contract` skill (each with tests). This was
  the *larger* body of code. The work account sat around **56–60%** when delegation began.
- **Dispatched (claude-personal, sonnet/medium):** 4 smaller well-scoped cards —
  `tui-branch-tree-glance` (#303), `stale-datum-usage-overlap-reconciliation` (#304),
  `tui-launch-model-effort-selection` (#305), `parallel-signal-informational-not-verdict`
  (#306). All delivered cleanly, attempt 1/1, zero supervisor corrections.

### The personal-account 5h window across the four dispatches

| checkpoint | tui-tree #303 start | stale-datum #304 start | tui-launch #305 start | now (after #306) |
|---|---|---|---|---|
| **5h window** | 1% | 24% | 46% | **81%** |
| implied per-step Δ | — | +23pp | +22pp | +35pp (#305+#306) |

- Each sonnet/medium worker consumed **~20–25pp of a 5h rate window**; the four together
  used **~80% of one 5h window** in ~**40 min** of total agent wall-time
  (runtimes: 12m41s / 10m18s / 12m46s / 4m10s).
- The **weekly** window barely moved (14% → 19%), so the cost landed on the 5h window.

**Net:** inline shipped *more* code for ~60% of a window on a *pricier* model (opus/high);
dispatch shipped *less* for ~80% of a window on *cheaper* models (sonnet/medium). Delegation
was less efficient per unit of output — the opposite of the "cheaper worker saves money"
intuition.

## Why — the hidden costs (owner's hypothesis, confirmed)

1. **Cold-start context reload, paid N×.** Each fresh worker rebuilds the whole mental
   model from zero: reads CLAUDE.md, explores the repo, learns the card's surface, traces
   the code it must touch — *before* writing a line. An inline session amortizes this: one
   context load (which *compounds* as the session grows) serves many cards; item 4 reused
   item 3's loaded understanding of cli.py/run_executor, etc. **4 cold starts ≫ 1 warm
   continuation.** This is the dominant term and the owner's stated intuition: the inline
   opus session's compounding context is precisely what avoids re-reading code per task.
2. **Verification is done twice.** The worker implements; then the supervisor independently
   re-reads the diff, runs the gate, watches CI, and reasons about correctness. Inline,
   verification folds into the doing. Dispatch adds a whole second reasoning pass (worker's
   tokens + supervisor's tokens) per card.
3. **No parallelism recovered.** The one thing that offsets the overhead — concurrent
   workers — was impossible: the *one-live-agent-process-per-account-config-dir* invariant
   forced **sequential** dispatch to the single personal account. So we paid all the
   overhead and captured **none** of the wall-clock/throughput benefit.
4. **Defensive over-exploration.** A headless full-auto worker with no owner to steer tends
   to read more broadly and re-run the suite more times than a steered inline session would.

## This batch was the worst case for delegation

All three legitimate dividends were *absent*: the owner was present (no time-shift needed),
the primary account was healthy at ~60% (no capacity pressure), and work ran sequentially on
one account (no parallelism). So it incurred full overhead for zero offsetting benefit. The
clean 4/4 *delivery* result is real and worth keeping — mid-tier workers handled well-scoped,
self-sufficient cards without a bounce — but delivery quality ≠ cost efficiency.

## When delegation IS worth the markup (narrow)

- **Time-shift** — run while the owner is asleep/away and literally cannot supervise inline
  (the away-mode kit's real reason). You pay the markup to get unattended progress.
- **Capacity arbitrage** — only when the primary account is genuinely near a limit and a
  secondary is idle: spend the idle budget at a markup because the alternative is not
  working at all. Useless when the primary has headroom (as here).
- **True parallelism** — N independent cards on N *distinct* accounts concurrently, for
  wall-clock speedup. Needs multiple accounts + independent work; a single account is
  strictly sequential and captures none of it.

This confirms (does not overturn) the existing delegation Rule: *integrated campaigns may be
cheaper inline; owner-directed dispatch spends expiring capacity or protects supervisor
context.* The earlier PRD Shipped note ("data point favors offloading…") over-weighted
delivery quality and under-weighted cost; corrected there.

## Caveats on the measurement (honest limits)

- A 5h-window **percentage is a fraction of a rate limit, not raw tokens** — a proxy for
  felt cost, roughly monotonic within a window, not an exact token count.
- The two bodies of work are **not identical** — the comparison is directional, not
  controlled. (It is directionally strong: pricier model inline did *more* for *less*.)
- Worker **end-readings were unavailable** (headless workers get no pushed statusline; the
  OAuth read is flaky), so per-worker deltas are inferred from consecutive *start* readings —
  reasonable but not exact. This confounding is exactly what card #304 now surfaces.
- The opus run `68c07a22` (7m55s, +17pp 5h) is **excluded**: its weekly baseline (26%)
  places it in an earlier window, not this batch.

## Forward ideas this raised (see backlog)

- **Per-launch continuity posture** — surface the existing `handoff`/`delivery` granularity
  as a launch-time choice (alongside the account/model/effort picker) so "batch to closure"
  vs "per-card" is set at launch without re-stating it. Largely exposes an existing control;
  small. (Assessment pending — may not need a new mechanism.)
- **Semi-inline supervised warm worker** (`explore` card) — instead of N cold headless
  workers, launch ONE worker that holds context across cards while a supervisor model steers
  it (simulating the owner) and it ships several cards before one continuity closure. Directly
  targets hidden cost #1 (kills the cold-start-×N tax) while staying delegated/unattended.
  A PoC to test whether warm-context sequential delegation beats headless-per-card on cost.
