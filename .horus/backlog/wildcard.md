---
status: shelved
shelved_on: 2026-08-01
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
readiness: shaping
readiness_reason: "A 'fun to try' exploratory idea; the grounding (what steers the exploration), the quality bar, and the run substrate are unscoped. Explore before drafting the skill."
topic: po-lifecycle
type: spike
depends-on: pathfinder-structured-outcome
---

# wildcard — an autonomous divergence skill that emits ONE reviewable card

## Why — owner, 2026-07-21

`pathfinder` is deliberately attended: direction-setting (convergence) is owner
territory. But this session's autonomy discussion suggests a safe autonomous sibling.
The principle we landed on: **autonomy is safe when the blast radius is bounded and
reversible — and a card is the ultimate bounded output** (nothing ships, nothing
changes, it's a reversible proposal). So the *divergence/discovery* step can run
unattended even though *convergence* and *implementation* cannot.

`wildcard` = autonomous pathfinder-divergence, minus convergence, minus implementation.
It runs on its own, explores, and produces ONE well-defined candidate card for the
owner to revise / approve / discard. **Nothing is implemented without owner approval** —
the output is a proposal, not a change.

This is literally `refine-autonomy-hardening-lens` applied to pathfinder: isolate the
one autonomizable step (divergence → a bounded-output card) from the intrinsic-attended
steps (direction, taste, shipping).

## Grounding — the pathfinder run (owner-decided, 2026-07-21)

Not free-roaming. `wildcard` is grounded on a **pathfinder run** — either a **fresh** one
(if the owner wants current evidence) or the **previous** run's saved artifacts. Every
pathfinder run already persists its evidence: the position brief, the `product-audit`
receipt, the `market-scan` receipt, and the `roadmap-branches` divergence tree (dated,
under `.horus/research/` and `.horus/audits/`). Wildcard reads that artifact set and
autonomously synthesises **ONE** opportunity worth a card — effectively an autonomous
"convergence into a single proposal" over pathfinder's divergence evidence, safe because
the output is a card, not a direction commitment.

**Fresh vs previous — the tradeoff:**

- **Previous run (default):** cheap, no re-gathering; risk is staleness — cite the
  artifacts' dates and flag when the run is old.
- **Fresh run:** current evidence, but re-runs the (autonomizable) evidence steps
  (`product-audit` / `market-scan`) at real token cost. Convergence and direction stay
  the owner's; only the evidence-gathering + single-proposal synthesis is autonomous.

Each emitted card cites the specific artifacts it was grounded in.

## Quality bar (open)

- Emit ONE evidence-grounded card per run, self-critiqued / ranked — resist dumping a
  flood of low-value cards.
- Each proposal cites its grounding (the gap / receipt / friction it came from).

## Why it's a good autonomous-loop candidate

Zero-blast-radius output makes it near-ideal food for the scheduled away-mode loop (cf.
`autotest-e2e-away-mode-drill`): a real autonomous job that pings the owner with a card
to review — exercising the dispatch infra with no merge risk. Fun *and* a safe exercise
of the autonomous substrate.

## Prior art / to explore

- **`github.com/uditakhourii/adhd`** (owner-flagged, 2026-07-21) — a coding-agent skill
  implementing divergence-then-convergence *by design*: spawn N **isolated** reasoning
  branches under different cognitive frames (branches never see each other → no
  anchoring), then a **separate critic** pass scores every idea, flags traps, clusters by
  angle, and deepens the top-K survivors. Framed as "an architectural fix for premature
  convergence in autoregressive reasoning." Directly relevant to wildcard's
  divergence → one-card mechanism (generate under N frames, self-critique to one) and to
  pathfinder's `roadmap-branches`. Explore whether to adopt the isolated-frames +
  separate-critic structure (it maps cleanly onto the Workflow parallel/judge patterns).

## Non-goals

- Not autonomous convergence — direction stays owner-gated, via `pathfinder`.
- Not autonomous implementation — the emitted card follows the normal
  refine → approve → implement path.

## Prerequisite — structured pathfinder run outcome (`pathfinder-structured-outcome`)

For wildcard to load a *coherent* set from "the previous pathfinder run," the artifacts
must be grouped by run. Today they land as **dated receipts** in `.horus/research/` and
`.horus/audits/` — not tied together. This is now its own card,
**`pathfinder-structured-outcome`** (refine the chain to emit an addressable per-run
bundle + manifest); wildcard `depends-on` it for the "previous run" path.

## Open questions

- Fresh vs previous default + staleness flagging (see Grounding).
- Run substrate (scheduled job vs on-demand); cadence + a bounded token budget per run.
- (Resolved) run-bundle/manifest is now its own card, `pathfinder-structured-outcome`.
- Overlap with `pathfinder` / `scope-cards` / `market-scan` — it reuses their divergence
  machinery but strips the attended gates; position so it is not a duplicate.

## Source

In-session, 2026-07-21 (owner idea — "could be fun to try and test to see what outcomes
we get"; grounding decided same session). Related: `pathfinder`, `scope-cards`,
`market-scan`, `refine-autonomy-hardening-lens`, `autotest-e2e-away-mode-drill`.

## Reviews

- 2026-07-21 — **Grounding decided** (owner): wildcard runs on a pathfinder run's saved
  artifacts (fresh or previous), not free-roaming — resolving the pure-wild-vs-grounded
  question toward grounded. Surfaced a likely prerequisite: a per-run artifact
  bundle/manifest so the previous run's evidence can be loaded coherently.
- 2026-07-21 — **v0 skill drafted + calibrated** (owner): a dry-run grounded on the live
  session produced the `backlog-librarian` card; the owner judged it good and adopted it. A
  v0 `SKILL.md` draft now lives at `.claude/skills/wildcard/` (+ `.agents/` parity), NOT yet
  bundled in `horus/skills.py` — the registry/version wiring + install verification is the
  dedicated-session step this card drives.

## Field evidence — recency anchoring beats the frame rules (2026-07-31)

Two consecutive v4 runs produced **zero** branch-advancing ideas; the owner's verdict was
"fully focused on skills, no actual features but small adjustments and definition changes."
That is the **fifth** run with this failure — the 2026-07-28 audit already recorded three,
and v2/v4 were both written to stop it. Diagnosis from the runs themselves:

- **Recency beat the stated grounding.** The skill's default grounding is a pathfinder
  bundle; both runs used the *live session* as the de facto spine, and that session was
  entirely skills work (#462-#466). Every "distinct lens" was a lens on what had just been
  done. Run 2's top-ranked idea was a regression from a PR merged minutes earlier — that is
  follow-up, not divergence.
- **The branch umbrellas were never engaged.** Zero proposals from X3/X4/X5/X6 across both
  runs, despite the Procedure saying to read them. When run 3 pinned frames to the umbrellas
  and excluded skills/process by construction, it produced five branch-level moves from
  material that had been sitting there the whole time — including that
  `autotest-e2e-away-mode-drill`'s "Deferred until after 2026-07-29" trigger had silently
  expired. So the failure is frame selection, not a shortage of feature material.
- **The worked example still demonstrates hygiene.** v4's example is a `usage_at_close`
  frontmatter stamp — plumbing — so the text tells the reader not to do hygiene while
  showing hygiene. Same defect the 2026-07-28 audit named in v2's example frames.
- **A structural tension, not just operator error.** X4/X5 are `deferred` and X3 `gated`,
  and PRD forbids re-raising X5's hold. Wildcard is additive-only and must respect holds, so
  it drifts to whichever facet has live work. Nothing in the text says that *advancing* a
  parked branch is in scope while *unparking* it is not — run 3 had to derive that.

Candidate fixes for the dedicated session (not decided): replace the worked example with a
branch-advancing one; require ≥1 proposal per umbrella or an explicit "nothing here, because
X"; state that parked branches are valid divergence targets; and make the grounding step
refuse to fall back to live-session context when a pathfinder bundle exists but is stale —
say so and offer the refresh instead. Run 3's output: `research/2026-07-31-wildcard-branch-divergence.md`.
