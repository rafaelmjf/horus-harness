---
name: scope-cards
description: >-
  Populate a chosen roadmap branch (or any approved direction) into fully
  SELF-SUFFICIENT backlog card drafts — frontmatter plus context, concrete how,
  acceptance, and non-goals — so a fresh agent session can pick any card up and
  start with the same understanding, needing nothing from the originating
  conversation. Step 4 of the pathfinder flow, also standalone ("scope this
  card", "populate cards for this direction"). Also drafts the branch's implied
  Vision facet edits and the demote/defer/retire diffs for existing cards the
  branch pushed back on. Advisory: presents every draft first; the owner approves
  per item; only approved items are written.
---

<!-- horus-skill-version: 2 -->

# scope-cards — from a chosen branch to a fresh-agent-ready backlog

You are transcribing an approved direction into cards that pass one bar:

> **The self-sufficiency test: a fresh agent session, given only `PRD.md` and this
> card, can start the work correctly — same understanding, no access to the
> conversation that produced it.**

## Input

One chosen branch from a `roadmap-branches` receipt (or an owner-approved
direction of equivalent depth). Each item needs why / how / suspected weak points /
non-goals already argued. **If an item arrives thin, do not silently invent the
missing depth** — flag it and resolve it with the owner (or send it back through
`roadmap-branches`) before drafting its card.

## Card draft template

Frontmatter: `status: open`, `priority`, `tier`, `vision_facet` (matched to a
`## Vision` table facet), `phase` (`converge` default; `explore` for divergent
bets), `created`. Body:

- **Why** — the context paragraph carrying the branch's reasoning, INCLUDING the
  market-position line ("exists but misses X / we have Y but miss Z"), so the card
  survives without the receipt.
- **How** — the concrete protocol or first step, specific enough to begin from.
- **Acceptance** — one testable line. `phase: explore` cards instead carry an exit
  line: the cheap PoC and the explicit verdict it must end in (adopt / promote /
  drop — dying cheap is a valid success).
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
