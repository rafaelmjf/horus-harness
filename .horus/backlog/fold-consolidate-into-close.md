---
status: open
priority: medium
tier: sonnet
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/cli.py (close/consolidate), horus/consolidate.py
shipped:
---

# Fold consolidate's signals into `close --check`; reserve the skill for heavy passes

## Problem (observed 2026-07-12)

`horus close --check` and `horus consolidate` are **two disjoint, signal-only gates
that both fire at session close** — close checks freshness+git (lanes fresh /
uncommitted / pushed), consolidate checks PRD hygiene (size vs ~250-line cap /
duplicate titles / lingering done items / undistilled session notes). Neither writes;
the agent acts on the signals. Because they fire at the same moment but are separate
commands, it's easy to run one and skip the other — the overseer did exactly that this
session (ran `close`, skipped `consolidate`), and the PRD had crept to 247 lines
uncaught until the owner asked.

**Structural context:** consolidate's original heavy job (six-lane v2 routing —
shipped→features, distilling across six files, de-duplicating drift between
`roadmap.md`/`features.md`) mostly evaporated on the v3 single-file `PRD.md`. The
residual recurring value is essentially the **line-count guard** plus rare
dupe/done/undistilled nudges. The ceremony predates the refined structure.

## Change

- **`horus close --check` also emits consolidate's deterministic PRD-hygiene signals**
  (size vs cap, duplicate backlog titles, lingering done items, undistilled session
  notes) for v3 projects — so ONE close-time gate surfaces everything and there is no
  second command to forget.
- Keep both **signal-only** (do NOT auto-rewrite `.horus/`; the agent still edits).
- **Reserve the `horus-consolidate` skill + `horus consolidate` command** for the
  occasional HEAVY pass (bloated PRD, migration, big session backlog to distill) — it
  stays, it's just no longer the routine close-time step.

## v2 (six-lane) note

For v2 projects, consolidation is still heavier (real cross-file routing). Don't
duplicate the full six-lane routine inside `close --check`; either emit the v2
signals too or have `close --check` point v2 projects at the consolidate skill. The
fold is primarily a v3 simplification — don't regress v2.

## Verification

`close --check` on a v3 project whose PRD is >250 lines surfaces the size signal (and
a dup/done fixture surfaces those); a clean v3 project shows no hygiene warnings; v2
path unchanged. CI green.
