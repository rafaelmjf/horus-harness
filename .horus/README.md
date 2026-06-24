# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

- `project.md` — what this project is, current focus, shape, boundaries.
- `roadmap.md` — current focus + a checklist of planned / in-progress / done items.
- `decisions.md` — durable decisions and their reasoning, dated.
- `sessions/` — local session summaries (gitignored; per-machine context that
  distills into the files above).

**This is the single concise source of "what is this, and what's next."** If the
project already has rich docs (README, a status/roadmap file, and anything they
point to), distill the essentials here and treat those as the source — do not
maintain two hand-written roadmaps that will drift. Mark a superseded doc as such
once its content lives here.

Durable state (`project.md` / `roadmap.md` / `decisions.md`) is committed and
travels via git; session summaries stay local per machine.

These files are scaffolded by `horus init` and maintained by the agents working in
this repo. A future `horus infer` will populate them automatically (LLM-based).
