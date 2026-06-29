# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

- `project.md` — what this project is, current focus, shape, boundaries (overview + vision).
- `roadmap.md` — open **action points** (any type: feature work, bug fix, chore),
  pruned when done. The *what's next*, not a completed log.
- `features.md` — the **capability ledger**: complete packages tracked
  shipped / in-progress / planned. A capability, not a task — distinct from roadmap.
- `decisions.md` — durable decisions / rules to follow and their reasoning, dated.
- `history.md` — curated bumps in the road: problems that bit us and the lessons
  that shaped the design. Relevant context, **not** a timeline and **not** open issues.
- `execution.md` — optional active execution plan for the current roadmap item:
  phase breakdown, model-tier routing, worker handoff notes, and review gates.
- `sessions/` — local session summaries (gitignored; per-machine context that
  distills into the files above).
- `temp/` — gitignored scratch notes from implementation workers/subagents. These
  are fleeting handoffs for the supervisor, not durable project memory.

**This is the single concise source of "what is this, and what's next."** If the
project already has rich docs (README, a status/roadmap file, and anything they
point to), distill the essentials here and treat those as the source — do not
maintain two hand-written roadmaps that will drift. Mark a superseded doc as such
once its content lives here.

Keep each lane in its lane; run `horus consolidate` to route facts to the right
file, prune what's done, and distill session summaries upward.

When the roadmap recommends `plan-execution`, run `horus execution prompt
--target claude|codex` for the supervisor frame and `horus execution handoff
<phase>` to create the local worker note in `temp/`.

Durable state (`project.md` / `roadmap.md` / `features.md` / `decisions.md` /
`history.md` / `execution.md`) is committed and travels via git; session summaries
and temp worker notes stay local per machine.

These files are scaffolded by `horus init` and maintained by the agents working in
this repo. A future `horus infer` will populate them automatically (LLM-based).
