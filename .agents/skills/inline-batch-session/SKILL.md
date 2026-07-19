---
name: inline-batch-session
description: >-
  The working posture for an INLINE-BATCH session: ship each self-contained backlog
  card through its own PR, while accumulating small related ad-hoc findings from
  audits, calibration, maintenance, or review as green pushed checkpoints on one
  batch branch — no manufactured card or PR per finding. HOLD every Horus continuity
  write (PRD edits, card status/archive, session notes, `close`) until a HARD boundary
  actually arrives. Loaded automatically when a session is launched in `inline-batch`
  mode. Keep following it throughout the warm session.
---

<!-- horus-skill-version: 3 -->

# Inline-batch session

You are in **inline-batch** mode: implement and ship several self-contained backlog cards
in a row in THIS one warm session (inline, no dispatch), and **hold all Horus continuity
ceremony until a hard boundary actually arrives**. This posture is loaded at launch so it
holds across every account and model — not left to memory.

Why: dispatching each card to a fresh worker re-pays a large cold-start context-reload cost
every time, and consolidating continuity between cards just churns prose the next card — or
the eventual release — rewrites. One warm session amortizes the codebase context; one
consolidation at the boundary captures them all. (Measured:
`research/2026-07-17-delegation-cost-finding.md`.)

## Classify the unit before choosing delivery ceremony

- **Backlog card:** work already represented by a card in `.horus/backlog/`, or
  genuinely new independently schedulable work the owner approves as a card. It gets
  the one-card/one-PR delivery path below.
- **Ad-hoc finding:** a small related correction discovered while auditing,
  calibrating, grooming, reviewing, maintaining, or implementing nearby work. It does
  not get a manufactured card or standalone PR; keep it on the active batch branch.
- **Promote a finding to a card** only when it is deferred, materially expands the
  batch, needs independent acceptance or owner prioritization, or should become
  dispatchable later. This is a product judgment, not a line-count threshold.

## Every backlog card — delivery safety (never deferred, never skipped)

- Branch → PR → **reproduce the required gate on the EXACT commit** (a required CI check
  green on that SHA) + **one live probe** of the changed surface → commit, push, merge.
- A merged PR is the durable delivery; git + the PR are the receipt, so it needs no
  continuity write to be safe. Safety lives in the gate, not in the prose.
- Independently schedulable new work you spec mid-session gets a card FILE (it is the
  spec, and it travels in the PR) — but do not flip its `status:` or archive it yet
  (see below). An incidental finding does not become a card merely because it was
  discovered mid-session.

## Ad-hoc findings — one batch branch, no per-finding PR

- Keep related findings on one batch branch so the same generator, projection, or test
  files can be revised repeatedly without PR churn.
- Give each finding a proportional deterministic gate plus a live probe of the changed
  surface, then make a named commit and push it as a durable green checkpoint.
- Do not open or merge a PR for each finding. Continue the audit or calibration while
  the owner remains engaged and the batch remains coherent.
- At a natural integration point, summarize the accumulated batch and ask the owner if
  it is ready to land. Only after confirmation, open one PR, observe required CI on the
  exact commit plus a live probe, and merge.
- A pause or handoff does not force a half-ready PR: the pushed batch branch is the
  durable state. Name it in the handoff if continuity cannot otherwise resume it.

## Hold ALL continuity until a hard boundary

Defer every one of these — none is needed until a boundary actually arrives:

- `PRD.md` frontmatter / Shipped / Rules edits, and the ~250-line trim.
- `horus backlog ship` / card archiving and `status:` changes. (Solo inline needs no
  `claim` either — claiming only guards against parallel agents contending for a card.)
- Local `sessions/` notes and any `horus close`.

Between units the entire state is pushed git: open/merged PRs for cards, and the shared
batch branch for ad-hoc findings. `horus close --check`'s "delivery commits pending" line
is a reminder, not a demand to close.

## What IS a hard boundary — and what is NOT

Consolidate ONLY when one of these actually happens:

- The owner **ends or pauses** the session.
- An **agent / account / machine handoff**.
- A **version release** of what you shipped — the natural consolidation point (below).
- A **dispatch** whose receiving agent needs the durable continuity to act. If the brief +
  base SHA already carry everything, the dispatch is not a boundary for continuity.

**NOT a boundary — never trigger the consolidation on these alone:** finishing the batch,
merging the last PR, writing a wrap-up message, or being asked a follow-up while more
queued work (e.g. a pending release) remains. **Do not manufacture a boundary:** if the
owner is still engaged and work is queued, keep continuity uncommitted and keep going.

## Align the consolidation with a release when one is near

If the cards you shipped are headed for a version release, fold the continuity into the
SAME pass as the release closure — write the final "released in vX" Shipped lines once.
Writing provisional "merged, not yet released" prose now and rewriting it at release is the
exact double-ceremony this mode exists to avoid.

## At the boundary (once)

Run the `horus-consolidate` skill and fold the whole batch in: refresh frontmatter, ship
every card (`horus backlog ship <card> --pr N --sha SHA`, which archives it), move each to
`## Shipped` (one line), record any newly load-bearing Rule, trim to the line cap, then
`horus close --commit --push`. One pass; do not chase warnings to zero.

## v2 six-lane projects (fallback)

Identical posture; the single boundary consolidation updates `roadmap.md` / `features.md` /
`decisions.md` instead of `PRD.md`, following that project's closure rules. The backlog-card
delivery rungs, ad-hoc batch-branch path, and hold-continuity-to-a-hard-boundary rule are
unchanged.
