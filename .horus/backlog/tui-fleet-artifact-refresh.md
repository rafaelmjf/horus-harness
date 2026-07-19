---
status: open
priority: low
tier: medium
created: 2026-07-16
vision_facet: "Dashboard / cockpit"
created_by: owner
type: feature
parallel: unsafe
surface: horus/terminal_tui.py, horus/dashboard.py, horus/upgrade.py, horus/integration.py
---

# TUI fleet artifact refresh

Turn Projection Sync from read-only drift visibility into an owner-confirmed,
end-to-end refresh workflow for one project or every eligible registered project.
Refresh covers the canonical Horus-managed projection assets, including bundled
skills and managed instructions; it is not complete when files are merely changed
locally.

## Acceptance

- Projection Sync offers both **Refresh project** and **Refresh all**. The fleet
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
