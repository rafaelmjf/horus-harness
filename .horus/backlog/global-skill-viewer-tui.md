---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Introspection & self-improvement"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/skills.py (installed vs available/version findings — already exists), horus/terminal_tui.py (new skills screen), horus/dashboard.py (optional parity)
---

# global-skill-viewer-tui — see installed vs available skills, per agent

**Why (owner, 2026-07-18):** there is no single place to see, across a project, which
bundled skills are installed for Claude vs Codex, which are available-but-missing, and
which are stale. `skills.skill_findings` / `missing_or_stale` already compute this (they
feed the passive `_skill_nudge` tip), but nothing renders it as a browsable view. Adds a
TUI screen that surfaces the existing detection — routing findings, not new scanning
(cf. the related bug `skill-drift-surfacing-and-refresh`).

## How

- A new TUI screen (keybind from Home, e.g. `k`) lists bundled skills grouped by agent
  (claude / codex), each row showing state: **installed (vX)** / **outdated (vX→vY)** /
  **available, not installed** / **unversioned/customized** — straight from
  `skills.skill_findings` for the current project.
- Show the one canonical refresh command per the drift-card decision (reconcile the
  `upgrade-project --apply` vs `skill install --target` ambiguity there); never
  auto-write.
- Read-only projection; it renders canonical `skills.py` results, never a second parser
  (Terminal-TUI-stays-thin rule).

## Acceptance

- The screen lists every bundled skill for both agents with its per-agent install state
  for the open project, matching `horus doctor` / the nudge.
- Customized/unversioned skills are shown as such, never silently flagged for overwrite.
- No new scanning logic; it consumes `skills.skill_findings`.

## Non-goals

- No auto-install/auto-refresh from the viewer (owner-visible step only).
- Not a fleet-wide sweep (that is `skill-drift-surfacing-and-refresh`); this is the
  per-project browsable view.
