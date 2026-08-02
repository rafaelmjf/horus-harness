---
name: wildcard
description: >-
  Owner-invoked (or scheduled) AUTONOMOUS divergence skill that proposes NEW MOVES to
  advance the vision — the safe autonomous sibling of pathfinder. It draws ideas from the
  gap between each Vision facet's definition of done and the code that actually exists,
  from the owner's real friction in recent use, and from outside the project — never from
  the backlog, which it reads only to avoid duplicating. It emits ALL valid moves RANKED
  high→low, each one BUILDABLE and SELF-SUFFICIENT: a fresh agent could start it without
  asking the owner anything, because every execution choice it depends on has already been
  made and stated. Strictly ADDITIVE: it never proposes dropping, archiving, pruning or
  deferring anything — those are backlog-refine and convergence decisions.
  Safe to run unattended because every output is a proposal the owner disposes of — it
  never sets direction, never implements, never edits the backlog.
  Use when the owner says "run wildcard", "surprise me with an opportunity", "what am I
  missing", or schedules an away-mode discovery job. NOT autonomous convergence (direction
  stays owner-gated via pathfinder) and NOT a card factory (cards are drafted only on
  request, for ideas the owner picks).
---

<!-- horus-skill-version: 7 -->

# wildcard — autonomous divergence → ranked, buildable vision-advancing moves

**Status: v5 (2026-07-31, from the run-3 failure).** This SKILL.md and its `.agents/`
twin ARE the source — there is no generator for this skill yet, so they are edited
directly and kept byte-identical. Registering it in `horus/skills.py` (version wiring +
install verification) is the dedicated-session step the `wildcard` backlog card drives.

## Purpose — move the vision FORWARD

`wildcard` exists to propose **new moves that advance the vision**: a facet closer to its
definition of done, or a `vision-branch-*` direction closer to being promoted into a facet.
Divergence here means *finding the next thing worth building or proving*.

Two properties make an idea worth emitting, and they are the whole skill:

- **BUILDABLE** — its substance is a change to code or prose, or a fully specified probe.
  Something an agent could execute.
- **SELF-SUFFICIENT** — a fresh agent could start it without asking the owner anything,
  because every choice its execution depends on has already been made *inside the idea*.

Anything failing either property is not an idea, it is an agenda item. See the
self-sufficiency bar below — it is the primary gate, and the one this version exists for.

**Never propose dropping, archiving, deprioritising, pruning, retiring, or deferring
anything.** Those are subtractive decisions and they belong to `backlog-refine` (per-card
disposition) and the convergence step (facet and branch verdicts) — never here. A run whose
output is mostly "stop doing X" has failed, however well-evidenced: it spent a divergence
pass on work another skill owns. If a subtraction is genuinely the obvious move, note it in
one line at the end and route it, then get back to proposing forward moves.

## Grounding — where ideas come from (NEVER the backlog)

Four sources, in this order. **The backlog is not one of them.** Existing cards and
`vision-branch-*` umbrellas are read for ONE purpose: to avoid duplicating something already
carded. They are never the well ideas are drawn from.

This is the correction v5 exists for. Four consecutive revisions fixed the *shape* of the
output while the procedure still said "diverge over the branches" — so every run obediently
produced backlog triage, and the fallback grounding ("the live session's context plus the
backlog") was the recency-anchoring failure mode written in as an approved path. Ideas do
not come from the project's own bookkeeping. If an idea can be traced to a card, it is
almost certainly triage wearing an idea's clothes.

1. **Facet DoD vs delivered code — always available, never stale.** Take each Vision facet's
   definition of done and go read what actually exists in the repo. The gap between the two
   is the richest source there is, it needs no external evidence, and it cannot go out of
   date. Start here on every run.
2. **The owner's real friction — highest signal when present.** What was slow, manual,
   surprising, repeated by hand, or annoying in recent actual use of the product? Session
   context and recent continuity are legitimate evidence *of friction*; the move is the
   capability that removes it, not a note about the friction. (The one output this skill
   ever produced that the owner judged good — the `backlog-librarian` capability — has this
   shape.)
3. **Outside the project — opt-in, scope-confirmed.** What do comparable tools, agent-CLI
   changelogs, or the wider ecosystem now make possible that this project has not absorbed?
   This costs web work: confirm the scope with the owner before spending it, and skip it
   silently in an unattended run rather than escalating.
4. **A previous pathfinder run's artifacts — context, not the well.** Position brief,
   product-audit receipt, market-scan receipt, roadmap-branches tree. Useful for what the
   project already concluded; they are background, and never the thing being paraphrased.

**Disclose dates; never refuse on age.** State the date of every artifact you leaned on and
let the reader judge what that is worth. Do NOT add a freshness threshold and do NOT refuse
to run because an artifact looks old: staleness here is subjective and hard to pin down, so
it is left to the reader's interpretation (owner, 2026-07-31) — and a preemptive gate where
nothing has been shown to fail contradicts the PRD's controls ladder. Source 1 never goes
stale, so a run is always possible.

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

## The self-sufficiency bar — the primary gate

**An idea is ready to emit only if a fresh agent could build it without asking the owner
anything.**

If the idea's execution depends on a choice — where something lives, which of two shapes it
takes, what the field is called, what the threshold is — **make the choice, state it, and
give the one-line reason.** Do not hand the choice back.

This is not a style preference, it is the difference between a proposal and a meeting. The
owner disagreeing with a stated choice is a cheap and useful conversation, and it happens
*before* building. The owner being asked to settle three questions before anything can start
is the failure this bar exists to stop. **"Decide X, then build Y" is not an idea.** Neither
is anything whose real ask is a go-ahead.

Concretely, an idea fails this bar if:

- its `Do this` contains "decide", "settle", "define", "determine", "choose", or "agree";
- its substance is unblocking a card that is blocked *on owner decisions*;
- its `Change performed if accepted` describes an outcome ("a verdict recorded", "clarity
  on X", "the card becomes writable") rather than a named change to named things;
- a fresh agent reading it would have to come back with a question before writing anything.

When an idea is genuinely worth doing but genuinely needs the owner to choose first, that is
a real finding — write it as ONE routed line at the end (`needs an owner decision:` …), not
as a ranked proposal.

## Procedure

1. **Diverge — one lens at a time, over the GROUNDING SOURCES.** Generate ~5-7 candidate
   moves, each from a DISTINCT lens, working the sources above — facet-DoD gaps first, then
   friction, then outside. Vary the frame deliberately and do not let one frame's result
   shape the next. **Do not iterate over the backlog or the branch umbrellas**: that is what
   produced triage in every prior run. True branch isolation would need parallel subagents;
   that is a token-intensive fan-out requiring owner authorization under the delegation
   rule, so it is not the default. (Prior art for the isolated-frames + separate-critic
   structure: github.com/uditakhourii/adhd.)

2. **Make each candidate self-sufficient BEFORE ranking it.** For every candidate, list the
   choices its execution depends on and settle them now, with a reason each. A candidate you
   cannot settle is not ready — either do the reading that settles it, or drop it to the
   routed-line list. This step is where a triage item reveals itself: if settling the choices
   IS the whole idea, it was never a move.

3. **Critique and RANK — every valid idea survives.** Score each candidate and order them
   high→low. Do not discard a valid idea to manufacture a single winner. Drop a candidate
   only if it is genuinely invalid: already covered by an existing card or skill, factually
   wrong, or outside this project's scope. Say so in one line and move on — a long reject
   list is a symptom, not a deliverable.

   Rank on: how far it moves a facet or branch FORWARD · is the evidence real and cited ·
   is it cheap relative to what it unlocks · does it respect the PRD Rules. A candidate whose
   substance is a drop, archive, deprioritise or defer is **invalid here** — route it to
   `backlog-refine` in one line and rank it nowhere.

   **Three mandatory checks before ranking, all learned from failed runs:**
   - **Self-sufficiency check.** Apply the bar above to every candidate. This is the one
     that would have emptied run 3.
   - **Rules check.** Read `## Rules` in PRD.md and reject anything that contradicts one.
     A candidate proposing a new control where nothing has failed in the field violates the
     controls ladder ("never enforce preemptively") and is invalid, not merely low-ranked.
   - **Premise check.** For every field, flag, or convention the idea relies on, confirm
     what it *actually* means to the owner before building on it. A dated field may be a
     floor ("not before"), not a due date ("act on").

4. **Emit the ranked set — index first, then a scope block per idea.** A ranked table is an
   index, not the proposal: on its own it makes a decision, an experiment and a code change
   look like the same size of thing. Every idea therefore carries a scope block, so the
   owner can judge what they are agreeing to without asking a follow-up question.

   **The index table:** rank · **the action, as an imperative** · what it advances · `kind` ·
   effort.

   **Then, for EVERY idea, an action-first block. Lead with the two fields the owner
   actually needs, and keep them concrete:**

   - **Do this** — ONE imperative sentence naming the work. "Add X to Y so Z" or "Run A
     against B and record C". Not a topic, not a question, never "explore", "consider", or
     any of the decision verbs listed in the self-sufficiency bar.
   - **Change performed if accepted** — the concrete before→after. Name the files,
     commands, or behaviour that differ afterward, in terms someone could verify. This is
     the field that answers "what am I agreeing to", so it must survive one test: *could a
     fresh agent start work from this line alone?* If not, rewrite it.
   - **Choices already made** — the execution decisions this idea settles on the owner's
     behalf, one line each with its reason. This is what makes it buildable rather than a
     request for a go-ahead, and it is where the owner pushes back if they disagree.
   - **Why this advances the vision** — the named facet or branch, and which clause of its
     definition of done or convergence criterion moves. One sentence, cited.
   - **Size** — `kind` + effort. Kind must be one of: `code change` · `prose change` (docs,
     skills, continuity text) · `probe` (a bounded experiment, fully specified: the exact
     commands, what gets recorded, what it settles). **`decision` and `evidence read` are
     not emittable kinds** — an idea whose substance is either belongs in the routed line
     at the end.
   - **Not included** — one line, concrete. Name the adjacent thing a reader would assume
     comes along and does not ("does not touch the scheduler", never "out of scope: broader
     concerns").
   - **Risk** — one line: why it might not work, or cost more than it looks.

   Then a short rationale paragraph for the **top 2-3 only**.

   **Draft a full card only for an idea the owner picks**, and offer the honest
   alternative: if it is small and the owner is present, the PRD Rule "card what you won't do
   now; fix what you will" says do it now and skip the card. State per idea whether it wants
   a new card, belongs to an existing card (name it), or is a fix-now candidate.

### Worked example — the shape, and the failures to avoid

**Good** — buildable, and every execution choice already settled:

> **1 — Stamp per-card usage at dispatch close so `explore` cards can be judged on real
> use** · advances PO lifecycle · `code change` · one session
>
> - **Do this:** stamp the worker's start/end usage reading onto the card it delivered, at
>   the point `supervise` already writes its ship-stamp.
> - **Change performed if accepted:** `horus/supervise.py`'s ship-stamp path gains a
>   `usage_at_close` write to the delivered card's frontmatter; `horus/backlog.py` tolerates
>   and exposes the field; `explore`-phase cards start accumulating a real usage signal
>   where today they have none.
> - **Choices already made:** field name `usage_at_close` (mirrors the existing
>   `shipped_sha` naming); written at ship-stamp rather than a new hook (that path already
>   opens the card for write); stored as the raw reading, not a delta (deltas need a
>   same-window pair, which dispatch cannot guarantee).
> - **Why this advances the vision:** PO lifecycle's open frontier is
>   convergence-driven-by-usage, and `explore-converge-lifecycle` is Deferred *specifically*
>   waiting on "a real per-card usage signal" — this produces exactly that signal.
> - **Size:** `code change`, one session.
> - **Not included:** does not add the converge-or-drop advisory itself; does not touch the
>   usage cache and adds no polling.
> - **Risk:** dispatch is rare right now, so the signal accumulates slowly and may stay too
>   thin to judge anything for weeks.

**Bad — abstract.** Every line is a topic rather than an action, and no fresh agent could
start from it. This skill has produced all three; do not:

> - ~~**In scope:** clarify the branch's direction and gather the relevant evidence.~~
> - ~~**Deliverable:** a verdict recorded in the umbrella's Reviews.~~
> - ~~**Consequence:** the review becomes a short question; card count drops.~~

**Bad — the run-3 shape: a to-do list for the owner.** Every line here is concrete, cited
and honest, and it is still not an idea, because the work it names is the owner's:

> - ~~**Do this:** decide where the contract is declared (docs vs code constants vs README),
>   the exact field list per tier, and how tier names surface to users.~~
> - ~~**Change if accepted:** the card leaves `shaping` and becomes writable.~~

Three of run 3's five proposals had this shape. It passes every earlier check in this file —
it is specific, it cites its grounding, its scope block is fillable — and it fails the only
one that matters, because accepting it produces a meeting rather than a commit. The fix is
not to delete the idea: it is to **make the three choices, state them with reasons, and
propose the declaration itself.**

## Output

- A ranked index table of every valid idea (typically 3-6), plus the scope block for each,
  each citing its grounding and the facet or branch it advances.
- One routed line per item that is real but owner-gated (`needs an owner decision:` …),
  after the ranked set, never inside it.
- Full card drafts only on request, for the ideas the owner picks.
- If nothing clears the bar, say so and emit nothing — that is a valid result.

## Quality bar

- **A run that emits zero buildable ideas has failed.** Say so plainly rather than filling
  the set: an all-`decision` output is the exact failure of run 3, where three of five
  proposals asked the owner to choose something and none named a change an agent could make.
- Every emitted idea must be defensible on its own; ranking replaces rejection.
- **The action test: if `Change performed if accepted` would not let a fresh agent start
  work, the idea is not ready to emit.** An abstract deliverable ("a verdict recorded", "a
  finding", "clarity on X") means the idea is a topic, not a move.
- **The self-sufficiency test outranks all of the above** — see the bar above. An idea that
  is specific, cited and well-scoped still fails if building it requires the owner to decide
  something first.
- **Every idea must be additive.** If the ranked set is mostly subtraction, the run has
  failed and should be redone against the forward question.
- Cite grounding per idea, with the date of any artifact leaned on. Check each against the
  open backlog for duplication — that is the backlog's only role here.
- Obviousness **lowers a rank, it never excludes** — an obvious idea the owner has not
  acted on may simply be the right next move.
- Prefer ideas whose evidence already exists over ideas needing new investigation.

## Non-goals

- Not autonomous convergence — direction/roadmap choice stays owner-gated (pathfinder).
- Not autonomous implementation — a picked idea follows refine → approve → implement.
- **Not a pruning pass.** No drops, archives, retires, deprioritisations or deferrals;
  those are `backlog-refine`'s and convergence's authority.
- **Not a backlog triage pass.** Surfacing undecided, stale or blocked cards is
  `backlog-librarian` and `backlog-refine`; a run whose output could have been produced by
  reading the backlog alone has failed regardless of how good the items are.
- Not a card factory: ideas are ranked proposals; cards are drafted only on request.

## References

- Backlog: `wildcard` (refinement driver + the registration step), the four
  `vision-branch-*` umbrellas (duplication check only — not the idea source),
  `pathfinder-structured-outcome` (grounding substrate), `pathfinder` / `scope-cards` /
  `market-scan` (divergence machinery reused), `autotest-e2e-away-mode-drill` (safe
  autonomous-loop food — buildable wildcard ideas are candidate drill legs, which is only
  possible once ideas are executable work rather than owner decisions).
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
  accepted`, gated by the action test. **v4 → v5, 2026-07-31, from the run-3 failure
  (`.horus/research/2026-07-31-wildcard-branch-divergence.md`):** run 3 was pinned to the
  branch umbrellas — the fix for runs 1-2's recency anchoring — and produced five items of
  backlog triage, which the owner judged "not wildcard worthy … scraping the backlog for
  undecided or stale cards, not novel features and ideas". **The diagnosis is that all four
  prior revisions fixed the FORM of the output and none touched where ideas come from**,
  while the procedure still said "diverge over the branches" and the documented fallback was
  "the session's context plus the backlog". By this skill's own `Kind` taxonomy run 3 emitted
  three `decision`, one `evidence read`, one `probe` — and zero code or prose changes, so
  nothing was executable, which is also why none could serve as away-mode drill legs. v5
  therefore (a) replaces the grounding with facet-DoD-vs-code, owner friction, and outside
  evidence, with the backlog demoted to a duplication check; (b) adds the **self-sufficiency
  bar** as the primary gate, on the owner's framing that an idea should be "ready to build
  without extra decisions rather than a 'go ahead'"; (c) makes `decision` and `evidence read`
  non-emittable kinds with a routed line for genuine owner-gated items; (d) adds
  `Choices already made` to the scope block; and (e) declines a staleness threshold on the
  owner's call that staleness is subjective and better disclosed than enforced.
