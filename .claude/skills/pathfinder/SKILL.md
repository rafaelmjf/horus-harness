---
name: pathfinder
description: >-
  Owner-invoked, guided divergence→convergence re-baseline of a project's
  direction — the thin WORKFLOW that sequences individually-invocable steps: pin
  the intent (deepen own-use vs broaden adoption vs both; triage backlog-POLISH
  requests out to the grooming pass — the full chain is for direction changes),
  pin a position brief (`horus consolidate` read-out), gather the inward
  evidence (`product-audit` where the project has one, else shipped-vs-used with
  the owner), scan the market (`market-scan`, shallow by default),
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
  scope before any web work; the market step is shallow by default and offers more
  depth rather than assuming it. Not continuous monitoring.
---

<!-- horus-skill-version: 11 -->

# pathfinder — the re-baseline workflow (thin by design)

You are running the project's **breathing loop** once, on demand: research →
**divergence** (a tree of alternative roadmaps) → the owner picks → shaping drafts
→ refined backlog → later **convergence** (the `horus consolidate` read-out trims the fat).
You are a pathfinder: you **scout the route ahead and report it** — you do not
build the road. This runs the SAME whether the project is brand-new (no facet
table yet — the onboarding fork inside `roadmap-branches`) or years old (a genuine
re-baseline); the name is deliberately age-agnostic.

**Cross-step output convention (owner calibration, 2026-07-20):** every step's
receipt keeps a fixed semi-deterministic spine, uses consolidated tables for
enumerable material, is written for a reader with no project context, is
pasted into the terminal in an interactive session, cites sibling receipts
instead of restating them, and ends with a dive-deeper-into-one-named-topic-
or-proceed offer. The stable structure is the owner's drift detector: a
summary that feels off signals drift in the inputs that produced it.

v2 is **genuinely thin**: every stage is its own skill or CLI signal, and
pathfinder contributes NO analysis of its own — only the sequencing, the owner
gates between steps, and passing each step's receipt into the next. (v1 kept the
direction/card judgment inline and unstructured, and its output quality drifted;
the depth requirements now live in the step skills, where `skill-audit` can hold
each one against reality separately.)

This table is the contract: read it before running anything, so you know what each
step does, what it costs, and what it hands the next one. **Steps 0-2 spend nothing;
step 3 is the only web spend; every step gates on the owner.** A step listed only in
the prose below is a step that gets skipped — that is how step 7 was missed on
2026-07-31, when a run went 0-4, was rejected, and trailed off without ever stating
what had landed.

| The owner's question | Runs | What happens, in detail |
|---|---|---|
| **0 — Is this a re-baseline at all, and what for?** | pathfinder itself | **Triage before anything else.** If the *direction* is in question — drift, a pivot, a new opportunity, onboarding onto facets — this chain applies. If the direction holds and the backlog merely needs readiness, contracts, disposition or order, that is grooming: route it to `backlog-refine` standalone and say plainly that the full chain would be ceremony. Then pin the intent, **interactively**, because it steers both the research frame and the verdict criteria downstream: `deepen-own-use` (audience is the owner; evidence reads as build-vs-adopt per capability), `broaden-adoption` (evidence reads as market gap and differentiation), or both. An intent arriving in the invocation arguments, a stored `next_prompt`, or a scheduled brief is a **proposal, not a confirmation** — present the options and get a pick. Also settle here whether the owner wants a gate at every step (default) or one pre-authorized straight-through run. Produces no artifact; nothing else starts until the intent is confirmed. |
| **1 — Where are we?** | `horus consolidate` (read-out) | **Builds the pinned position brief, which every later step treats as a hard constraint.** Reads `## Vision` — or notes the facet table's absence, which switches the chain into its onboarding fork — plus the active backlog cards with their `vision_facet` and `phase` stamps, `## Shipped`, and the deterministic convergence read-out that maps cards onto facets. The brief states three things: what has shipped, what the Vision claims and for whom, and where facet coverage is open or thin. Its job is to stop later steps drifting into research about a project this is not. Costs nothing — no web, no fan-out. Gate: the owner confirms the brief before the chain continues. |
| **2 — What actually earned its keep?** | `product-audit` (or a shipped-vs-used pass with the owner) | **Gathers the inward half of the evidence base.** Drift is an inward symptom, so this runs before looking outward. Three evidence lines: which surfaces the owner *demonstrably* used since the last audit (from `.horus/` artifacts, git history, machine-local state, and grepping the project's own reference surfaces — never telemetry); what the declared upstream sources shipped that overlaps something this project delivers; and which rituals were skipped, rubber-stamped or nagged past, because a step everyone bypasses is evidence against the step. **It is analysis only — it never issues demote, defer or retire verdicts**, which belong to the convergence session; suggestions are routed to the step that owns each decision. Produces a dated receipt under `.horus/audits/`. Costs nothing. Gate: stop with the owner when the audit *changes* the brief; say so and proceed when it merely confirms it. |
| **3 — Where is the world?** | `market-scan` | **Gathers the outward half, read through the pinned intent.** Under `deepen-own-use` the yardstick is build / adopt / compose **per capability** — is something external more valuable than maintaining this ourselves — and a market-saturation verdict is explicitly the *wrong* instrument. Under `broaden-adoption` it is the classic prior-art and differentiation read. Produces a JTBD hypothesis (labelled a hypothesis, never a finding — a skill cannot run interviews), a competitive teardown of 3-6 named products with a fetched URL behind every row, a PR-FAQ vision paragraph, and a one-line market-size sanity check that is hard-capped. **This is the only step that spends web budget**, it runs a shallow sweep by default, and it offers more depth rather than escalating on its own. A fresh, still-valid receipt may be reused instead. Produces a dated receipt under `.horus/research/`. Gate: the owner reacts to the evidence. |
| **4 — Which directions could we take?** | `roadmap-branches` | **Produces the divergence tree — multiple alternative roadmaps, never one merged plan**, because merging is the owner's convergence decision and pre-merging destroys the choice this step exists to surface. Branches are DIRECTIONS, drawn from the gap between a facet's definition of done and the delivered code, from the owner's real friction (a direction with zero cards is a signal it was invisible to the backlog, not that it is unimportant), from the audit and market receipts, and from the Vision's out-of-scope lines treated as re-testable hypotheses. **The backlog is never the material branches are built from** — it is dispositioned against the branches once they exist, every card either earning a place or getting argued push-back. Full facet coverage lives in the receipt's narrative position read-out, **not in the branch list**: a branch is produced only where there is a real direction, so fewer branches than facets is normal and a converged facet needs none. Each branch's thesis opens in plain terms — what goes wrong today, what is different afterwards — before any mechanism, then carries a market-position line, a numbered roadmap deep enough for `scope-cards` to work from, a convergence criterion, and the facet diff it implies (which may propose shrinking a facet). Includes 1-2 speculative branches, at least one re-testing an out-of-scope declaration. Produces a dated receipt under `.horus/research/`. Gate: **the owner picks**, amends, or rejects the tree. |
| **5 — What high-level work does the chosen branch imply?** | `scope-cards` | **Shapes the picked branch into aligned high-level Shaping drafts** — enough context preserved that a later refinement session does not re-think the direction, but deliberately *not* execution-ready cards. Marks each draft as existing or new, carries the branch's Vision facet diff and any push-back diffs against existing cards, and requires wildcards to state their converge-or-drop criteria. Owner verdicts from step 4 that rescope or demote an existing card are written into that card's `## Reviews` here, because a verdict living only in a receipt does not bind future planning runs. Gate: the owner approves per item, and only approved drafts are written. |
| **6 — What is genuinely ready, waiting, or still undecided?** | `backlog-refine` | **The only step that makes a card execution-ready.** Runs picture-first and interactively: a walkthrough per card — problem background, proposed solution, verdict — with decisions taken strictly one at a time. Sets final readiness and autonomy, writes the concrete execution contract, records disposition for what is not proceeding, and applies the owner-approved order. Only cards passing its single execution-ready contract come out Ready. This is also the **standalone door**: an owner who wants grooming without a direction change invokes this directly and skips the chain entirely. Gate: interactive throughout; nothing is silently rewritten. |
| **7 — What landed, and what stays unapplied?** | pathfinder itself | **Closes the run — the step most likely to be skipped, because it produces no artifact of its own.** State what was actually written through the normal paths (approved cards, card edits, Vision diffs), and name everything the owner deferred as **explicitly not applied**, so nothing is left ambiguously half-decided. Then stop. **Convergence — trimming the fat once usage evidence has accumulated — is a SEPARATE session**, driven by the `horus consolidate` read-out, and is never chained off the end of this one. Re-run pathfinder only when a real re-baseline is needed again, not on a schedule and not because a bundle looks stale. |

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

Step 3 goes to the web (Steps 1–2 are no-spend). Before it, state: the intent
(from Step 0), the trigger (re-baseline | onboarding), the project in one line,
and the directions you already suspect. `market-scan` then runs a SHALLOW sweep of
the top public results by default and asks the owner afterwards whether to go
deeper — so a normal Step 3 needs no depth negotiation up front, and depth is
never escalated without an explicit request. A fresh, still-valid receipt
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
- No token estimate beyond stating the depth — `market-scan` owns the actual
  fan-out, and it defaults to a shallow sweep before offering more depth.
- No continuous monitoring (that always-on category is out of scope).

