---
status: open
priority: high
tier: sonnet
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/backlog.py, horus/infer.py, horus/init templates, PRD skeleton
shipped:
---

# Make card-per-file backlog the fleet standard (unify inline `## Backlog` → cards)

**Owner decision (2026-07-12):** the fleet runs three different backlog structures
today and the mix is real friction (agents must handle both shapes; the overseer
goes back and forth). Unify on **card-per-file `.horus/backlog/`** as the single
standard.

Fleet inventory at decision time:
- `backlog/` cards: horus-harness, horus-agent (cockpit)
- inline `## Backlog` in PRD: horus-hub, ttrpg, travel-guide, fabric
- **BOTH `backlog/` and `bugs/`**: agentic-gym-coach (the folder split to collapse — see below)

## Scope

1. **Cards are the default structure.** `horus init` and `horus infer` scaffold
   `.horus/backlog/` (with a starter/README card), and the PRD skeleton's
   `## Backlog` becomes a thin pointer to the cards dir (as horus-agent's PRD already
   models it), not an inline list.
2. **Migration path** from inline `## Backlog` → one card per item, preserving text
   and inferring frontmatter (`status`/`priority`; default `type: task`). A
   `horus backlog migrate` (or a flag on `upgrade-project`) that is idempotent and
   read-safe. Do NOT silently drop the inline section without converting it.
3. `horus backlog list`/`claim` already work per project — confirm they operate on
   any migrated project unchanged.

## Bug typing (fold in the `bugs/`-folder decision)

**DECIDED (owner, 2026-07-12): one `backlog/` folder + a `type: bug|feature|chore|task`
frontmatter field — NOT a separate `bugs/` folder.** Rationale = agent-overhead: one
place to query, `horus backlog list --type bug` is a single deterministic filter;
visibility comes from the tooling (list groups/counts by type; dashboard shows a bug
badge), not folder separation. So: add the `type` field to the card schema + a
`--type` filter to `horus backlog list`; default missing `type` to `task`.

**Cross-project cleanup (owner ask):** any project that already has a separate `bugs/`
folder gets a cleanup card in its OWN backlog to collapse `bugs/` → `backlog/` with
`type: bug` and default to this structure. At decision time only **agentic-gym-coach**
has `bugs/`; a cleanup card was dropped there (`clean-up-bugs-folder-to-type-field`).
Re-scan the fleet when this ships in case another project grew one.

## Enables

`fleet-backlog-view` (a deterministic fleet-wide backlog roll-up) is clean only once
every project is on cards — this card is its prerequisite.

## Verification

`horus init`/`infer` on a fresh temp project scaffolds `backlog/`; a migration
fixture converts a known inline `## Backlog` to cards byte-stably; `backlog list
--type bug` filters. CI green.
