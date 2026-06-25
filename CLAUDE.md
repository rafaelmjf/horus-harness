# Claude Code Instructions

<!-- HORUS:BEGIN shared-instructions -->
## Horus Project Continuity

This repository uses `.horus/` for project continuity.

**You — the agent in this session — maintain the `.horus/` lanes, filling them from the
context you hold in this conversation.** The `horus` CLI only scaffolds templates and
emits deterministic signals/checks; it never parses files to write lane content for you,
because it cannot see this session. Update the lanes by invoking the **`horus-consolidate`**
skill (it can see this conversation) and writing in what actually happened — decisions and
why, what shipped, dead ends, the next step.

Before substantial work, read the `.horus/` lanes (each stays in its lane):

- `project.md` — vision, shape, boundaries, current focus.
- `roadmap.md` — open action points (the *what's next*).
- `features.md` — capability ledger (shipped / in-progress / planned packages).
- `decisions.md` — durable rules and their reasoning.
- `history.md` — carried-forward lessons ("bumps in the road").
- Review recent local session summaries in `.horus/sessions/` when available.

After work that contributes to the project state, close the session by invoking the
`horus-consolidate` skill and folding in this session's context:

- Add a concise session summary under `.horus/sessions/` (scaffold with
  `horus session new "<title>"`, then write what actually happened — not just a date).
- Keep facts in their lane: open action points in `roadmap.md`, shipped/planned
  capabilities in `features.md`, durable rules in `decisions.md`, lessons in
  `history.md`. Don't maintain the same fact in two files.
- `horus consolidate` / `horus close` are signal + verification only — you supply the
  content from the session; they never rewrite the lanes for you.
- Do not store secrets or full transcripts in `.horus/`.

Instruction synchronization:

- Keep this shared Horus-managed block aligned with the matching block in `AGENTS.md`.
- Agent-specific instructions may live outside the Horus-managed block.
<!-- HORUS:END shared-instructions -->

## Claude Notes

- Prefer planning before larger edits.
- Keep the project lightweight and shaped around current user needs.

