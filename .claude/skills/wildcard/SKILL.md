---
name: wildcard
description: >-
  Owner-invoked (or scheduled) AUTONOMOUS divergence skill that proposes NEW MOVES to
  advance the vision — the safe autonomous sibling of pathfinder. Grounded on a pathfinder
  run's saved evidence (position brief, product-audit, market-scan, roadmap-branches), it
  reads the Vision facets and `vision-branch-*` umbrellas and asks what would make each
  demonstrably further along, then emits ALL valid moves RANKED high→low — each led by an
  imperative action and the concrete before→after change it performs, so the owner sees
  exactly what accepting it does. Strictly ADDITIVE: it never proposes dropping,
  archiving, pruning or deferring anything — those are backlog-refine and convergence
  decisions.
  Safe to run unattended because every output is a proposal the owner disposes of — it
  never sets direction, never implements, never edits the backlog.
  Use when the owner says "run wildcard", "surprise me with an opportunity", "what am I
  missing", or schedules an away-mode discovery job. NOT autonomous convergence (direction
  stays owner-gated via pathfinder) and NOT a card factory (cards are drafted only on
  request, for ideas the owner picks).
---

<!-- horus-skill-version: 4 -->

# wildcard — autonomous divergence → ranked, actionable vision-advancing moves

**Status: v4 (audited 2026-07-28; two same-day revisions from live runs; not yet bundled).** This SKILL.md and its `.agents/`
twin ARE the source — there is no generator for this skill yet, so they are edited
directly and kept byte-identical. Registering it in `horus/skills.py` (version wiring +
install verification) is the dedicated-session step the `wildcard` backlog card drives.
The "previous run" grounding depends on `pathfinder-structured-outcome`.

## Purpose — move the vision FORWARD

`wildcard` exists to propose **new moves that advance the vision**: a facet closer to its
definition of done, or a `vision-branch-*` direction closer to being promoted into a facet.
Divergence here means *finding the next thing worth building or proving*.

Read the Vision facet table and the branch umbrellas — thesis, exists-vs-gaps map, ordered
children, convergence criterion — and ask: **what would make this facet or branch
demonstrably further along, and what is the smallest next piece of work that gets there?**

**Never propose dropping, archiving, deprioritising, pruning, retiring, or deferring
anything.** Those are subtractive decisions and they belong to `backlog-refine` (per-card
disposition) and the convergence step (facet and branch verdicts) — never here. A run whose
output is mostly "stop doing X" has failed, however well-evidenced: it spent a divergence
pass on work another skill owns. If a subtraction is genuinely the obvious move, note it in
one line at the end and route it, then get back to proposing forward moves.

Frames are lenses on the forward question. Vary them deliberately — an unmet gap in the
exists-vs-gaps map, a capability the branch would unlock, a cheaper route to the evidence a
convergence criterion demands, a probe that would settle an open hypothesis, an adjacent
facet the same work would also serve. Operational-hygiene findings are in scope only when
they **block** forward movement; a hygiene idea with nothing to advance belongs to
`backlog-librarian` or `product-audit`.

## What it is / hard boundaries

- **Advisory, owner-gated.** Emits ranked *proposals*. NEVER sets direction, NEVER
  implements, NEVER creates/edits cards until the owner picks one.
- **Safe to run unattended** because every output is a proposal the owner disposes of —
  nothing is written, so the blast radius is zero. The safety comes from
  proposal-not-mutation, **not** from emitting only one item.
- Ranked ideas, not a flood of drafted cards: full card drafts happen on request only.
- **Additive only.** Every proposal builds, proves, or unlocks something. Dropping,
  archiving, pruning, deprioritising and deferring are `backlog-refine` and convergence
  decisions; proposing them here is out of contract, not merely low-value.

## Grounding — a pathfinder run (never free-roaming)

- **Previous run (default):** load the last pathfinder run's artifacts — position brief,
  product-audit receipt, market-scan receipt, roadmap-branches divergence tree (see
  `pathfinder-structured-outcome` for the run bundle/manifest). Cheap; if the run is old,
  say so and cite the artifact dates.
- **Fresh run:** if the owner wants current evidence, run pathfinder's evidence steps
  (product-audit / market-scan) first, then proceed. More costly.
- **Fallback:** if no pathfinder run exists, ground on the live session's accumulated
  context plus the backlog — and SAY that is the grounding. Every emitted idea cites the
  specific artifacts/signals it was grounded in.

## Procedure

1. **Diverge — one lens at a time, over the branches.** Generate ~5-7 candidate moves,
   each from a DISTINCT lens on the forward question above. Vary the frame
   deliberately and do not let one frame's result shape the next. True branch isolation
   would need parallel subagents; that is a token-intensive fan-out requiring owner
   authorization under the delegation rule, so it is not the default. (Prior art for the
   isolated-frames + separate-critic structure: github.com/uditakhourii/adhd.)

2. **Critique and RANK — every valid idea survives.** Score each candidate and order them
   high→low. Do not discard a valid idea to manufacture a single winner. Drop a candidate
   only if it is genuinely invalid: already covered by an existing card or skill, factually
   wrong, or outside this project's scope. Say so in one line and move on — a long reject
   list is a symptom, not a deliverable.

   Rank on: how far it moves a facet or branch FORWARD · is the evidence real and cited ·
   is it cheap relative to what it unlocks · does it respect the PRD Rules. A candidate whose
   substance is a drop, archive, deprioritise or defer is **invalid here** — route it to
   `backlog-refine` in one line and rank it nowhere.

   **Two mandatory checks before ranking, both learned from failed runs:**
   - **Rules check.** Read `## Rules` in PRD.md and reject anything that contradicts one.
     A candidate proposing a new control where nothing has failed in the field violates the
     controls ladder ("never enforce preemptively") and is invalid, not merely low-ranked.
   - **Premise check.** For every field, flag, or convention the idea relies on, confirm
     what it *actually* means to the owner before building on it. A dated field may be a
     floor ("not before"), not a due date ("act on").

3. **Emit the ranked set — index first, then a scope block per idea.** A ranked table is an
   index, not the proposal: on its own it makes a decision, an experiment and a code change
   look like the same size of thing. Every idea therefore carries a scope block, so the
   owner can judge what they are agreeing to without asking a follow-up question.

   **The index table:** rank · **the action, as an imperative** · what it advances · `kind` ·
   effort.

   **Then, for EVERY idea, an action-first block. Lead with the two fields the owner
   actually needs, and keep them concrete:**

   - **Do this** — ONE imperative sentence naming the work. "Add X to Y so Z" or "Run A
     against B and record C". Not a topic, not a question, never "explore" or "consider".
   - **Change performed if accepted** — the concrete before→after. Name the files,
     commands, or behaviour that differ afterward, in terms someone could verify. This is
     the field that answers "what am I agreeing to", so it must survive one test: *could a
     fresh agent start work from this line alone?* If not, rewrite it.
   - **Why this advances the vision** — the named facet or branch, and which clause of its
     definition of done or convergence criterion moves. One sentence, cited.
   - **Size** — `kind` + effort. Kind is one of: `code change` · `prose change` (docs,
     skills, continuity text) · `probe` (a bounded experiment that spends real resources) ·
     `evidence read` (answer a question from what already exists) · `decision` (owner
     judgement, no build).
   - **Not included** — one line, concrete. Name the adjacent thing a reader would assume
     comes along and does not ("does not touch the scheduler", never "out of scope: broader
     concerns").
   - **Risk** — one line: why it might not work, or cost more than it looks.

   Then a short rationale paragraph for the **top 2-3 only**.

   **Draft a full card only for an idea the owner picks**, and offer the honest
   alternative: if it is small and the owner is present, the PRD Rule "card what you won't do
   now; fix what you will" says do it now and skip the card. State per idea whether it wants
   a new card, belongs to an existing card (name it), or is a fix-now candidate.

### Worked example — the shape, and the failure to avoid

**Good** — concrete enough that work could start from it:

> **1 — Stamp per-card usage at dispatch close so `explore` cards can be judged on real
> use** · advances PO lifecycle · `code change` · one session
>
> - **Do this:** stamp the worker's start/end usage reading onto the card it delivered, at
>   the point `supervise` already writes its ship-stamp.
> - **Change performed if accepted:** `horus/supervise.py`'s ship-stamp path gains a
>   `usage_at_close` write to the delivered card's frontmatter; `horus/backlog.py` tolerates
>   and exposes the field; `explore`-phase cards start accumulating a real usage signal
>   where today they have none.
> - **Why this advances the vision:** PO lifecycle's open frontier is
>   convergence-driven-by-usage, and `explore-converge-lifecycle` is Deferred *specifically*
>   waiting on "a real per-card usage signal" — this produces exactly that signal.
> - **Size:** `code change`, one session.
> - **Not included:** does not add the converge-or-drop advisory itself; does not touch the
>   usage cache and adds no polling.
> - **Risk:** dispatch is rare right now, so the signal accumulates slowly and may stay too
>   thin to judge anything for weeks.

**Bad** — every line is a topic rather than an action, and no fresh agent could start from
it. This skill has actually produced all three; do not:

> - ~~**In scope:** clarify the branch's direction and gather the relevant evidence.~~
> - ~~**Deliverable:** a verdict recorded in the umbrella's Reviews.~~
> - ~~**Consequence:** the review becomes a short question; card count drops.~~

## Output

- A ranked index table of every valid idea (typically 3-6), plus a six-field scope block
  for each, each citing its grounding and the branch it advances.
- Full card drafts only on request, for the ideas the owner picks.
- If nothing clears the bar, say so and emit nothing — that is a valid result.

## Quality bar

- Every emitted idea must be defensible on its own; ranking replaces rejection.
- **The action test: if `Change performed if accepted` would not let a fresh agent start
  work, the idea is not ready to emit.** An abstract deliverable ("a verdict recorded", "a
  finding", "clarity on X") means the idea is a topic, not a move — either sharpen it into
  a named change, or say plainly that it is a direction needing its own session. Vagueness
  is the failure this skill was audited for twice; do not fill the block with placeholders.
- **Every idea must be additive.** If the ranked set is mostly subtraction, the run has
  failed and should be redone against the forward question.
- Cite grounding per idea. Check each against the open backlog for duplication.
- Obviousness **lowers a rank, it never excludes** — an obvious idea the owner has not
  acted on may simply be the right next move.
- Prefer ideas whose evidence already exists over ideas needing new investigation, and say
  so in `Kind`: an `evidence read` outranks a `probe` that would settle the same question.

## Non-goals

- Not autonomous convergence — direction/roadmap choice stays owner-gated (pathfinder).
- Not autonomous implementation — a picked idea follows refine → approve → implement.
- **Not a pruning pass.** No drops, archives, retires, deprioritisations or deferrals;
  those are `backlog-refine`'s and convergence's authority.
- Not a card factory: ideas are ranked proposals; cards are drafted only on request.

## References

- Backlog: `wildcard` (refinement driver + the registration step), the four
  `vision-branch-*` umbrellas (the subject matter), `pathfinder-structured-outcome`
  (grounding substrate), `pathfinder` / `scope-cards` / `market-scan` (divergence machinery
  reused), `autotest-e2e-away-mode-drill` (safe autonomous-loop food).
- Prior art: github.com/uditakhourii/adhd (isolated N-frame divergence + separate critic).
- Calibration: 2026-07-21 dry-run produced the `backlog-librarian` card (owner judged it
  good → v0/v1). **2026-07-28 audit (`.horus/audits/2026-07-28-skill-wildcard.md`) → v2:**
  three consecutive live runs produced zero branch-advancing ideas because the text stated
  no purpose and its example frames were all operational hygiene; and the mandated
  one-winner-plus-rejects output read as padding. Both fixed, plus the Rules and premise
  checks that would have caught the two rejected cards. **v2 → v3, same day, from the first
  v2 run:** the ranked table alone made a decision, an experiment and a code change look
  like the same size of thing, so the owner could not tell what any idea committed them to.
  Added the `Kind` taxonomy, the mandatory six-field scope block with an explicit
  out-of-scope list, a worked example, and a quality bar that treats an unfillable scope
  block as a signal the idea is not ready. **v3 → v4, same day, from the v3 run:** all six
  ideas were rejected. Two defects, one of them introduced by this skill's own v2 text —
  "promote-or-**drop**" in the Purpose and "a reason to drop it outright" in the lens list
  made four of six ideas subtractive, which is `backlog-refine`'s authority, not wildcard's;
  and the In-scope/Out-of-scope/Deliverable fields were abstract enough that the owner could
  not tell what any idea would actually change. v4 makes the skill strictly additive and
  replaces the scope block with an action-first one led by `Do this` and `Change performed if
  accepted`, gated by the action test.
