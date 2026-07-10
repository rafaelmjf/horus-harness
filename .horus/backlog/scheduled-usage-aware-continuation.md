---
status: open
priority: later
tier: sonnet
created: 2026-07-10
---
# Scheduled / usage-aware autonomous continuation

Proven hand-rolled 2026-07-05: systemd timer → `horus run` ran one pinned task, closed
cleanly; preflight refused an exhausted-window spawn. Make first-class on the
survival-kit substrate: `run --stop-at-usage <pct>`, `--at <time>` /
`--after-usage-reset` (defer via `resets_at`), `--resume-plan` (cold session =
`horus resume` + pinned-task → hold-merge → close), unattended posture,
registry/dashboard record of run + PR. Local scheduling required; continuity must pin a
*specific* task. Full learnings: the 2026-07-05 session note.
