---
status: open
priority: high
tier: sonnet
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/backlog.py, horus/infer.py, horus/init templates, PRD skeleton
shipped: "2026-07-12 — capability built, PR open (branch feat/unify-backlog-cards). horus init/infer scaffold .horus/backlog/ + starter card; prd_md()'s ## Backlog is now a thin pointer (templates.backlog_pointer_block); new `horus backlog migrate` (idempotent, per-project, no --all) converts inline PRD Backlog items to cards, preserving item text byte-stably and folding unconverted prose into a 'Migrated notes' block rather than dropping it; Card.type field (default task) + `backlog list --type`. 1154 tests green. Per-project harmonization (horus-hub, agentic-ttrpg, agentic-travel-guide, fabric, agentic-gym-coach) is a follow-up run of the shipped command, not part of this PR."
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

## Application mode (how harmonization actually happens — owner Q, 2026-07-12)

Build the capability HERE (this card, one dispatch). Then applying the migration to
each existing inline/`bugs/` project is **mechanical, not authoring** — so:
- Keep `horus backlog migrate` **per-project** (operates on + commits to ONE repo).
  Do NOT add a cockpit `--all` that writes to N repos from the overseer session — that
  re-concentrates the cross-repo writes the cockpit boundary exists to prevent.
- Because it's idempotent + deterministic, harmonizing is just *running the command*:
  the owner runs the one-liner in each project dir (zero agent overhead), OR a cheap
  mechanical worker (Haiku-tier) does it per project and commits there. NOT the cockpit
  hand-editing other projects; NOT a heavyweight full session per trivial migration.
- Projects to migrate at decision time: inline `## Backlog` → cards for horus-hub,
  agentic-ttrpg, agentic-travel-guide, fabric; `bugs/` collapse for agentic-gym-coach
  (its own cleanup card).

## Enables

`fleet-backlog-view` (a deterministic fleet-wide backlog roll-up) is clean only once
every project is on cards — this card is its prerequisite.

## Verification

`horus init`/`infer` on a fresh temp project scaffolds `backlog/`; a migration
fixture converts a known inline `## Backlog` to cards byte-stably; `backlog list
--type bug` filters. CI green.
