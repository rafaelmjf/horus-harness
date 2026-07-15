---
name: horus-infer
description: >-
  Bootstrap or refresh a project's Horus continuity (`.horus/`) by distilling the
  project's own canonical docs — README, status/roadmap files, CLAUDE.md/AGENTS.md,
  and linked docs — into `.horus/`: the PRD-structure `PRD.md` skeleton (Vision /
  Backlog / Shipped / Rules) on a v3 project, or the six-lane structure on a v2
  project. Use this when setting Horus up in an existing repo that already has useful docs;
  when the user says "set up horus here", "bootstrap the .horus files", "populate
  the continuity", "infer the project state", or "fill in the backlog/roadmap from
  our docs". A blank scaffold is valid until a real use case or evidenced docs exist.
  Runs `horus infer` first to find canonical docs and empty/placeholder sections.
---

<!-- horus-skill-version: 4 -->

# Infer Horus continuity from the project's docs

Most repos already encode their state in prose (a README, a status doc, a roadmap).
This distills that into `.horus/` as the single concise source of "what is this and
what's next" — pointing at the canonical docs rather than copying them, so the two
never drift.

`horus infer` reports which structure the project uses — follow the matching
section below.

Do not invoke inference merely because `horus init` produced blank placeholders.
With no useful source truth and no concrete user request, leave the scaffold blank.

## PRD-structure projects (v3 — `.horus/PRD.md` present)

1. **Get the signals.** Run `horus infer` (optionally `--path <repo>`). It lists
   the canonical docs to distill from and which `PRD.md` skeleton sections
   (Vision / Backlog / Shipped / Rules) are missing or still placeholder text.

2. **Read the canonical docs and follow their pointers** — README → status/roadmap →
   CLAUDE.md/AGENTS.md → linked docs like `docs/*.md`. Build a real model of the
   project before writing anything.

3. **Distill into `PRD.md`**, one file, each section concise:
   - Frontmatter: `status`, `current_focus`, `next_action`, `next_prompt`,
     `execution_recommendation`, `last_updated`.
   - `## Vision` — what the project is, its shape, and explicit out-of-scope
     boundaries.
   - `## Backlog` — retain the thin pointer. Create one
     `.horus/backlog/<slug>.md` card per evidenced open item, with
     `status`/`priority`/`type` frontmatter; do not create a starter card.
   - `## Shipped` — **one line per capability**, not a paragraph; the deep
     detail lives in git history, not here.
   - `## Rules` — durable, current invariants only (not a dated log — if the
     docs describe *why* a rule exists or a superseded alternative, that
     rationale belongs in git history, an optional recovery note when needed, or
     `.horus/archive/`, not `PRD.md`).

4. **Don't duplicate.** Where a canonical doc stays the deep reference (e.g. a
   detailed architecture doc), point at it from `PRD.md` instead of copying it
   wholesale. Keep the whole file well under the ~250-line cap — `horus
   consolidate` will start warning past 235.

5. **Mark superseded docs — only when truly superseded.** If a doc's "current
   state / next steps" role now lives in `PRD.md`, add a one-line pointer at
   its top. But if `PRD.md` merely *distills* a doc that stays the canonical
   deep reference, add no pointer. Ask before substantially rewriting any
   source doc.

### Boundaries

- When intent is genuinely unclear (real status, priorities, what shipped vs
  planned), **ask the user** rather than guess. Never invent decisions, dates,
  or versions — `## Rules` in particular: only record an invariant the docs
  actually state; leave it thin rather than manufacturing one.
- Edit scope is `.horus/PRD.md`, plus — with care and consent — a one-line
  pointer atop a superseded source doc.

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — infer into the six lanes as before.

1. **Get the signals.** Run `horus infer` (optionally `--path <repo>`). It lists the
   canonical docs to distill from and which `.horus/` lanes are missing or still hold
   `horus init` placeholders. If `.horus/` doesn't exist yet, run `horus init` first.

2. **Read the canonical docs and follow their pointers** — README → status/roadmap →
   CLAUDE.md → linked docs like `docs/*.md`. Build a real model of the project before
   writing anything.

3. **Distill into the lanes**, each in its lane:
   - `project.md` — what it is, current shape, boundaries, current focus.
   - `roadmap.md` — open action points (what's next), grouped.
   - `features.md` — shipped / in-progress / planned capabilities.
   - `decisions.md` — durable decisions + reasoning, dated.
   - `history.md` — curated lessons / bumps in the road (use `horus-distill-history`
     if there's a big log).
   - `execution.md` — optional active execution plan only if the canonical docs
     describe current phased/subagent work.

4. **Don't duplicate.** Where a canonical doc stays the deep reference, point at it
   from `.horus/` instead of copying it wholesale. The lanes are concise.

5. **Mark superseded docs — only when truly superseded.** If a doc's "current state /
   next steps" role now lives in `.horus/`, add a one-line pointer at its top. But if
   `.horus/` merely *distills* a doc that stays the canonical deep reference, add no
   pointer — just point at the doc from `.horus/`. Ask before substantially rewriting
   any source doc.

### Boundaries

- When intent is genuinely unclear (real status, priorities, what shipped vs planned),
  **ask the user** rather than guess. Never invent decisions, dates, or versions —
  `decisions.md` in particular: only record a decision the docs actually state with
  reasoning; leave it empty rather than manufacturing one.
- Edit scope is `.horus/**`, plus — with care and consent — a one-line pointer atop a
  superseded source doc.
