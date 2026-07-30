---
name: execution-decision
description: >-
  Decide HOW to execute an in-project task: recommend `inline` vs
  `native-subagent` (a child of THIS session, same account) vs `horus-worker` (a
  tracked external agent-CLI session that may use another provider/model/account),
  plus a model tier and a verification depth. Owner-invoked only: use this ONLY
  when the owner explicitly
  asks whether or how to delegate, hand work to a worker/subagent, or prepare a
  delegated execution plan. Do not trigger it for ordinary feature/fix planning,
  merely because `execution_recommendation` needs setting, or because the agent
  wonders whether delegation might help; stay inline without loading it. It reads
  live calibration data (`horus capabilities --models`) through the shared
  delegation rubric. Advisory: it EMITS a recommendation you apply — it never
  auto-selects a model or auto-spawns a worker. For cross-project cockpit dispatch
  use `dispatch-decision` instead.
---

<!-- horus-skill-version: 6 -->

# Execution decision (in-project)

You are choosing how to execute the NEXT in-project unit of work. This skill is
the thin in-project consumer of the shared rubric — it adds the in-project mode
vocabulary and one substrate note, nothing else. It pairs with
`horus-execution`, which supervises a **Horus worker** plan once you've decided
to delegate to one.

## Two substrates — decide this BEFORE reading any usage data

"Delegate" is not one thing here. One repo and one working session can reach two
different substrates, with different costs and different consent requirements:

| | **Native subagent** | **Horus worker** |
|---|---|---|
| What it is | a child of THIS session (Claude's Task/Agent tool, Codex's own agent spawning) | a tracked external agent-CLI session (`horus run`) |
| Provider / account | normally the same runtime and the same account | may be another provider, model, account, or worktree |
| Coordination | the agent CLI's own collaboration contract; supervisor synthesizes | usage/account consent envelope, receipts, `horus-execution` / `execution.md` |
| Consent needed | the owner's request to use one | the full model/account/usage envelope, approved before launch |

**Delegation authorization is bounded to the substrate the owner named.** "Use a
subagent for this" authorizes a child of this session — it is **not** permission
to launch another provider or spend another account's budget. Only an explicit
external-worker request ("run this through Horus on the <account> account")
opens the `horus run` path.

So: if the owner says "subagent", or asks whether "lower models" could do
something, and has **not** identified the substrate — **ask one clarification
question first**, before reading another account's usage or drafting a dispatch
envelope. Answering the wrong substrate is the observed failure (2026-07-29): a
question about Codex's own agent spawning was answered with a Haiku-on-another-
account `horus run` proposal, which was internally consistent and still not what
was asked.

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
- **`native-subagent`** — hand a bounded task to a child of this session, and
  synthesize its result here. The rubric's "delegate" case when what delegation
  buys is **context hygiene**: high-volume, low-ambiguity, fenceable scope, clear
  gate, but no reason to leave this account or runtime. Uses the agent CLI's own
  collaboration contract — **no `horus run`, no account switching, no
  `execution.md`, and no Horus usage routing**. Cost grounding still applies, via
  that native contract rather than a manufactured worker envelope.
- **`horus-worker`** — delegate to a tracked external agent-CLI session (one
  phase at a time) via `horus-execution` / `execution.md`. Choose this only when
  the dividend actually requires *leaving this session*: a cheaper implementation
  tier, another account's capacity, a separate worktree, or time-shifted
  unattended work. Name the tier from the data, set `delegation_basis` to what
  the move buys, and bind the model/account/usage consent envelope before launch.

Feed the recommendation into `execution_recommendation`: **both `inline` and
`native-subagent` map to `continue-as-is`** — a native child is still this
session, so it needs no execution plan — and only `horus-worker` maps to
`plan-execution`, which then carries the `execution.md` phase's `worker_tier` /
`delegation_basis`. Writing `plan-execution` for a native subagent would invite a
later session to stand up worker machinery nobody authorized.

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

`mode` (`inline` | `native-subagent` | `horus-worker`) + `tier` (a vendor-neutral capability point —
`low|medium|high|frontier` — resolved to a concrete provider+model only at the
consent envelope, from the neutral-tier map + live capacity,
never defaulted from the label) + `verification depth`
(observe-only | observe+probe | owner-eyeball,
with the gate command named). Name the **substrate** explicitly in the emit, so
the owner can see which one they are approving.

For `horus-worker`, include the exact agent/model/
effort/account/usage+reset/task/attempts/dividend-or-owner-override/gate consent
envelope, mark it awaiting explicit owner approval, and ask again on any
fallback or extra attempt. For `native-subagent`, emit the bounded task, the gate
you will run on its result, and the context dividend — **not** an account/usage
envelope, because no other account is being spent. Spawning the child, selecting
the model, and running the gate are all YOUR actions — this skill recommends, it
does not route.

## v2 six-lane projects (fallback)

Structure-agnostic except where the recommendation lands: on a v3 project the
`execution_recommendation` field is in `PRD.md` frontmatter; on a v2 (six-lane)
project it's in `roadmap.md`. The decision logic, the shared rubric, and the
modes are identical.
