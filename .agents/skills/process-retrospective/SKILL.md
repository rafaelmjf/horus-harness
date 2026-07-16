---
name: process-retrospective
description: >-
  Bounded, evidence-first retrospective on how one campaign/episode was
  executed or supervised — not what Horus should build. Use only on an
  explicit owner request ("what should we do differently", "why did that take
  so long") or a concrete incident: failure, near-miss, unexpectedly long run,
  surprising usage/cost movement, or inefficient supervision. Never fires at
  every closure. Lazy-loads only that incident's evidence (execution plan,
  exact PR/CI state, datum/receipt, targeted log fragments, owner
  observations), attributes cost across inherent/delegation-tax/supervisor-
  error/worker-error/Horus-defect/external-failure, checks existing PRD Rules
  and backlog cards first, then recommends the cheapest control rung
  (no-change, guidance clarification, deterministic signal, hard guard),
  capped at three. Advisory only — never estimates tokens, launches another
  model, rereads the repo, or writes continuity itself; accepted outcomes
  land in existing Rules/card Reviews/backlog, never a new document or
  telemetry stream.
---

<!-- horus-skill-version: 1 -->

# Process retrospective — bounded, evidence-first

You are examining how one campaign or episode went, not auditing the Horus
product (that's `product-audit`, periodic and prune-only) and not closing
continuity (that's `horus-consolidate`). This skill never runs on its own —
only on an explicit owner ask or a concrete incident.

## When this fires

- The owner explicitly asks what should improve, why something took long, or
  what happened in a specific episode.
- A concrete incident: a failure, a near-miss, an unexpectedly long run, a
  surprising usage/cost movement, or supervision that felt inefficient.
- **Never** at every closure, and never as a standing habit — that is exactly
  the generic self-reflection ceremony this skill exists to avoid.

## Scope the incident before reading anything

Name the bounded campaign/episode under review and the specific question
being asked. Do not widen this into a review of the whole project.

## Lazy-load only the relevant evidence

Pull only what this one incident needs:

- The relevant `.horus/execution.md` phase, if the work was delegated.
- Exact PR/CI state for the affected commit (`gh pr checks`, merge-watch
  history).
- The datum/receipt for the run(s) in question (`horus datum report`).
- Targeted log fragments (the failing command's actual output, the relevant
  tmux pane) — not a full log tail or a repo-wide re-read.
- The owner's own observations already in this conversation.

Do not broadly reread the repository or open unrelated files "for context."

## Attribute cost honestly — six buckets

Classify what happened. Label anything you cannot pin down as
unknown/confounded rather than guessing:

1. **Inherent task cost** — the work was always this big or this hard.
2. **Delegation tax** — brief/review/gate/merge/close overhead paid regardless
   of who executed.
3. **Supervisor error** — a wrong call by the supervising agent/session.
4. **Worker error** — the delegated agent/session got it wrong.
5. **Horus/skill defect** — a bug or gap in `horus` itself or a bundled skill.
6. **External failure** — provider outage, rate limit, infra flake.

Never estimate token consumption or launch another model call to
investigate; reason only from the evidence already gathered.

## Check existing coverage before proposing anything

Before recommending anything new, check whether `.horus/PRD.md` Rules, open
backlog cards, or an existing skill's stated boundary already cover this
finding. If it's already covered, say so and stop there — don't recreate a
rule that exists.

## Recommend the cheapest rung, capped at three

For each surviving finding, propose the cheapest control that would have
caught or prevented it, cheapest first:

1. **No-change** — inherent cost or a one-off external failure; no rung is
   warranted.
2. **Guidance clarification** — a prose fix (CLAUDE.md/AGENTS.md, a skill's
   own boundary section).
3. **Deterministic signal** — an observable check (a warning, a CLI signal, a
   gate someone watches).
4. **Hard guard** — code that blocks the dangerous class of mistake outright.

Never jump straight to a hard guard without stating why the cheaper rungs are
insufficient — start with instructions and promote only after an observed
field failure. Cap the whole retrospective at **three recommendations**,
ranked by leverage; more than three is a sign the incident needs splitting or
the analysis is padding out generic reasoning.

## Land the outcome — no new artifacts

- Every recommendation is advisory: present it and stop. A process change
  needs explicit owner approval before anything is touched.
- On approval, land the accepted outcome in an **existing** surface: a
  `## Rules` line in `PRD.md`, a backlog card, or a card Review — never a new
  retrospective document, log, or telemetry stream.
- Do not write continuity or backlog entries as part of running this skill;
  recording durable state is `horus-consolidate`'s job at the next boundary.
  This skill proposes; the owner or the next consolidation pass records.

## Stay inline

Default to inline, single-agent analysis. A worker, another model call, or an
independent forward-test to run or validate this retrospective needs its own
separately named and approved envelope — running a retrospective is not by
itself grounds for delegating.

## Review this skill itself

After roughly three real uses, check whether it produced findings that were
actually new — not a restatement of generic reasoning — and cheaper than the
overhead of running it. If not, recommend demoting or retiring it via
`product-audit`.

## v2 six-lane projects (fallback)

Structure-agnostic: the "check existing coverage" step reads whichever
continuity structure the project uses (`.horus/PRD.md` Rules/backlog on v3,
`decisions.md`/`roadmap.md` on v2), and the accepted outcome lands in that
project's live lanes instead of `PRD.md`. Scoping, lazy evidence load, the
six-bucket attribution, and the capped cheapest-rung recommendations apply
unchanged.
