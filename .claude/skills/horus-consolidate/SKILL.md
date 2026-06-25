---
name: horus-consolidate
description: >-
  Consolidate a project's Horus continuity (`.horus/`) so each lane stays in its
  lane — route shipped work into the features ledger, prune done/stale roadmap
  items, distill session notes into the durable files, and de-duplicate facts that
  drifted across roadmap.md and features.md. Use this whenever wrapping up or
  closing out a work session in a repo that has a `.horus/` directory; when the user
  says "consolidate", "wrap up", "update continuity", "tidy the roadmap", or "close
  out"; right after shipping a capability (to move it from roadmap to features); or
  whenever the `.horus/` lanes look like they've drifted. Prefer this over editing
  the `.horus/` files ad hoc, because it runs `horus consolidate` for precise signals
  first and applies consistent routing rules.
---

<!-- horus-skill-version: 2 -->

# Consolidate Horus continuity

You are running *inside* the working session, so you have something the `horus`
CLI does not: the **live context of what just happened** — decisions made, work
shipped, things discussed but not yet written to `.horus/`. Use that. The CLI sees
only the files and git; you see the conversation too. Fold both in.

## Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). It reports candidates it can detect from the files alone:
   roadmap↔features overlaps, done-but-unshipped roadmap items, session summaries to
   distill, and missing lanes. Treat these as leads, not gospel — verify each.

2. **Read the lanes.** Read `.horus/project.md`, `roadmap.md`, `features.md`,
   `decisions.md`, `history.md`, and any `sessions/*.md`. If `docs/routines.md`
   exists, it holds the full routing contract; if it's absent, the rules in this
   skill are authoritative.

3. **Apply the routing rules**, editing **`.horus/**` only** (never source files,
   never `AGENTS.md`/`CLAUDE.md`):

   - **Ship → ledger.** For each done roadmap action point that completed a
     shippable capability, close it in `roadmap.md` and add/update the matching row
     in `features.md` (move Planned/In-progress → Shipped; stamp the version if the
     repo records one, else leave blank). Capture anything shipped *this session*
     that isn't on disk yet.
   - **De-duplicate across lanes.** Where the same item sits in both `roadmap.md`
     and `features.md`, keep the *action points* in `roadmap.md` and the *capability
     status* in `features.md`. Make the split explicit with a cross-reference each
     way: put a literal `→ features.md` pointer in the roadmap item, and an `action
     points → roadmap.md` note on the features row. That pointer is the marker that
     the item was *intentionally* split (both `horus consolidate` and a future reader
     rely on it), not a leftover duplicate. No fact maintained in two places.
   - **Prune.** Drop done/obsolete roadmap items — they live in features/history/git
     now. A roadmap is "what's next", not a completed log.
   - **Distill sessions.** Fold durable content from `sessions/*.md` into the lanes
     (a decision → `decisions.md`, a lesson → `history.md`, a shipped thing →
     `features.md`), then remove or mark the distilled summary.
   - **Record fresh context.** Decisions, lessons, and shipped capabilities from the
     current session that belong in the lanes but aren't written yet — add them.
   - **Set the next step + resume prompt.** The dashboard surfaces these from
     `roadmap.md` frontmatter and never infers them, so author both:
     `next_action` (the single best next step, one imperative line) and `next_prompt`
     (a natural-language prompt to paste into a fresh Claude/Codex session to resume
     it — write it for a cold reader: name the step, point at `.horus/`; shown with a
     copy button).

4. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`. If
   `history.md` has grown into a verbatim log/changelog rather than curated lessons,
   that's a `horus-distill-history` job — flag it rather than fixing it here.

5. **Verify.** Re-run `horus consolidate`. An overlap clears once you've split the
   item *and* added the cross-reference — the `→ features.md` / `→ roadmap.md` pointer
   is how the tool knows a shared name is an intentional split, not a duplicate. An
   in-progress or planned item that legitimately lives in both lanes is *expected* to
   keep appearing until it carries that pointer; do **not** delete ledger rows or
   roadmap actions chasing zero warnings. Only done/shipped items clear by being
   pruned from the roadmap. Running the skill again on a clean tree changes nothing.

## Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is unclear,
  leave the content in place and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a coding
  task — do not continue editing source as part of it.
- Bump `last_updated` front matter on lanes you change (if it isn't already today).
