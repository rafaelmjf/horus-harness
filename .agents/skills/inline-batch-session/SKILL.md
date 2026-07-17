---
name: inline-batch-session
description: >-
  The working posture for an INLINE-BATCH session: implement and ship several
  self-contained backlog cards in a row in one warm session, and HOLD the canonical
  continuity write until the session boundary. Loaded automatically when a session is
  launched in `inline-batch` mode (it does not depend on the model remembering a rule).
  Use/keep following it whenever you are shipping multiple cards inline without dispatch.
---

<!-- horus-skill-version: 1 -->

# Inline-batch session

You are in **inline-batch** mode. You will implement and ship several self-contained
backlog cards in a row in THIS one warm session (inline, no dispatch), and you **hold the
continuity ceremony until the end**. This posture is loaded at launch so it holds across
every account and model — not left to memory.

Why this mode exists: dispatching each card to a fresh worker re-pays a large cold-start
context-reload cost every time, and closing continuity after every card just churns prose
the next card rewrites. One warm session amortizes the codebase context across cards, and
one consolidation at the end captures them all. (Measured:
`research/2026-07-17-delegation-cost-finding.md`.)

## Every card — the delivery-safety rungs (never skip, regardless of mode)

- Work on a branch → open a PR → **reproduce the required gate on the EXACT commit**
  (a required CI check green on that SHA), plus **one live probe** of the changed surface.
- Commit and push; after merge, `horus backlog ship <card> --pr N --sha SHA`.
- These are non-negotiable and unchanged by the batching below — safety lives in the gate,
  not in the continuity write.

## Batch to the boundary — do NOT do per card

- Do **not** run a full canonical continuity close after each card. Defer the `PRD.md`
  frontmatter / Shipped / Rules write and any line-cap trim to **ONE** consolidation pass at
  the session boundary (end, pause, or an agent/account/machine change), covering all cards.
- This is the `handoff` granularity made explicit and loaded: pushed git/PR/archived-card
  state is the durable receipt between cards, and the "delivery commits pending" line from
  `horus close --check` is a reminder, not a demand to close now.
- The PRD line-cap (~250) is its own deliberate hygiene pass — never folded into a per-card
  close.

## At the session boundary (once)

- Run the `horus-consolidate` skill and fold the whole batch in: refresh frontmatter, move
  every shipped card to `## Shipped` (one line each), record any newly load-bearing Rule,
  then `horus close --commit --push`. One pass; do not chase warnings to zero.

## v2 six-lane projects (fallback)

Identical posture; the single end-of-session consolidation updates `roadmap.md` /
`features.md` / `decisions.md` instead of `PRD.md`, following that project's closure rules.
The per-card delivery-safety rungs and the defer-continuity-to-the-boundary rule are unchanged.
