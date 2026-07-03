---
name: horus-distill-history
description: >-
  Compress a large, raw project log (a long `docs/HISTORY.md`, `CHANGELOG.md`, or an
  oversized history archive) down to the curated "bumps in the road" worth carrying
  forward — the problems that bit the project and the durable lessons they forced.
  On a PRD-structure (v3) project the curated result lives in
  `.horus/archive/history.md`, with any still-load-bearing rule folded into `PRD.md`'s
  `## Rules`; on a six-lane (v2) project it's `.horus/history.md` directly. Use this
  whenever onboarding Horus into a long-running project with a big changelog; when
  the user says "distill the history", "compress the changelog", "the history file
  is too long", or "summarize the project log"; or when the curated history has grown
  into a timeline instead of a lesson set. Runs `horus distill-history` first for the
  source-log location and size.
---

<!-- horus-skill-version: 3 -->

# Distill project history

Turn a verbose log into the high-signal subset worth carrying forward. You are not
writing a timeline — you are keeping only what a future agent would otherwise have
to re-learn the hard way.

## PRD-structure projects (v3 — `.horus/PRD.md` present)

The curated target is **`.horus/archive/history.md`** — in this structure history is
retired-lane material, not an actively maintained file (`PRD.md`'s `## Rules` section
is the *current*-state surface; this archive is the *why* behind it, same idea as
`decisions.md` + `history.md` in v2, just no longer live lanes).

1. **Locate the source.** Run `horus distill-history` (optionally `--path <repo>` /
   `--source <file>`) for the source log it found. Its `.horus/history.md missing`
   line is a known false note on v3 projects — the deterministic pre-pass predates
   the archive convention and doesn't look in `.horus/archive/` yet; ignore that
   line and check `.horus/archive/history.md`'s current size yourself.

2. **Read the source log** in full (or in chunks if very large).

3. **Apply the signal test** to every entry — same test as v2 below: keep a real
   problem plus the durable lesson/design change it forced; drop routine noise,
   version bumps, and anything already captured as a `PRD.md` `## Rules` entry
   (cross-reference instead of duplicating).

4. **Write the curated subset** into `.horus/archive/history.md` (create the
   `archive/` directory if this is the first distillation): short, deduplicated
   "bumps in the road", each pairing the problem with the lesson. Not a timeline.

5. **Promote load-bearing lessons.** If a lesson amounts to an invariant the
   project must keep obeying (not just "this happened once"), also add a
   concise one-liner to `PRD.md`'s `## Rules` — that's the surface a cold
   reader actually checks day to day.

6. **Forward open work, don't drop it.** Roadmap-shaped material (backlog,
   "next session", planned-but-not-done) isn't history — note it for the user
   to fold into `PRD.md`'s `## Backlog` rather than silently dropping it. (This
   skill edits history/archive material, so flag it; don't edit `## Backlog`
   here.)

7. **Freeze the source**, don't delete it: add a one-line "superseded —
   curated in `.horus/archive/history.md`" pointer at the top of its body
   (below any YAML front matter) so the two don't drift.

### Boundaries

- Only compress what the log records — **never invent** incidents, dates, or causes.
- Edit `.horus/archive/history.md`, at most a one-line addition to `PRD.md`'s
  `## Rules`, and the one-line pointer on the source log; nothing else.

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the curated target is `.horus/history.md` directly, as before.

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

   - If the source *already* contains a curated/highlights section plus a raw
     archive, treat the highlights as just more input — re-derive across the whole
     log and merge, rather than copying the existing summary verbatim.

4. **Write the curated subset** into `.horus/history.md`: short, deduplicated
   "bumps in the road", each pairing the problem with the lesson. Aim for a scannable
   set (roughly a dozen or two high-signal entries), not a line-for-line rewrite —
   if you're keeping most of the log, you're not distilling. Not a timeline, not open
   issues.

5. **Forward open work, don't drop it.** If the log contains roadmap-shaped material
   (backlog, "next session", planned-but-not-done), that's not history — note it for
   the user to fold into `roadmap.md` rather than silently dropping it. (This skill
   edits `history.md`, so flag it; don't edit `roadmap.md` here.)

6. **Freeze the source**, don't delete it: add a one-line "superseded — curated in
   `.horus/history.md`" pointer at the top of its body (just below any YAML front
   matter, so the front matter stays first) so the two don't drift.

### Boundaries

- Only compress what the log records — **never invent** incidents, dates, or causes.
- Edit `.horus/history.md` (and the one-line pointer on the source log); nothing else.
