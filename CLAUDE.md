# Claude Code Instructions

<!-- HORUS:BEGIN shared-instructions -->
## Horus Project Continuity

This repository uses `.horus/` for project continuity.

Before substantial work, read the `.horus/` lanes (each stays in its lane):

- `project.md` — vision, shape, boundaries, current focus.
- `roadmap.md` — open action points (the *what's next*).
- `features.md` — capability ledger (shipped / in-progress / planned packages).
- `decisions.md` — durable rules and their reasoning.
- `history.md` — carried-forward lessons ("bumps in the road").
- Review recent local session summaries in `.horus/sessions/` when available.

After work that contributes to the project state:

- Add a concise session summary under `.horus/sessions/`.
- Keep facts in their lane: open action points in `roadmap.md`, shipped/planned
  capabilities in `features.md`, durable rules in `decisions.md`, lessons in
  `history.md`. Don't maintain the same fact in two files.
- Run `horus consolidate` to route/prune/distill when the lanes drift.
- Do not store secrets or full transcripts in `.horus/`.

Instruction synchronization:

- Keep this shared Horus-managed block aligned with the matching block in `AGENTS.md`.
- Agent-specific instructions may live outside the Horus-managed block.
<!-- HORUS:END shared-instructions -->

## Claude Notes

- Prefer planning before larger edits.
- Keep the project lightweight and shaped around current user needs.

