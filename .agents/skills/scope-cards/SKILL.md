---
name: scope-cards
description: >-
  Turn an owner-approved roadmap branch or equivalent direction into aligned,
  high-level backlog drafts that preserve enough context for a later refinement
  session. Use after `roadmap-branches`, or standalone when the owner says
  "scope this direction", "draft cards for this branch", or "turn this vision
  branch into cards". This is the SHAPING step, not final readiness: it never
  makes cards dispatchable or grooms an existing backlog. Advisory and
  owner-gated; only approved drafts and Vision/card diffs are written.
---

<!-- horus-skill-version: 7 -->

# scope-cards — from a chosen branch to aligned shaping drafts

You are transcribing an approved direction into cards that pass one bar:

> **The shaping test: a fresh owner+agent refinement session, given only
> `PRD.md`, the source receipt/vision branch, and this draft, understands why the
> item exists, what outcome it seeks, its broad boundaries, and which decisions
> remain — without the originating conversation.**

This skill shapes a branch; `backlog-refine` later decides readiness and owns the
single execution-ready card contract. Do not collapse those jobs back together.

## Input

One chosen branch from a `roadmap-branches` receipt, a raw `vision-branch-*` card,
or an owner-approved direction of equivalent depth. Read the branch thesis,
position/evidence, numbered roadmap, convergence criterion, Vision diffs, and
push-back verdicts. If the direction itself is ambiguous, do not silently invent
it: show the missing decision and resolve it with the owner or route it back to
`roadmap-branches`.

## Output — the shaping-draft contract

Every proposed card carries:

- frontmatter sufficient to place it: `status: open`, `priority`, `created`,
  `created_by`, `phase`, `type`, the named `vision_facet` or speculative
  `branch`, and `readiness: shaping` with a concrete `readiness_reason` naming
  the unresolved refinement work;
- **Why** — the branch reasoning and market/own-use position, not a generic title;
- **Intended outcome** — what would be different if the item proved worthwhile;
- **Broad boundaries** — the likely shape plus explicit early non-goals, without
  pretending the implementation protocol is decided;
- **Open decisions** — questions `backlog-refine` must settle before Ready;
- **Source** — receipt path/branch name or raw owner vision-branch card.

Do NOT invent final `tier`, `surface`, `parallel`, `autonomy`, dependency order,
implementation steps, supervisor acceptance, or live probes. Preserve a field
only when the source already decides it; otherwise leave it for `backlog-refine`.
An umbrella remains a thin unit-level thesis with ordered proposed children and a
convergence criterion; it is not an execution card.

**Second-order items are never pre-invented:** when work depends on findings that
do not exist yet, shape the evidence-gathering item and state that approved
findings may become later drafts. Do not fabricate findings or their fixes.

## Alongside the shaping drafts, propose the branch's edits

- **Existing-card diffs** — the demote / defer / retire push-back the branch made,
  as explicit per-card proposals (field change or archival, with the reason).
- **Vision facet diff** — exact replacement definition-of-done text per touched
  facet (add / rename / rescope / retire), never a wholesale table rewrite.
- **Vision-branch umbrella** — when the direction spans multiple cards and should
  be judged as a unit, draft or refresh a thin `vision-branch-*` umbrella (thesis,
  exists-vs-gaps map, proposed child order, convergence criterion) and stamp each
  child `branch: <umbrella-name>`. Never mirror child status into the umbrella.

## Gate, then write

Present all shaping drafts, existing-card diffs, and Vision edits as concrete
options plus a free-text alternative. Format the proposal set per the owner's
2026-07-20 calibration: ONE consolidated table with an explicit
**Existing / New** column per row (a diff to an existing card is never
visually confusable with a new draft), `phase` visible per row, no-context
prose, pasted into the terminal in an interactive session. The set MUST
include **wildcards** — explicitly divergent `phase: explore` ideas beyond the
branch's numbered items (agent-found ones welcome), each stating its
converge/drop criterion as prominently as its promise; a proposal set with
only convergent drafts is incomplete. End with a
dive-deeper-into-one-item-or-proceed offer. Let the owner approve, amend, or drop each item individually. Only
then write approved items. Owner rejections
and rescopes of existing cards land in that card's `## Reviews`; a verdict
that lives only in conversation does not bind future planning. Anything
unapproved stays unwritten.

## Deliberately omit

- No backlog-wide grooming or Ready verdict — invoke `backlog-refine`.
- No implementation, dispatch, or execution planning.
- No new receipt — the branch receipt plus the written cards are the trace.
- No detailed fields invented merely to make a shaping draft look complete.

## v2 six-lane projects (fallback)

No card files — each approved item becomes a high-level `roadmap.md` entry carrying
the same shaping context inline, and Vision edits go to `project.md` prose at the
owner's discretion. `backlog-refine` later deepens selected entries under the
six-lane project's rules. The per-item owner gate is unchanged.
