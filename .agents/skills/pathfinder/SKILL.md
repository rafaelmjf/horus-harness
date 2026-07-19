---
name: pathfinder
description: >-
  Owner-invoked, guided divergence→convergence re-baseline of a project's
  direction — the thin WORKFLOW that sequences individually-invocable steps: pin
  the intent (deepen own-use vs broaden adoption vs both; triage backlog-POLISH
  requests out to the grooming pass — the full chain is for direction changes),
  pin a position brief (`horus consolidate` read-out), gather the inward
  evidence (`product-audit` where the project has one, else shipped-vs-used with
  the owner), scan the market (`market-scan`, which composes `deep-research`),
  build the divergence tree of alternative roadmaps (`roadmap-branches`), then
  shape the chosen branch into high-level drafts (`scope-cards`) and refine the
  approved drafts into execution-ready cards (`backlog-refine`). Works the SAME on a
  brand-new repo and a long-running one (it scouts the route ahead and reports;
  it never builds the road). Use when the owner says "pathfinder", "kickstart",
  "re-baseline", "where should this project go next", "reset the roadmap", or
  "onboard this project onto facets"; interactive by design — the owner and the
  LLM decide direction together, never unattended. Advisory and gated: every
  step hands the owner a proposal and each
  step is also callable standalone — pathfinder adds only sequencing, gates, and
  the receipts handoff; nothing is ever written without approval. Confirm a
  token envelope before any web work. Not continuous monitoring.
---

<!-- horus-skill-version: 7 -->

# pathfinder — the re-baseline workflow (thin by design)

You are running the project's **breathing loop** once, on demand: research →
**divergence** (a tree of alternative roadmaps) → the owner picks → shaping drafts
→ refined backlog → later **convergence** (the `horus consolidate` read-out trims the fat).
You are a pathfinder: you **scout the route ahead and report it** — you do not
build the road. This runs the SAME whether the project is brand-new (no facet
table yet — the onboarding fork inside `roadmap-branches`) or years old (a genuine
re-baseline); the name is deliberately age-agnostic.

v2 is **genuinely thin**: every stage is its own skill or CLI signal, and
pathfinder contributes NO analysis of its own — only the sequencing, the owner
gates between steps, and passing each step's receipt into the next. (v1 kept the
direction/card judgment inline and unstructured, and its output quality drifted;
the depth requirements now live in the step skills, where `skill-audit` can hold
each one against reality separately.)

| Step | Owner's question | Owned by |
|---|---|---|
| 0 | what is this re-baseline FOR — and is it a re-baseline at all? | pathfinder (intent + triage gate) |
| 1 | where are we? | `horus consolidate` read-out → pinned brief |
| 2 | what actually earned its keep? | inward audit: `product-audit` where the project has one, else shipped-vs-used with the owner |
| 3 | where is the world? | `market-scan` (composes `deep-research`) |
| 4 | which directions could we take? | `roadmap-branches` (the divergence tree) |
| 5 | what high-level work does the chosen branch imply? | `scope-cards` (aligned Shaping drafts) |
| 6 | what is genuinely ready, waiting, or still undecided? | `backlog-refine` (interactive readiness + execution contract) |

**Receipts are the interfaces**: the market receipt and the branch-tree receipt
live under `.horus/research/`, and the card drafts land as files — so the chain
can pause at any gate and resume in a later session, and any step can be invoked
standalone without the workflow.

## Hard boundary — advisory, gated, never auto-applied

- **Never auto-apply.** Every step hands the owner a proposal; Vision and backlog
  are the load-bearing artifacts and git is the reversal path.
- **Gate at every step by default.** The owner may pre-authorize a
  straight-through run at Step 0; the intermediate gates then collapse into ONE
  final review of the whole package (tree + chosen-branch drafts) — but nothing
  (Vision text, cards, card edits) is ever WRITTEN without explicit approval.
- **Facet changes are always a DIFF** against the existing set (the rule lives in
  `roadmap-branches`: add / rename / retire / promote against a named facet);
  never a wholesale Vision replacement, so a re-run does not thrash continuity.

## Step 0 — pin the intent BEFORE anything (never assume it)

**Triage first: is this a re-baseline at all?** Two owner needs arrive wearing
similar words, and they take different-size tools:

- **Re-baseline** — the *direction* is in question (drift, a pivot, a new
  opportunity, onboarding onto facets). That is this chain.
- **Backlog polish** — the direction holds; existing cards need readiness,
  concrete execution contracts, disposition, or order. Invoke `backlog-refine`
  standalone. Running the full chain for a grooming need is ceremony — route it
  out and say so.

`scope-cards` owns high-level branch shaping; `backlog-refine` alone owns final
execution readiness. Do not merge the two contracts.

A re-baseline has more than one legitimate goal, and the goal steers the whole
run — the research frame AND the verdict criteria. Do NOT default to one silently:

- **deepen-own-use** — make it more useful for the owner's own stated goals
  (audience = the owner). Research reads as **build-vs-adopt** per capability,
  NOT market saturation.
- **broaden-adoption** — reach new users. Research reads as market gap /
  prior-art / differentiation.
- **both** — run the outward scan but summarize through both lenses.

**Confirm interactively, even when the intent arrives pre-declared.** An intent
carried in args, a stored `next_prompt`, or a scheduled brief is a PROPOSAL, not
a confirmation — present the options above plus a free-text alternative and get
the owner's pick before launching any machinery. (Calibration: the 2026-07-17
convergence-test run treated a pre-pinned intent as settled and skipped the ask.)

The pinned intent travels into every step: the envelope statement, the
`market-scan` framing, the `roadmap-branches` theses, the `scope-cards` context,
and `backlog-refine` readiness decisions. Also settle here whether the owner wants per-step gates
(default) or a pre-authorized straight-through run.

## Before you spend — confirm the token envelope

Step 3 fans out web research (Steps 1–2 are no-spend). Before any web work,
state: the intent (from Step 0), the trigger (re-baseline | onboarding), the
project in one line, the directions you already suspect, and the research depth
— then get the owner's confirmation. A light comparative sweep usually beats a
full adversarial report for a direction call. A fresh, still-valid receipt
may be reused instead of a new scan — say so explicitly and get a nod; that nod
carries the owner's reaction to the evidence, so it REPLACES Step 3's STOP (do
not re-gate reused evidence — calibration 2026-07-17). If the owner only wants
the inward pass, skip the scan and let `roadmap-branches` mark its tree
inward-only.

## The flow

1. **Position brief (no spend).** Read `## Vision` (or note the facet table's
   absence), the active cards with their `vision_facet`/`phase` stamps, and
   `## Shipped`; run `horus consolidate` for the deterministic convergence
   read-out. Write the pinned brief — SHIPPED / VISION + audience (per Step 0) /
   OPEN facet coverage — a HARD CONSTRAINT passed into every later step so the
   research stays anchored to what the project already is and who it is for.
   STOP for the owner to confirm the brief (unless straight-through).
2. **Inward audit (no spend).** Drift — pathfinder's own trigger — is an inward
   symptom, so gather the inward evidence before looking outward. Where the
   project has an inward-audit skill (`product-audit` on horus-harness), run it —
   or reuse its receipt when one is fresh. Everywhere else the generic form is a
   short shipped-vs-used pass WITH the owner: walk `## Shipped` (or the features
   ledger) asking what was actually used since the last re-baseline and which
   rituals became ceremony — pathfinder elicits, it does not analyze. Fold the
   answers into the brief; they become `roadmap-branches`' push-back evidence and
   any demote/defer/retire verdicts flow through the normal advisory paths. STOP
   with the owner when the audit changes the brief (skip the stop when it
   confirms it — say so and proceed).
3. **`market-scan`** with the intent + brief, under the confirmed envelope. Its
   dated receipt is the outward evidence. STOP for the owner to react (already
   satisfied when the receipt was reused under the envelope nod — proceed).
4. **`roadmap-branches`** consuming the brief + receipt (+ prior branch-tree
   receipts when they exist) → the branch-tree
   receipt: per-facet position, market shells → verdict → risk, one branch per
   direction (each with a market-position line, a numbered roadmap, a convergence
   criterion, implied Vision edits), 1-2 speculative branches, explicit
   push-back on existing cards, and a held-loosely recommendation. The
   **Onboarding fork** lives there: no facet table → propose the initial facet
   set and offer to stamp existing cards. STOP: the owner picks branch(es).
5. **`scope-cards`** on the chosen branch → aligned high-level Shaping drafts +
   the branch's Vision facet diff + existing-card push-back diffs. The owner
   approves per item; only approved drafts are written.
6. **`backlog-refine`** over the approved drafts and affected existing backlog →
   picture-first interactive decisions, final readiness/autonomy, concrete
   execution contracts, disposition, and owner-approved order. Only Ready cards
   pass its single execution-ready contract.
7. **Hand off.** Approved cards and edits are in place via the normal paths;
   anything the owner deferred stays unapplied — say so. Later, **convergence is
   a separate session**: usage evidence accumulates, the `horus consolidate`
   read-out trims the fat; re-run pathfinder only when a real re-baseline is
   needed again.

## Deliberately omit

- No new CLI subcommand, module, roles, or multi-file ceremony — the
  deterministic signals already exist; pathfinder is pure sequencing over them.
- No analysis inside pathfinder itself — depth belongs to the step skills where
  it can be audited and calibrated one skill at a time.
- No token estimate beyond stating the depth and getting confirmation — let
  `market-scan`/`deep-research` own the actual fan-out.
- No continuous monitoring (that always-on category is out of scope).

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the same sequence over the six-lane files: the brief comes
from `project.md`/`roadmap.md`/`features.md`, `roadmap-branches` states direction
changes against `project.md`'s vision prose, `scope-cards` writes approved shaping
entries, and `backlog-refine` deepens selected entries inline under that project's
rules. The Step 0
intent gate, the pinned brief, and the advisory gate-at-every-step boundary are
unchanged.
