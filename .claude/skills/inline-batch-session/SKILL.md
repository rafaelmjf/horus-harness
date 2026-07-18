---
name: inline-batch-session
description: >-
  The working posture for an INLINE-BATCH session: implement and ship several
  self-contained backlog cards in a row in one warm session, and HOLD every Horus
  continuity write (PRD edits, card status/archive, session notes, `close`) until a HARD
  boundary actually arrives — never on merely finishing the cards. Loaded automatically
  when a session is launched in `inline-batch` mode (it does not depend on the model
  remembering a rule). Keep following it whenever you ship multiple cards inline.
---

<!-- horus-skill-version: 2 -->

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

## Every card — delivery safety (never deferred, never skipped)

- Branch → PR → **reproduce the required gate on the EXACT commit** (a required CI check
  green on that SHA) + **one live probe** of the changed surface → commit, push, merge.
- A merged PR is the durable delivery; git + the PR are the receipt, so it needs no
  continuity write to be safe. Safety lives in the gate, not in the prose.
- New work you spec mid-session gets a card FILE (it is the spec, and it travels in the
  PR) — but do not flip its `status:` or archive it yet (see below).

## Hold ALL continuity until a hard boundary

Defer every one of these — none is needed until a boundary actually arrives:

- `PRD.md` frontmatter / Shipped / Rules edits, and the ~250-line trim.
- `horus backlog ship` / card archiving and `status:` changes. (Solo inline needs no
  `claim` either — claiming only guards against parallel agents contending for a card.)
- Local `sessions/` notes and any `horus close`.

Between cards the entire state is pushed git + open/merged PRs. `horus close --check`'s
"delivery commits pending" line is a reminder, not a demand to close.

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
`decisions.md` instead of `PRD.md`, following that project's closure rules. The per-card
delivery-safety rungs and the hold-continuity-to-a-hard-boundary rule are unchanged.
