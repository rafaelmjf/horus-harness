---
status: open
priority: low
readiness: gated
readiness_reason: "Wait for the unified skill/artifact refresh brainstorm verdict before fixing this card's workflow."
tier: medium
created: 2026-07-16
last_refined: 2026-07-29
refine_passes: 3
vision_facet: "Dashboard / cockpit"
created_by: owner
type: feature
parallel: unsafe
depends-on: skill-drift-surfacing-and-refresh
surface: horus/terminal_tui.py, horus/dashboard.py, horus/upgrade.py, horus/integration.py
---

# TUI fleet artifact refresh

Turn **Horus Assets Refresh** (the TUI screen renamed from "Projection Sync" —
2026-07-29) from read-only drift visibility into an owner-confirmed, end-to-end
refresh workflow for one project or every eligible registered project. Refresh
covers the canonical Horus-managed assets projected into consumer repos — bundled
skills and the managed instruction block; it is not complete when files are merely
changed locally.

This is the **outbound** direction: Horus's own assets pushed *out* into consumer
repos as releases move them. It is deliberately named apart from the **inbound**
`Sync` action (`tui-remote-freshness-indicator` / `cockpit-sync-action`), which
fast-forwards a project's *own* checkout. "Refresh" = Horus assets outward;
"Sync" = project state inward.

## Acceptance

- Horus Assets Refresh offers both **Refresh project** and **Refresh all**. The fleet
  action first renders one dry-run plan naming every target, changed managed path,
  workflow policy, and any project that cannot safely participate, then requires
  explicit owner confirmation for that exact plan.
- Each target is fetched before evaluation. A dirty, detached, unavailable,
  unknown, ahead, or diverged checkout is never rewritten or cleaned implicitly;
  it is skipped with an actionable reason. A behind checkout must be brought to a
  positively verified current default-branch base before projection changes begin.
- Dashboard and TUI reuse one canonical per-project refresh service: resolve the
  registered repository and default branch, enforce the CLI/version floor, dry-run
  and apply `upgrade_project`, then integrate only the managed paths through the
  repository's resolved workflow policy. No second projection/updater path exists.
- Automatic integration uses a bounded branch/commit/push/PR flow. Manual policy
  returns the exact remaining commands and reports the project as pending rather
  than refreshed. No unrelated project files enter the commit.
- A project reports **refreshed** only after its change is on the remote default
  branch, required checks on the delivered commit are green, a fresh fetch confirms
  the remote contains it, and the local default checkout is clean and synchronized
  with that remote. A no-op project is complete only after the same fetch/clean/sync
  checks establish that its assets were already current.
- **Refresh all** processes independently safe targets without hiding partial
  failure, then shows a durable per-project result: refreshed, already current,
  pending PR/manual action, skipped, or failed. Rerunning is idempotent and resumes
  only incomplete targets.
- Multi-project execution never auto-stashes, force-pushes, deletes branches, merges
  around protection, or treats unknown state as permission. The existing curator
  remains available for repositories that need human cleanup or bespoke review.
- Focused service and TUI tests cover single/fleet confirmation, mixed clean/dirty
  fleets, no-op idempotence, partial failure, manual policy, and exact remote-default
  verification; a live isolated multi-repository probe proves the full push/merge/
  fetch/clean result.

## Reviews

- **2026-07-16 — Scope clarification (owner):** “Refresh all” is a first-class
  requirement. Success means the remote default branches and clean synchronized
  local defaults contain the refreshed Horus artifacts, not merely that local files
  were regenerated.
- **2026-07-29 — Rename (owner, refine pass).** The TUI screen "Projection Sync"
  is renamed **"Horus Assets Refresh"** — "projection sync" was jargon and shared
  the word "sync" with the opposite (inbound git) direction. Putting **Horus** first
  draws the ownership boundary: these are *Horus's* assets pushed outward, distinct
  from a project's own state. The paired resolution: the inbound git fast-forward is
  named **Sync** (matching the shipped `horus sync` CLI verb). This also **closes the
  "two differently-scoped refresh verbs on one surface" collision** that
  `tui-remote-freshness-indicator` flagged — there is now one "Refresh" (assets, out)
  and one "Sync" (state, in). Rename touches display labels only
  (`terminal_tui.py:1210,1343,1633,452` + a docstring); no logic change, and the gate
  on `skill-drift-surfacing-and-refresh` is unchanged.
