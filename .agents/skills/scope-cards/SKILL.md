---
name: scope-cards
description: >-
  Populate a chosen roadmap branch (or any approved direction) into fully
  SELF-SUFFICIENT backlog card drafts — frontmatter plus context, concrete how,
  acceptance, and non-goals — so a fresh agent session can pick any card up and
  start with the same understanding, needing nothing from the originating
  conversation. Step 4 of the pathfinder flow, also standalone ("scope this
  card", "populate cards for this direction"). Owns the dispatchable-card
  contract — the single authority for what a backlog card must carry, referenced
  (never restated) by the cockpit ready-gate. Also use standalone when the
  direction holds but the existing backlog needs grooming, refinement, readiness
  review, or disposition. Draft the branch's implied Vision facet edits and the
  demote/defer/retire diffs for existing cards the branch pushed back on.
  Advisory: present every decision-bearing draft first; the owner approves per
  item; only approved items are written.
---

<!-- horus-skill-version: 5 -->

# scope-cards — from a chosen branch to a fresh-agent-ready backlog

You are transcribing an approved direction into cards that pass one bar:

> **The self-sufficiency test: a fresh agent session, given only `PRD.md` and this
> card, can start the work correctly — same understanding, no access to the
> conversation that produced it.**

The curated backlog is the interface between interactive curation (owner + LLM,
here) and autonomous execution (the away-mode worker/supervisor loop, which only
CONSUMES cards — it never curates). A card that will ever be dispatched unattended
must therefore carry not just enough to *start* but enough to be *finished and
independently verified* — that is what the contract below encodes.

## Input

One chosen branch from a `roadmap-branches` receipt (or an owner-approved
direction of equivalent depth). Each item needs why / how / suspected weak points /
non-goals already argued. **If an item arrives thin, do not silently invent the
missing depth** — flag it and resolve it with the owner (or send it back through
`roadmap-branches`) before drafting its card.

## Grooming an existing backlog (standalone mode)

The other input shape: no branch, just an existing backlog whose direction holds
(pathfinder's Step 0 triage routes polish needs here). Read the CONTENT of every
open card, including explore children and `vision-branch-*` umbrellas; a
frontmatter-only lint pass is not backlog refinement. Use this sequence:

1. **Show the picture before asking decisions.** Summarize what each Vision facet
   and active branch is trying to achieve, then split the backlog honestly into:
   Ready (`status: open` + no `deferred:` + dependencies met), Deferred (waiting
   deliberately on the named trigger), and Gated (missing a decision, dependency,
   evidence, or contract element). Keep priority as importance-when-active; never
   use it to disguise waiting work.
2. **Judge first; audit second.** Read why/how/acceptance/reviews and use LLM
   judgment to decide whether each card is still valuable, correctly scoped,
   phase-appropriate, and self-sufficient. Then run deterministic
   frontmatter/heading checks (surface, parallel, tier vocabulary, facet/branch,
   acceptance markers) to catch omissions and support the judgment. Sort every
   hit into by-design vs defect using project rules; a heuristic firing is not
   itself a finding.
3. **Apply the bar for the card's job.** A converge card advances a named facet
   and eventually owes supervisor-grade acceptance; an explore card owes a cheap
   PoC plus an adopt/promote/drop verdict; an umbrella owes a current thesis,
   ordered children, and a convergence criterion, not worker acceptance. Keep all
   three in the pass instead of excluding non-dispatchable cards from curation.
4. **Escalate only pending decisions.** Do not interrogate the owner about clean
   cards or questions the evidence already settles. For each real judgment call,
   show a compact preview: card + branch/facet goal, current disposition, your
   recommendation and why, and the exact proposed diff. Offer concrete choices
   plus a free-text alternative; get a separate verdict before writing it.
   Batch only mechanical fixes with obvious values into one approval.
5. **Write disposition as durable state.** `deferred: "<reason and un-deferral
   trigger>"` means deliberately waiting; remove it when that trigger is met or
   the owner reactivates the work. Set `last_refined: YYYY-MM-DD` only after the
   card's content was reviewed in this pass, including clean/no-change cards —
   never from a field audit alone. Record owner demote/defer/retire/rescope
   verdicts in the card's `## Reviews` as well as its frontmatter/body diff.

The per-item owner gate and never-silently-invent rule remain unchanged.

## The dispatchable-card contract (single authority — consumers reference, never restate)

This section IS the contract for what a backlog card carries. The cockpit
dispatch contract's ready-gate judges candidates against it; a backlog grooming
pass refines existing cards toward it. When the contract changes, it changes here
once and propagates — do not fork partial copies into consumer skills.

Frontmatter: `status: open`, `priority`, `tier` (the closed vendor-neutral set —
`low | medium | high | frontier`; model-named values are legacy aliases the
tooling normalizes, never coin new ones), `vision_facet` (matched to a
`## Vision` table facet — **required for `converge` cards; `explore` cards may
substitute a `branch: <umbrella>` stamp** until the direction earns a facet or
dies, per the Vision's breathing rule), `phase` (`converge` default; `explore`
for divergent bets), `created`, `created_by`, and the two collision stamps the
dispatch machinery reasons with:

- `surface: <comma-separated globs>` — the code areas the card touches
  (e.g. `surface: horus/dashboard.py, horus/pty_*`). Without it the collision
  check cannot clear concurrent work — it warns instead of reasoning — so a card
  born without `surface` is born un-dispatchable. Scoping time is when the owner
  is present to answer "what does this touch"; capture the best-effort answer now
  rather than leaving it for a dispatch gate with no human in the room.
- `parallel: safe | exclusive` — whether the card tolerates in-flight siblings.

Body:

- **Why** — the context paragraph carrying the branch's reasoning, INCLUDING the
  market-position line ("exists but misses X / we have Y but miss Z"), so the card
  survives without the receipt.
- **How** — the concrete protocol or first step, specific enough to begin from.
- **Acceptance** — written FOR THE SUPERVISOR, who never trusts a worker
  self-report: the deterministic gate (the test/CI check that must go green on
  the exact SHA) PLUS one **live probe** of the changed surface — the command to
  run or the surface to poke, and what correct looks like. A card whose probe
  must be invented at verify time forces that invention on an unattended session
  with no owner present; name it now. `phase: explore` cards instead carry an
  exit line: the cheap PoC and the explicit verdict it must end in (adopt /
  promote / drop — dying cheap is a valid success). `vision-branch-*` umbrella
  cards carry a `## Convergence criterion` instead of acceptance — they are
  judged as a unit, never dispatched. **Probe-retrofit policy:** only NEW cards
  owe a probe at scoping time; an existing card gets its probe named when it is
  armed for dispatch (the ready-gate checks) or next substantively edited —
  blanket-retrofitting probes onto cards nobody will dispatch is ceremony.
- **Non-goals** — what this card deliberately does not do.
- **Source** — the receipt path + branch name.

**Second-order items are never pre-invented:** when work depends on findings that
do not exist yet (e.g. gap cards a verification probe will produce), scope the
probe card and state "each finding becomes its own card" —
do not fabricate the findings.

## Alongside the new cards, draft the branch's edits

- **Existing-card diffs** — the demote / defer / retire push-back the branch made,
  as explicit per-card proposals (field change or archival, with the reason).
- **Vision facet diff** — exact replacement definition-of-done text per touched
  facet (add / rename / rescope / retire), never a wholesale table rewrite.
- **Vision-branch umbrella** — when the direction spans multiple cards and should
  be judged as a unit (every `explore` direction; any branch the owner may later
  promote or drop whole), draft a thin `vision-branch-*` umbrella card (thesis,
  exists-vs-gaps map, ordered children, convergence criterion) and stamp each
  child `branch: <umbrella-name>`, per the PRD structure contract. Keep the
  umbrella thin — agents-first, minimal overhead; never mirror child status
  into it.

## Gate, then write

Present ALL drafts — new cards, existing-card diffs, Vision edits — as concrete
options plus a free-text alternative, and let the owner
approve, amend, or drop each item individually. Only then write the approved items: new cards as files
under `.horus/backlog/`, facet edits into `## Vision`, existing-card changes in
place. Owner rejections and rescopes of EXISTING cards are written into that
card's `## Reviews` at decision time — a verdict that lives only in a receipt or
the conversation does not bind future planning runs (calibration 2026-07-17).
Anything not approved stays unwritten; say so.

## Deliberately omit

- No implementation, no dispatch, no execution planning (`execution-decision` owns
  the execute-vs-delegate call; `horus-execution` owns phase plans).
- No new receipt — the branch receipt plus the written cards are the trace.
- No priority invention: inherit the branch order; the owner sets priorities.

## v2 six-lane projects (fallback)

No card files — each approved item becomes a `roadmap.md` entry carrying the same
depth inline (why / how / acceptance / non-goals, one compact block per item), and
Vision edits go to `project.md` prose at the owner's discretion, following that
project's six-lane closure rules. The self-sufficiency bar and the per-item owner
gate are unchanged.
