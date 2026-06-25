---
name: horus-infer
description: >-
  Bootstrap or refresh a project's Horus continuity (`.horus/`) by distilling the
  project's own canonical docs — README, status/roadmap files, CLAUDE.md/AGENTS.md,
  and linked docs — into the clean six-lane structure. Use this when setting Horus up
  in an existing repo that already has docs; when the user says "set up horus here",
  "bootstrap the .horus files", "populate the continuity", "infer the project state",
  or "fill in the roadmap from our docs"; or right after `horus init` left placeholder
  lanes. Runs `horus infer` first to find the canonical docs and the empty lanes.
---

<!-- horus-skill-version: 1 -->

# Infer Horus continuity from the project's docs

Most repos already encode their state in prose (a README, a status doc, a roadmap).
This distills that into `.horus/` as the single concise source of "what is this and
what's next" — pointing at the canonical docs rather than copying them, so the two
never drift.

## Steps

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

4. **Don't duplicate.** Where a canonical doc stays the deep reference, point at it
   from `.horus/` instead of copying it wholesale. The lanes are concise.

5. **Mark superseded docs.** If a doc's "current state / next steps" role now lives in
   `.horus/`, add a one-line pointer at its top. Ask before substantially rewriting a
   source doc.

## Boundaries

- When intent is genuinely unclear (real status, priorities, what shipped vs planned),
  **ask the user** rather than guess. Never invent decisions, dates, or versions.
- Edit scope is `.horus/**`, plus — with care and consent — a one-line pointer atop a
  superseded source doc.
