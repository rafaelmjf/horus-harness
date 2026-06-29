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

<!-- horus-skill-version: 5 -->

# Consolidate Horus continuity

You are running *inside* the working session, so you have something the `horus`
CLI does not: the **live context of what just happened** — decisions made, work
shipped, things discussed but not yet written to `.horus/`. Use that. The CLI sees
only the files and git; you see the conversation too. Fold both in.

## Two jobs — do not conflate them

This skill spans two sizes of work. **Do the per-session close every time; do the
backlog pass only when the user asks for it.** Conflating them is why lanes drift:
the per-session part gets half-done because the backlog looks huge.

- **Per-session close (always, bounded):** capture *this* session and make the
  dashboard reflect it. Small and complete — only this session's delta plus the
  dashboard fields below. Steps 3–4.
- **Backlog consolidation (occasional, opt-in):** distill the *accumulated* old
  sessions, move historical done-items into features, split long-standing overlaps.
  A large, separate pass — run it only on an explicit "pay down continuity debt" /
  "consolidate the backlog" request. Step 5. The signals will report a big backlog
  (many done items / undistilled sessions); that pressure is for *this* job, not the
  per-session close — **do not try to clear it every time.**

## The dashboard contract — keep these current at EVERY close

The dashboard renders exactly these as the project's *current* state and never
infers them. If this session moved the project, each must reflect it before you
finish:

- `project.md` → `current_focus` (frontmatter): the one-line "where things are now".
- `roadmap.md` → `next_action` (the single NEXT) and `next_prompt` (the resume prompt).
- `roadmap.md` → `execution_recommendation`: analyze the NEXT and say whether to
  continue directly or prepare `execution.md` + worker/subagents.
- `roadmap.md` → the checkbox states behind the progress bar (mark what this session did).
- `features.md` → a row for anything **shipped this session** (Planned/In-progress → Shipped).
- `execution.md` → active phase status and supervisor/worker handoff state, when this
  session was part of a phased execution plan.
- `last_updated` frontmatter on every lane you touched (bump to today).

`horus close --check` is the gate: it fails (non-zero) while any of these is stale,
so closure isn't done until it passes. It also backs a pre-merge CI check.

## Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). It reports file-only candidates: roadmap↔features overlaps,
   done-but-unshipped items, session summaries to distill, missing lanes. Leads, not
   gospel — and most belong to the backlog job (Step 5), not this close.

2. **Read the lanes.** Read `.horus/project.md`, `roadmap.md`, `features.md`,
   `decisions.md`, `history.md`, optional `execution.md`, and the newest
   `sessions/*.md` / `temp/*.md` handoff notes. If `docs/routines.md` exists it
   holds the full routing contract; otherwise this skill is authoritative.

3. **Per-session close — record this session** (`.horus/**` only; never source,
   `AGENTS.md`, or `CLAUDE.md`):

   - **Record fresh context.** Decisions + *why*, lessons/dead-ends, and capabilities
     shipped *this session* that aren't on disk yet → `decisions.md` / `history.md` /
     `features.md` (a Shipped row for each capability). This is the content only you
     can supply — it's in the conversation, not the files.
   - **Update the dashboard contract** (the checklist above): refresh `current_focus`,
     `next_action`, `next_prompt`, the roadmap checkboxes for what you did, and bump
     `last_updated` on touched lanes. Author the next step for a *cold* reader — name
     it, point at `.horus/`.
   - **Recommend the execution mode for the NEXT.** If the next step is small,
     single-surface, low-risk, or mostly continuity/docs, set `execution_recommendation:
     "continue-as-is — <why>"`. If it is multi-phase, cross-module, risky, or benefits
     from supervisor/worker review, set `execution_recommendation: "plan-execution —
     <why>"` and create/update `execution.md` before implementation starts.
   - **When a worker handoff exists** in `.horus/temp/`, use it as evidence, not as
     truth: the supervisor reviews the diff/tests, then distills accepted facts into
     durable lanes and updates `execution.md`.

4. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`. If
   `history.md` has grown into a verbatim log, that's a `horus-distill-history` job —
   flag it, don't fix it here. `execution.md` is fluid active coordination; archive
   or replace it when the roadmap item is done.

5. **Backlog consolidation — ONLY when explicitly asked.** Distill old `sessions/*.md`
   and stale `temp/*.md` handoff notes into the lanes then remove them; move historical done items into `features.md` and
   **prune** them from `roadmap.md`; **de-duplicate** roadmap↔features overlaps by
   keeping action points in `roadmap.md` and status in `features.md`, with a literal
   `→ features.md` / `action points → roadmap.md` cross-reference each way (that
   pointer is how `horus consolidate` knows a shared name is an *intentional* split,
   not a duplicate). Skip this entirely during a normal close.

6. **Verify.** Run `horus close --check` — it must pass (the dashboard is fresh). For
   a backlog pass, also re-run `horus consolidate`: an overlap clears only once split
   *and* cross-referenced; in-progress/planned items that legitimately live in both
   lanes keep appearing until they carry the pointer — **do not delete ledger rows or
   roadmap actions chasing zero.**

## Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is unclear,
  leave the content and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a coding task.
- Bump `last_updated` front matter on lanes you change (if it isn't already today).
