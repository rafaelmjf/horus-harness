---
name: dispatch-decision
description: >-
  Decide HOW to dispatch a unit of work from the multi-project cockpit on the
  sessions substrate: recommend `inline-here` vs `dispatched-worker` vs
  `dispatched-plan`, which ACCOUNT to route it to (away from the overseer
  account, gated on `horus usage check`), a model tier, and a verification
  depth. Use this when triaging cross-project work from an overseer/cockpit
  session — picking whether to do it here, hand it to a tracked `horus run`
  worker, or stand up a phased plan. It reads live calibration data (`horus
  capabilities --models`) through the shared delegation rubric. Advisory: it
  EMITS a recommendation you apply — it never auto-selects a model, auto-routes
  an account, or auto-spawns a worker. For choosing how to execute inside a
  single repo use `execution-decision` instead.
---

<!-- horus-skill-version: 4 -->

# Dispatch decision (cockpit / multi-project, sessions substrate)

Substrate: an overseer/cockpit session triaging work across many registered
projects, dispatching tracked sessions via `horus run --account <alias> --path
<repo>`. Work lands back via PR + CI. This skill is the thin cross-project
consumer of the shared rubric — it adds the dispatch mode vocabulary, account
routing, and one substrate note.

## Load the shared rubric first

Read **`../delegation-rubric/SKILL.md`** and apply its dividend precondition plus
seven steps. All calibration, consent-envelope, and verification-depth logic
live there; do not restate or fork it.

## Mode vocabulary (this skill's output for the rubric's Step 4 axis)

- **`inline-here`** — do it in the overseer session. The rubric's "stay inline"
  case (small / ambiguous / exploratory / debugging), plus integrated campaigns
  where the current session already holds context that a handoff would discard.
  Overseer usage is a cost to weigh, not a presumption that dispatch is better.
- **`dispatched-worker`** — one tracked `horus run` worker for a bounded,
  fenceable, clear-gate task. The rubric's "delegate" case.
- **`dispatched-plan`** — a phased plan (orchestrator > supervisor > worker, one
  worktree per worker) for large multi-phase work whose independently fenceable
  phases have a named context or parallelism dividend that exceeds the supervisor
  tax. Cross-project scope alone is insufficient.

Do not dispatch merely to collect a datum. Calibration is a useful by-product of
real work, never the reason to create a worker.

## Account routing (cockpit-specific, on top of the rubric)

- **Route away from the overseer account.** A dispatched worker runs on an
  ISOLATED account (a `horus account` alias → its own `CLAUDE_CONFIG_DIR` /
  `CODEX_HOME`), never the ambient overseer login — that keeps the overseer free
  AND, on a tiered setup, buys the cheaper-tier × separate-account double win.
- **Gate the target account on `horus usage check`** (`--target claude|codex`
  for the worker's agent). If the chosen account is near a closure threshold,
  pick another isolated account or hold the dispatch — and heed the rubric's
  `guard` flags. This is a check you OBSERVE, not an auto-throttle. When native
  telemetry is incomplete or temporarily lifted, accept a current owner-provided
  reading as the routing signal and label that override explicitly.
- An owner may explicitly choose an account to spend capacity before its reset or
  protect the overseer context. This supplies the dispatch basis, but does not waive
  the exact-envelope approval or authorize a silent fallback.

## Overseer verification note (the substrate specialization of rubric Step 5)

Dispatched work lands via **PR + CI**, so the deterministic gate already exists
remotely: **OBSERVE the required CI check green on the merge SHA** — roughly one
`gh` call (`gh pr checks` / the run conclusion on the head SHA). Do NOT re-run
the suite locally; a required check green on the exact commit already reproduces
the test gate. Dial by tier-trust as the rubric says: a proven worker → observe
CI green and accept; an unproven worker → observe CI green AND drive one live
probe of the changed runtime surface (a mocked green never blesses a runtime
flag), then `horus datum close` the run. A runtime/visual surface still defaults
to the owner's eyeball.

## Emit (advisory — you apply it, nothing here auto-runs)

`mode` (`inline-here` | `dispatched-worker` | `dispatched-plan`) + `account`
(which isolated alias, or "hold — usage") +
`tier` (a vendor-neutral capability point — `low|medium|high|frontier` —
resolved to a concrete provider+model only in the consent envelope, from the
neutral-tier map + the target account's live capacity,
never defaulted from the label) + `verification depth` (observe-CI |
observe-CI+probe | owner-eyeball). Show the calibration + usage/reset evidence that
drove it. The account and the provider are the SAME decision here: a `medium` card
can run on Claude (Sonnet) or the equivalent Codex model — pick the one whose
isolated account has capacity, don't let the old vendor-named label choose. For
either dispatched mode, present the full consent envelope from the rubric and
stop for explicit owner approval. Any changed model/account/effort/scope or additional attempt requires a new
approval; provider errors never authorize fallback. Selecting the account, spawning
the worker, and observing CI are all YOUR actions — this skill recommends; `horus`
never auto-routes a dispatch (the hard boundary: `research/omnigent.md`).

## v2 six-lane projects (fallback)

Structure-agnostic: this skill operates at the cockpit level across projects and
reads live `horus` data + the task shape, not any `.horus/` lane file. v2 and v3
projects are dispatched identically.
