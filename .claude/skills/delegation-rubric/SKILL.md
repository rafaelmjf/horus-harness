---
name: delegation-rubric
description: >-
  Shared, data-backed reference for the two delegation-decision skills
  (`execution-decision` and `dispatch-decision`). It encodes ONE calibration +
  verification rubric: how to read `horus capabilities --models` (measured
  datums + owner priors from the empirical spine), turn a task shape into a mode
  + model-tier recommendation, and dial verification depth by how proven that
  tier is. NOT invoked on its own — the two decision skills load it so the logic
  lives in one place and a model re-tag (new datums) propagates to both flows.
  Advisory only: it EMITS a recommendation the agent applies; it never
  auto-selects a model or auto-routes a dispatch.
---

<!-- horus-skill-version: 7 -->

# Delegation rubric — shared calibration + verification logic

Single source of truth for the delegation-decision framework. Both
`execution-decision` (in-project, subagents substrate) and `dispatch-decision`
(cockpit, multi-project sessions substrate) LOAD this file and apply the steps
below. They differ only in their substrate and their mode vocabulary; the
calibration ladder and the verification logic are identical and live *here* — so
a model re-tag in the datums moves both flows at once, and the same tier-trust
sets BOTH the model pick AND how hard to verify.

## Hard boundary (do not cross)

This rubric is **advisory**. It produces a recommendation — mode + tier +
verification depth — that the agent reads and APPLIES. Nothing here auto-selects
a model, auto-routes a dispatch, or spends. `horus capabilities` stays
data-only: there is no `--for`/pick mode and you must not add one. Orchestration
is ceded to execution planes; Horus stays the memory plane that measures and
displays (drift trigger: `research/omnigent.md`).

## Precondition — prove delegation has a dividend

Before reading the model roster, define the bounded work unit and name what a
separate worker actually buys: context the current session avoids loading, useful
parallelism, or lower-tier savings. Compare that with the fixed tax of briefing,
reviewing, observing the gate, merging, and closing continuity.

- If the benefit is unclear or does not plausibly exceed that tax, stay inline and
  stop the routing analysis before selecting a model.
- Cross-project scope, multiple phases, and a desire to collect calibration data are
  not dividends by themselves.
- Decide per bounded unit, not once for an entire campaign. An integrated long-running
  session may be the cheapest place for cross-project judgment because it already
  holds the context that handoffs would discard.
- Never manufacture work or a worker solely to earn a datum.
- An explicit owner direction may instead optimize expiring isolated-account
  capacity or protect supervisor context. Label that as the dispatch basis; do not
  pretend it is a feature-economics dividend.

## Step 1 — Read the calibration data

Run `horus capabilities --models` (add `--stdout` for JSON). It is data only and
names no model to pick. Per model it reports:

- **`tier`** (owner prior) — the role the owner assigns: design/ambiguity/verify
  gate, scoped-impl lead, mechanical, frontier, codex, …
- **`clean_count` / `quality_datums`** (measured) — quality rate over only
  `clean` / `nudged` / `bounced`; `died_count` and `void_count` stay visible
  separately and never lower that denominator. `closed_datums` / `total_datums`
  still show how many runs were reviewed and seen overall.
- **`last_outcomes`** (measured, most-recent first) — the recent track record:
  quality outcomes only (`clean` / `nudged` / `bounced`).
- **`strength` / `caution` / `guard`** (owner priors, free text) — `caution` and
  `guard` are HARD constraints on how the model may be used.

Counts are not task-shape evidence by themselves. Read recent matching outcomes and
their notes, and keep measured datums distinct from explicit owner observations. If a
native usage signal is incomplete, stale, or temporarily lifted, an owner-provided
reading may override it for this decision; label the source rather than pretending the
telemetry was complete.

## Step 2 — Read the task shape (four axes)

- **Ambiguity** — is the goal + acceptance crisp, or exploratory/underspecified?
- **Volume** — a small localized change, or high-volume / repetitive work?
- **Runtime surface** — pure logic (tests are the gate), or a runtime/visual
  surface (server, UI, CLI UX) a human must eyeball?
- **Scope clarity** — are the files / blast-radius known and fenceable, or
  open-ended?

## Step 3 — Tier-trust ladder (data, not hardcode)

Trust is READ from the live data, never pinned to a model name or a count copied into
this skill:

- **Proven** = many `clean` closed datums with a clean recent `last_outcomes`
  streak. Trust it on work matching its `tier`.
  Well-matched proven work is the strongest delegation candidate.
- **Unproven** = 0–few quality datums. Prefer it ONLY on well-matched, scoped work
  where a clean gate will catch a miss — you are calibrating it, so the win is
  the datum as much as the output. Never hand an unproven tier a large/loose
  task.
- **Owner flags gate the pick.** A `caution` or `guard` is a hard constraint —
  read it before matching. A token-headroom guard, for example, takes the model
  off the table when the best available usage evidence says the ceiling is near.
- **Keep older-but-capable models in the roster.** A prior-frontier model
  does not stop being capable the day a newer model ships — it may still be the strongest AND
  cheapest fit for scoped/mechanical work. Don't drop a model from the ladder on
  recency alone: pick by capability-for-the-task, not by release date, and keep
  gathering datums on it so the ladder reflects measured reality instead of
  assumption.
- **Match tier to shape** (this mirrors the managed-block model-tier rule; the
  data tells you which concrete model fills each role now and how proven it is):
  design / ambiguity / the verify gate → the live design tier; most scoped
  implementation → the live scoped-implementation tier; mechanical verifiable
  sweeps → the live mechanical tier, never as the judgment gate.

## Step 4 — Shape → mode + tier

The mode *vocabulary* belongs to the consuming skill; the shared axis is:

- Small / ambiguous / exploratory / debugging → **stay inline** (orchestration
  overhead + judgment loss dominate; delegation buys little).
- High-volume / low-ambiguity / clear gate / fenceable scope → **delegate** to
  the best-matched tier from Step 3, then reproduce the gate.
- Large AND multi-phase / spans surfaces → **delegate as a phased plan only when**
  the phases are independently fenceable and the named context or parallelism
  dividend exceeds the supervisor tax; otherwise keep the integrated campaign inline.
- Runtime/visual surface where the *user* is the real reviewer → delegate the
  build, but the gate is the owner's eyeball, not a code read.

Pick the tier from Step 3: prefer a proven tier on matched work; an unproven
tier only on scoped work with a clean gate; respect every `caution` / `guard`.

## Step 5 — Verification depth, dialed by the SAME tier-trust

The pick and the verification are two ends of one lever: the less proven the
tier you chose, the harder you verify — because you are calibrating it.
Verification means **observing a deterministic gate you did NOT author** — never
re-running the worker's own narrative, never trusting a "tests pass" prose
claim, whoever wrote it.

- **Reproduction ≠ re-running the suite.** A *required* CI check green on the
  exact commit reproduces the test gate — don't re-run what it already covers.
  Reproduction is a deterministic signal you observe yourself.
- **Proven + gate green → just observe** the gate and move on. No line-by-line
  re-read; the diff review is for scope/risk, not as evidence it works.
- **Unproven → verify more:** observe the gate AND add one independent probe of
  the changed surface. You're building the datum, so spend a little more to
  trust the result — then close the loop with `horus datum close` so the next
  decision is better calibrated.
- **Runtime / visual surface → default to asking the OWNER** to eyeball it. A
  mocked test blesses nonexistent flags; only a live drive of the real surface
  counts. Self-probe only when the owner is away AND has pre-authorized it for
  this session.
- Each consuming skill adds its substrate-specific gate (in-project: run the
  gate at the phase boundary; overseer: observe required CI green on the merge
  SHA). The dial above is the same in both.

## Step 6 — Bind dispatch to explicit owner consent

Before any implementation worker is launched, present one exact consent envelope:

- agent and concrete model (not only a tier), effort, and account alias;
- current usage and reset evidence for that account, including source and freshness;
- bounded task, maximum attempts, expected dispatch dividend or owner-directed
  capacity/context override, and the deterministic verification gate.

The **concrete model** is the exact selector the target CLI will execute, which
is not always the same string as the Horus calibration key that names it in
history. Horus's calibration keys use a dotted `family-major[.minor]` shape;
Claude Code's own `--model` flag instead accepts a bare family alias or a full
dash-separated selector — the calibration-key spelling looks exact but Claude
Code rejects it before any work starts. `horus run` rejects a known
calibration-only Claude label before creating a worktree or session as a
backstop, but the envelope should already name the executable selector.

Wait for explicit owner approval of that envelope. Approval does not authorize a
different model, account, effort, task scope, or another attempt. Ask again before
any such change — including a corrected provider selector for the same intended
model; a provider failure never permits silent fallback. This approval is
the execution plane's responsibility—Horus records and displays evidence but never
authorizes, selects, or launches by itself.

Do not predict a per-task usage percentage. At completion, use the mechanically
captured start/end readings and `horus datum report`; show a delta only when Horus
labels fresh same-window isolated readings unconfounded. Otherwise report the actual
readings as unknown or confounded. Do not poll continuously or make another model call
for accounting.

## Step 7 — Emit the recommendation

Emit three things for the agent to APPLY (never auto-apply them):

- **mode** — in the consuming skill's vocabulary,
- **tier** — a concrete model, chosen from the data + shape,
- **verification depth** — observe-only vs observe+probe vs owner-eyeball, with
  the one deterministic gate you'll observe named explicitly.

For a dispatched mode, also emit the complete consent envelope from Step 6 and
state `awaiting owner approval`; never launch as part of the recommendation.

**When the mode is a dispatched one** (anything that spawns a tracked worker
rather than staying inline — `dispatched-worker`/`dispatched-plan` in
`dispatch-decision`'s vocabulary, `subagent-plan` in `execution-decision`'s),
also name the expected **dispatch dividend**: the context/detail the overseer
avoids by not implementing this inline, weighed against the fixed supervisor
tax every dispatch pays regardless of size — brief + review + gate + merge +
reinstall + datum/continuity close. Recommend dispatch only when the savings
plausibly exceed that tax, OR when parallelism / protecting the overseer's own
context was the explicit named benefit — say which one. `horus capabilities
--models`'s per-model cost glance (`dividend +P/~N/-Neg · oversight median: …`,
from `horus datum close --dividend`/`--oversight` — see `horus/datums.py`) is
the measured record of how that judgment actually played out on past
dispatches of this tier; read it as the closest thing to evidence before
naming the expected dividend. This stays advisory prose only, same hard
boundary as everything else here: no auto-scored dividend, no auto-routing —
the harness only ever RECORDS the closed `--dividend` judgment after the fact,
it never predicts or picks one up front.

Always show the live data and owner evidence that drove it, clearly labelled. The
agent decides and acts; you advise.

## v2 six-lane projects (fallback)

This rubric is **structure-agnostic** — it reads live `horus capabilities
--models` data and the task shape, not any `.horus/` lane file — so v2
(six-lane) and v3 (`PRD.md`) projects consume it identically. Nothing here
changes with the continuity structure.
