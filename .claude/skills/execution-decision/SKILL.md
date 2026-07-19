---
name: execution-decision
description: >-
  Decide HOW to execute an in-project task on the Claude/Codex subagents
  substrate: recommend `inline` vs `subagent-plan`, a model tier, and a
  verification depth. Owner-invoked only: use this ONLY when the owner explicitly
  asks whether or how to delegate, hand work to a worker/subagent, or prepare a
  delegated execution plan. Do not trigger it for ordinary feature/fix planning,
  merely because `execution_recommendation` needs setting, or because the agent
  wonders whether delegation might help; stay inline without loading it. It reads
  live calibration data (`horus capabilities --models`) through the shared
  delegation rubric. Advisory: it EMITS a recommendation you apply — it never
  auto-selects a model or auto-spawns a worker. For cross-project cockpit dispatch
  use `dispatch-decision` instead.
---

<!-- horus-skill-version: 5 -->

# Execution decision (in-project, subagents substrate)

Substrate: one repo, one working session, with native subagents / `horus run`
workers available. You are choosing how to execute the NEXT in-project unit of
work. This skill is the thin in-project consumer of the shared rubric — it adds
the in-project mode vocabulary and one substrate note, nothing else. It pairs
with `horus-execution`, which supervises the plan once you've decided to
delegate.

## Invocation boundary

An ordinary request to build, fix, review, or plan work authorizes inline work; it
does not authorize delegation and does not trigger this skill. Do not load this
skill merely to populate `execution_recommendation`, at every planning boundary,
or to validate an obvious inline choice. Load it only after the owner explicitly
asks whether/how to delegate, requests a worker/subagent, or requests a delegated
execution plan.

## Load the shared rubric first

Read **`../delegation-rubric/SKILL.md`** and apply its dividend precondition plus
seven steps (read the data, read the task shape, the tier-trust ladder,
shape→mode+tier, verification depth, bind consent, emit). Everything about reading
`horus capabilities --models` and dialing
verification by tier-trust lives there — do not restate or fork it here.

## Mode vocabulary (this skill's output for the rubric's Step 4 axis)

- **`inline`** — do it in this session. The rubric's "stay inline" case: small,
  or ambiguous/exploratory, or debugging. On a single-model runtime (no cheaper
  worker tier reachable) inline is also right unless volume would flood the
  context window — delegation then buys only context hygiene.
- **`subagent-plan`** — delegate to a bounded subagent / `horus run` worker (one
  phase at a time) via `horus-execution` / `execution.md`. The rubric's
  "delegate" and "delegate as a phased plan" cases: high-volume, low-ambiguity,
  fenceable scope, clear gate. Name the tier from the data and set
  `delegation_basis` to what delegation actually buys here (context hygiene, and
  on a tiered runtime a cheaper implementation tier).

Feed the recommendation into `execution_recommendation` (`continue-as-is` ≈
`inline`; `plan-execution` ≈ `subagent-plan`) and, when delegating, into the
`execution.md` phase's `worker_tier` / `delegation_basis`.

## In-project verification note (the substrate specialization of rubric Step 5)

CI has NOT run yet inside the session — there is no merge SHA to observe. So the
supervisor **RUNS the gate at the phase boundary** (the handoff note's one gate
command + one live probe of the changed surface) and **TRUSTS the code** —
reviews the diff for scope/risk, not line-by-line as evidence it works. Dial by
tier-trust exactly as the rubric says: a proven worker → run the gate once and
observe; an unproven worker → run the gate AND add an independent probe, then
`horus datum close` the run so the tier earns a real datum. A runtime/visual
surface still defaults to the owner's eyeball.

## Emit (advisory — you apply it, nothing here auto-runs)

`mode` (`inline` | `subagent-plan`) + `tier` (a vendor-neutral capability point —
`low|medium|high|frontier` — resolved to a concrete provider+model only at the
consent envelope, from the neutral-tier map + live capacity,
never defaulted from the label) + `verification depth`
(observe-only | observe+probe | owner-eyeball,
with the gate command named). For `subagent-plan`, include the exact agent/model/
effort/account/usage+reset/task/attempts/dividend-or-owner-override/gate consent
envelope, mark it awaiting explicit owner approval, and ask again on any
fallback or extra attempt. Spawning the subagent, selecting the model, and running
the gate are all YOUR actions — this skill recommends, it does not route.

## v2 six-lane projects (fallback)

Structure-agnostic except where the recommendation lands: on a v3 project the
`execution_recommendation` field is in `PRD.md` frontmatter; on a v2 (six-lane)
project it's in `roadmap.md`. The decision logic, the shared rubric, and the
modes are identical.
