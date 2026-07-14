---
status: retired
priority: later
tier: sonnet
created: 2026-07-10
---
> Retired 2026-07-14 (owner triage): the draft spike was closed, no graph/vault pull
> emerged, and the generated capabilities JSON plus TUI now covers the useful
> discovery path without another read-model surface. Re-open only on observed demand.

# Productionize `horus wiki` (fleet-memory read-model)

Spike landed as **draft PR #138** (`horus/wiki.py` + `wiki` subcommand): a read-only
Obsidian-vault projection of every registered project's `.horus/PRD.md` continuity —
index + one note per project, `[[wikilinks]]` for cross-project edges. Held invariants:
read-only over sources, idempotent (no timestamps), no fetching, self-contained, banner
on every note. Fleet memory stays git-backed — this is a **derived read-model, never a
second store**; do not add any writable/external (Drive) sync.

Decide-then-build once the spike is reviewed:

- **Richer graph:** promote feature/rule *entities* to their own graph nodes (currently
  edges are project↔project only; features/rules render as sections inside a project
  note). A real cross-project link index would let a feature in one project link a rule
  in another.
- **Stale-note pruning:** de-registered projects leave an orphan note in the vault; a
  regenerate could clear the `projects/` set it owns (guard against a mis-pointed
  `--out`).
- **Off-machine read access (read-only only):** publishing the generated vault read-only
  is compatible with "no second source of truth" *as long as* it's regenerated from git
  and never edited back. Design this alongside the remote-freshness item — do NOT let it
  become a writable second store.
- **Surface:** on-demand CLI is enough for the spike; consider a dashboard "Generate
  wiki" action and/or a checkpoint/close hook only if there's an observed pull for it
  (ladder rule — instruction/CLI first).
