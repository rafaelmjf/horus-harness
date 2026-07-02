# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

**Structure prototype (2026-07-03): PRD.md + sessions/.** The six-lane layout is
retired in this repo; transcript analysis showed the value lives in the resume
frontmatter + session notes, while the lane taxonomy carried the overhead.

- `PRD.md` — **the one maintained file**: vision, prioritized backlog (features and
  bugs in one list), shipped ledger (one line each), load-bearing rules.
- `sessions/` — local session summaries (gitignored; operational facts, dead ends,
  verified gates). Distilled notes move to `sessions/archive/`.
- `project.md` / `roadmap.md` — **frontmatter shims only** (current_focus,
  next_action/next_prompt) feeding the dashboard, `horus resume`, and the merge
  freshness gate until the tooling reads PRD.md directly. Content lives in PRD.md.
- `archive/` — the retired lanes (`features.md`, `decisions.md`, `history.md`,
  `execution.md`), preserved verbatim for archaeology.
- `temp/` — gitignored scratch notes from implementation workers/subagents.

If the project has rich docs (README, status files), distill essentials into PRD.md
and point at them — never maintain two hand-written roadmaps.

Closure = update PRD backlog/shipped + the two shim frontmatters + a session note,
then `horus close --commit --push`. One `horus consolidate` pass at most; do not
chase lane-routing warnings (they predate this structure).
