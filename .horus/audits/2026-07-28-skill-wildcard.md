# Skill audit — `wildcard` (v1 → v4) — 2026-07-28

**Trigger:** owner, after three consecutive live runs in one session. Stated complaint:
the skill was meant to produce ideas that **push the vision branches forward**, but
delivers suggestions that are "either redundant or just as buffer to be rejected," and
the output should be **all valid ideas ranked high→low**, not one winner plus rejects.

**Evidence base:** the three real runs of 2026-07-28 (in-conversation, no receipts —
`wildcard` writes none), the skill text at `<!-- horus-skill-version: 1 -->`, live
fidelity checks against `horus/skills.py`, `.horus/backlog/`, and the PRD Rules.

## Verdict table

| # | Finding | Verdict | One-line evidence |
|---|---|---|---|
| F1 | The skill never states its own purpose; its six example frames are all operational-hygiene lenses, and "branch" appears only as an *input* artifact, never the target | **revise** | 0 of 3 runs touched a vision branch, though 19 of 68 cards sit under four branches (X5 7, X4 6, X6 4, X3 2) |
| F2 | One-winner-plus-rejects is mandated in five places and reads as padding | **revise** | Reject trace was the majority of each run's output by volume; owner's verdict confirms |
| F3 | Autonomy safety is wrongly attributed to N=1 rather than to proposal-not-mutation | **revise** | "Safe … precisely because the output is a card"; but nothing is written until the owner approves, so ranked-N is equally safe |
| F4 | The critic has no check against the PRD Rules and no premise check | **revise** | Both rejected cards would have been caught: run 2 violated "never enforce preemptively"; run 1 misread `reactivate_after` as a due date when it is a floor |
| F5 | The "non-obvious" bar *excludes* rather than *ranks*, and suppressed a valid idea | **revise** | Run 3 rejected the `test_skills.py` candidate as top-of-mind; the owner then wanted it |
| F6 | Frame isolation is prescribed but unachievable on a single-context substrate | **revise** | Text demands frames "must not anchor on each other" citing adhd's isolated branches; one agent generates them sequentially — isolation was nominal in all 3 runs |
| F7 | The fixed card-shaped output conflicts with a PRD Rule | **revise** | Run 3's accepted output was correctly *fixed in-session*, not carded; the agent had to improvise past "Emit ONE candidate card" |
| F8 | Fidelity of every factual claim in the text | **no-change** | "Not yet bundled" accurate (0 hits in `horus/skills.py`); both projections exist, byte-identical at v1; `.horus/research/`+`.horus/audits/` exist; `pathfinder-structured-outcome` exists; the 2026-07-21 calibration claim checks out (`backlog-librarian` shipped, PR #392) |
| F9 | `skill-audit`'s own apply-instruction has an unstated exception | **revise** (on `skill-audit`, deferred) | It says never edit projected `SKILL.md` copies; true for bundled skills, false for `wildcard`, which has no generator — its projections *are* the source. Had to improvise this |
| F10 | The ranked output makes a decision, an experiment and a code change look like the same size of thing — the owner could not tell what an idea committed them to | **revise → applied as v3** | Found by running v2 (run 4, same day): the index table carried rank/claim/branch/grounding/next-step but no kind, size, surfaces, boundary or consequence |
| F11 | **This skill's own v2 text made it subtractive.** "promote-or-**drop**" in the Purpose and "a reason to drop it outright" in the lens list steered it into pruning — which is `backlog-refine`'s and convergence's authority, not wildcard's | **revise → applied as v4** | Run 5 (v3): 4 of 6 ideas were drops/archives; owner rejected all six — "wildcards are suggestions to move the vision forward, not to drop existing work" |
| F12 | The v3 scope block was still abstract: `In scope` / `Out of scope` / `Deliverable` described topics, not changes | **revise → applied as v4** | Owner, run 5: "action points are still not clear: I need a clear indication of what the to do is, what change will be performed if that is accepted" |

## The root cause, stated once

F1 and F2 are one defect seen twice. The `wildcard` **card** describes "autonomous
pathfinder-divergence" — and divergence in pathfinder's sense is about *direction and
roadmap branches*. The **skill text** lost that: it kept the mechanism (N frames →
critic → one output) and dropped the target. Given hygiene-flavoured example frames and
no stated purpose, three runs faithfully produced hygiene findings. The agent executed
the text correctly; the text pointed at the wrong thing.

F3 is why the owner's requested fix is safe rather than a loosening: the skill conflated
*bounded blast radius* with *exactly one item*. The blast radius comes from the output
being a proposal the owner disposes of. Ranking N proposals changes nothing about that.

## Proposed replacement text (owner approves before anything is edited)

**R1 — add a Purpose section** immediately after the title, and retarget the frames:

> ## Purpose — advance the vision branches
>
> `wildcard` exists to push the project's **vision branches** forward: the
> `vision-branch-*` umbrellas and their children, each a direction that must eventually
> be promoted into a facet or dropped. Divergence here means *finding the next move on a
> branch*, not surveying operational hygiene.
>
> Read the branch umbrellas first — thesis, exists-vs-gaps map, ordered children,
> convergence criterion — and ask per branch: what evidence would move this toward
> promote-or-drop, and what is the cheapest next probe that produces it? A branch that
> has been Deferred untouched for cycles is itself a finding.
>
> Frames are lenses on **that** question. Vary them deliberately — the branch's own
> convergence criterion, its stalest unmet gap, an adjacent capability it would unlock, a
> cheaper route to its evidence, a reason to drop it outright. Operational-hygiene
> findings are in scope only when they *block* a branch; a hygiene idea with no branch
> attached is out of scope and belongs to `backlog-librarian` or `product-audit`.

**R2 — replace step 2 and step 3** (critic-to-one → rank-all):

> 2. **Critique and RANK — every valid idea survives.** Score each candidate and order
>    them high→low. Do not discard a valid idea to manufacture a single winner. Drop a
>    candidate only if it is genuinely invalid: already covered by an existing card or
>    skill, factually wrong, or outside this project's scope. Say so in one line and move
>    on — a long reject list is a symptom, not a deliverable.
>
>    Rank on: does it move a branch toward promote-or-drop · is the evidence real and
>    cited · is it cheap relative to what it settles · does it respect the PRD Rules.
>
>    **Two mandatory checks before ranking, both learned from failed runs:**
>    - **Rules check.** Read `## Rules` in PRD.md and reject anything that contradicts
>      one. A candidate proposing a new control where nothing has failed in the field
>      violates the controls ladder ("never enforce preemptively") and is invalid, not
>      merely low-ranked.
>    - **Premise check.** For every field, flag, or convention the idea relies on,
>      confirm what it *actually* means to the owner before building on it. A dated
>      field may be a floor ("not before"), not a due date ("act on").
>
> 3. **Emit the ranked set.** A table of all surviving ideas — rank, one-line claim,
>    branch it advances, cited grounding, cheapest next step. Then a short rationale
>    paragraph for the top 2-3 only. **Draft a full card only for an idea the owner
>    picks**, and offer the honest alternative: if it is small and the owner is present,
>    the PRD Rule "card what you won't do now; fix what you will" says do it now and skip
>    the card.

**R3 — Output / Quality bar / Non-goals**, replacing the "exactly one card" clauses:

> ## Output
> - A ranked table of every valid idea (typically 3-6), each citing its grounding and the
>   branch it advances.
> - Full card drafts only on request, for the ideas the owner picks.
> - If nothing clears the bar, say so and emit nothing — that is a valid result.
>
> ## Quality bar
> - Every emitted idea must be defensible on its own; ranking replaces rejection.
> - Cite grounding per idea. Check each against the open backlog for duplication.
> - Obviousness **lowers a rank, it never excludes** — an obvious idea the owner has not
>   acted on may simply be the right next move.
> - Prefer ideas whose evidence already exists over ideas needing new investigation.
>
> ## Non-goals
> - Not autonomous convergence — direction stays owner-gated (`pathfinder`).
> - Not autonomous implementation.
> - Not a card factory: ideas are ranked proposals; cards are drafted only on request.

**R4 — soften the isolation claim** (F6), replacing "frames must not anchor on each other":

> Vary the frame deliberately and do not let one frame's result shape the next. True
> branch isolation would need parallel subagents; that is a token-intensive fan-out
> requiring owner authorization under the delegation rule, so it is not the default.

## Applied state (2026-07-28)

R1-R4 were **approved and applied**, taking the skill v1 → **v2**; the first v2 run then
exposed F10, and its fix was applied the same day as **v3**. Both projections carry
`horus-skill-version: 3` and are byte-identical.

- **v2** (R1-R4): the Purpose section retargeting the skill at the vision branches;
  rank-don't-reject with every valid idea surviving; the mandatory Rules and premise
  checks; the softened frame-isolation claim; output/quality-bar/non-goals rewritten off
  "exactly one card".
- **v3** (F10): the `Kind` taxonomy (`decision` · `evidence read` · `probe` ·
  `code change` · `prose change`), a mandatory six-field scope block per idea
  (Kind · In/Out of scope · Deliverable · Touches · Consequence · Needs/Risk), a worked
  example entry, and a quality bar making an unfillable scope block a signal that the idea
  is not ready to emit rather than something to paper over.

**Validation:** the v2 run produced 6 valid ranked ideas with 2 one-line invalids, all six
attached to a named branch — against the prior three runs' 1 winner + 6 rejects and zero
branch attachment. The purpose-drift and output-shape findings are therefore closed by
evidence, not assertion. F10 is closed by inspection only; the next run is its first test.

- **v4** (F11, F12): the Purpose retargeted from "promote-or-drop" to **move the vision
  FORWARD**, with an explicit **additive-only** boundary — no drops, archives, retires,
  deprioritisations or deferrals, routed to `backlog-refine` in one line instead. The
  ranking criterion and the lens list lost their subtractive options, and the scope block
  was replaced with an **action-first** one led by `Do this` (one imperative sentence) and
  `Change performed if accepted` (the concrete before→after, naming files/commands/
  behaviour), gated by the **action test**: if it would not let a fresh agent start work,
  the idea is not ready to emit. Added a paired good/bad worked example, the bad one quoting
  this skill's own real output.

**Lesson for future skill revisions, from F11:** a revision can *introduce* a drift. F11's
subtractive steer was written by the v2 fix, not inherited from v1 — the word "drop" entered
the Purpose while fixing an unrelated defect and silently redefined the skill's job. Re-read
a revision against the skill's *purpose*, not only against the finding it was written for.

**Version mechanics:** `wildcard` v1 → **v4**. It is **not** bundled in `horus/skills.py`, so
unlike a bundled skill its two projections (`.claude/skills/wildcard/SKILL.md` and
`.agents/skills/wildcard/SKILL.md`) *are* the source and must be edited directly and kept
byte-identical. Registering it in `horus/skills.py` remains the `wildcard` card's own
dedicated-session step — this audit does not do it.

## Defers

- **F9** (`skill-audit`'s own unstated exception) — deferred to a `skill-audit` self-audit;
  recording it here rather than editing a second skill inside a one-skill audit.
- **Adjacent, out of scope:** `horus.backlog.Card` does not expose `branch:`, so
  `load_cards()` cannot be used to reason about branch membership (this audit had to regex
  the frontmatter). If wildcard's purpose becomes branch-advancing, that friction recurs.
  Belongs to a parser card or `x6-continuity-contract-declaration`, not to this skill.

## Not audited

The `github.com/uditakhourii/adhd` prior-art URL was not fetched; no web call was made for
this audit and the citation is not load-bearing for any verdict.
