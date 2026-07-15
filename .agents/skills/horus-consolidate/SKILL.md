---
name: horus-consolidate
description: >-
  Consolidate a project's Horus continuity (`.horus/`). On a PRD-structure (v3)
  project this is a light backlog-hygiene pass over the single `PRD.md` file
  (line-count vs the cap, stale frontmatter, undistilled session notes,
  duplicate or lingering-done backlog items). On a six-lane (v2) project it
  routes shipped work into the features ledger, prunes done/stale roadmap
  items, distills session notes into the durable files, and de-duplicates
  facts that drifted across roadmap.md and features.md. Use this whenever
  wrapping up or closing out a work session in a repo that has a `.horus/`
  directory; when the user says "consolidate", "wrap up", "update continuity",
  "tidy the roadmap"/"tidy the backlog", or "close out"; right after shipping a
  capability; or whenever `.horus/` looks like it's drifted. Prefer this over
  editing `.horus/` ad hoc, because it runs `horus consolidate` for precise
  signals first and applies consistent routing rules.
---

<!-- horus-skill-version: 10 -->

# Consolidate Horus continuity

You are running *inside* the working session, so you have something the `horus`
CLI does not: the **live context of what just happened** — decisions made, work
shipped, things discussed but not yet written to `.horus/`. Use that. The CLI sees
only the files and git; you see the conversation too. Fold both in.

`horus consolidate` inspects `.horus/` and reports the signals for whichever
structure the project uses — follow the matching section below.

## PRD-structure projects (v3 — `.horus/PRD.md` present)

`PRD.md` is the **one maintained continuity file**: frontmatter (`status`,
`current_focus`, `next_action`, `next_prompt`, `execution_recommendation`,
`last_updated`) plus Vision / Backlog / Shipped / Rules sections. `sessions/`
(one note per session) and `temp/` (fleeting worker handoff notes) are
**unchanged** from six-lane projects.

### Two jobs — do not conflate them

- **Per-session close (always, bounded):** fold this session's delta into
  `PRD.md` and refresh the frontmatter handoff fields.
- **Backlog hygiene (small, do it whenever `horus consolidate` flags it):** trim
  the file back under the line cap, delete done items, split duplicate titles.
  Mechanical — no need to wait for an explicit "pay down continuity debt" ask
  the way v2's backlog pass does; a v3 PRD drifts fast if hygiene waits.

### The dashboard contract — keep these current at EVERY close

The shared reader (`resolve_focus`) is PRD-first, so `current_focus`,
`next_action`, `next_prompt`, and `execution_recommendation` must live in
`PRD.md` frontmatter (not a shim). `horus close --check` fails while any of
them is stale or empty.

### Steps

1. **Get the deterministic signals.** Run `horus consolidate` (optionally
   `--path <repo>`). On a v3 project it reports **backlog-hygiene signals
   only** — no lane-routing/overlap warnings, because there are no lanes to
   route between:
   - **Line count vs the ~250-line cap** — warns past 235, more urgently past
     250. Fix by trimming: one-line `## Shipped` entries, deleted done backlog
     items (git remembers them, no need to keep them around).
   - **Stale frontmatter** — `last_updated` older than the newest `sessions/`
     note date. Refresh the content and bump the date.
   - **Undistilled session notes** — more than a dozen files directly in
     `sessions/` (excluding `README.md` and `archive/`). Move older ones to
     `sessions/archive/` (local, git-ignored, doesn't count against the cap).
   - **Duplicate backlog titles** — two `## Backlog` items whose bold
     `**Title**` text matches case-insensitively. Merge or rename one.
   - **Lingering done items** — a backlog item checked `[x]` or prefixed
     `DONE`/`Done:`. Delete the item; a `**Result … PASS**` note continuing a
     still-open item is not itself a done marker, leave those.

2. **Read `PRD.md`**, the newest `sessions/*.md` note, and any `temp/*.md`
   handoff notes awaiting review.

3. **Record this session, in `PRD.md` only** (never source, `AGENTS.md`, or
   `CLAUDE.md`):
   - Fold capabilities shipped *this session* into `## Shipped` as **one line
     each** — not a paragraph; detail lives in git history and session notes.
   - Add or update `## Backlog` items for new or changed open work.
   - Add any newly load-bearing invariant to `## Rules`, concise and
     current-state only (not a dated log — that's what `sessions/` and git
     history are for).
   - Refresh the frontmatter handoff fields and bump `last_updated`. Same
     judgment as v2 for `execution_recommendation`: `"continue-as-is — <why>"`
     for small/ambiguous/exploratory/debugging work, `"plan-execution — <why>"`
     for high-volume low-ambiguity work with a clear gate (create/update
     `execution.md` before implementation starts). The `<why>` must name what
     delegation actually buys *on this runtime* — a frontier supervisor +
     cheaper worker tiers gains context hygiene AND a cheaper tier; a single
     strong model gains mostly context hygiene, so its bar is higher. Do not
     sell supervisor review as the safeguard (reproduce the gate / bound
     checkpoints / safety-in-code are the durable ones).
   - When a `temp/` worker handoff note exists, treat it as evidence, not
     truth: review the diff/tests yourself, then fold the accepted facts into
     `PRD.md` and update `execution.md` if a phase completed.

4. **Apply backlog hygiene** for whatever Step 1 flagged. This is normally
   small enough to fold into the same close — don't let the file blow the cap
   before acting on the warning.

5. **Verify.** Run `horus close --check` — it must pass. One `consolidate`
   pass at most per close; don't chase every signal to zero (a duplicate title
   you've deliberately kept apart, for instance, is fine to leave).

### Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is
  unclear, leave the content and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a
  coding task.
- Bump `last_updated` in `PRD.md` frontmatter if it isn't already today.

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — the project still uses the six lanes (`project.md`,
`roadmap.md`, `features.md`, `decisions.md`, `history.md`) plus `sessions/`
and `temp/`. `horus consolidate` reports lane-routing signals for this
structure unchanged from before.

### Two jobs — do not conflate them

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

### The dashboard contract — keep these current at EVERY close

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

### Steps

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

   - **Record fresh context.** Decisions, lessons/dead-ends, and capabilities shipped
     *this session* that aren't on disk yet. A decision splits in two: the **rule**
     (concise, under its topic) goes in `decisions.md`, dropping any rule it supersedes;
     the ***why*** and dead ends go in `history.md` ("Decision rationale"). Capabilities
     → a Shipped row in `features.md`. This is the content only you can supply — it's in
     the conversation, not the files.
   - **Update the dashboard contract** (the checklist above): refresh `current_focus`,
     `next_action`, `next_prompt`, the roadmap checkboxes for what you did, and bump
     `last_updated` on touched lanes. Author the next step for a *cold* reader — name
     it, point at `.horus/`.
   - **Recommend the execution mode for the NEXT.** Apply `execution-decision`'s
     need-first rubric: set `execution_recommendation:
     "continue-as-is — <why>"` for small, ambiguous/exploratory, debugging, or
     mostly-continuity work; set `"plan-execution — <why>"` for high-volume,
     low-ambiguity work with a clear gate (and create/update `execution.md` before
     implementation starts). The `<why>` must name the concrete dividend on this
     runtime — context avoided, useful parallelism, or lower-tier savings — and show
     that it exceeds the fixed supervisor tax. Cross-project scope, multiple phases,
     and calibration goals are not dividends by themselves. Do not sell supervisor
     review as the safeguard (reproduce the gate / bound checkpoints / safety-in-code
     are the durable ones).
   - **When a worker handoff exists** in `.horus/temp/`, use it as evidence, not as
     truth: the supervisor reviews the diff/tests, then distills accepted facts into
     durable lanes and updates `execution.md`.

4. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`.
   `decisions.md` is **concise current rules grouped by topic, not a dated log** — if
   it has drifted into long dated entries, collapse superseded ones to the rule that
   won and move the rationale to `history.md` (backlog pass, Step 5). Keep `roadmap.md`
   on top/open action points; condense long completed lists. If `history.md` has grown
   into a verbatim log, that's a `horus-distill-history` job — flag it, don't fix it
   here. `execution.md` is fluid active coordination; archive or replace it when the
   roadmap item is done.

5. **Backlog consolidation — ONLY when explicitly asked.** Distill old `sessions/*.md`
   into the lanes then move them to `sessions/archive/` (local-only, excluded from the
   to-distill count — don't delete); remove stale `temp/*.md` handoff notes once
   reviewed; move historical done items into `features.md` and
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

### Boundaries

- **Never invent** status, dates, versions, or decisions. When intent is unclear,
  leave the content and flag it for the user rather than guessing.
- Edits are confined to `.horus/**`. This is continuity maintenance, not a coding task.
- Bump `last_updated` front matter on lanes you change (if it isn't already today).
