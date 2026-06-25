---
name: horus-distill-history
description: >-
  Compress a large, raw project log (a long `docs/HISTORY.md`, `CHANGELOG.md`, or an
  oversized `.horus/history.md` archive) down to the curated "bumps in the road" that
  belong in Horus's `history.md` — the problems that bit the project and the durable
  lessons they forced. Use this whenever onboarding Horus into a long-running project
  with a big changelog; when the user says "distill the history", "compress the
  changelog", "the history file is too long", or "summarize the project log"; or when
  `.horus/history.md` has grown into a timeline instead of a curated lesson set. Runs
  `horus distill-history` first for the source-log location and size.
---

<!-- horus-skill-version: 1 -->

# Distill project history

Turn a verbose log into the high-signal subset worth carrying forward. You are not
writing a timeline — you are keeping only what a future agent would otherwise have
to re-learn the hard way.

## Steps

1. **Locate + size the source.** Run `horus distill-history` (optionally
   `--path <repo>` / `--source <file>`). It reports the source log it found and the
   current `history.md` size, so the compression target is explicit.

2. **Read the source log** in full (or in chunks if very large).

3. **Apply the signal test** to every entry:
   - **Keep** — a real problem the project hit *and* the durable lesson or design
     change it forced. The kind of thing that prevents a repeat mistake.
   - **Drop** — routine changelog noise, version-bump entries, resolved-and-now-
     irrelevant incidents, and anything already captured as a rule in `decisions.md`
     (cross-reference it instead of duplicating).

4. **Write the curated subset** into `.horus/history.md`: short, deduplicated
   "bumps in the road", each pairing the problem with the lesson. Not a timeline,
   not open issues (those live in `roadmap.md`).

5. **Freeze the source**, don't delete it: add a one-line "superseded — curated in
   `.horus/history.md`" pointer at its top so the two don't drift.

## Boundaries

- Only compress what the log records — **never invent** incidents, dates, or causes.
- Edit `.horus/history.md` (and the one-line pointer atop the source log); nothing else.
