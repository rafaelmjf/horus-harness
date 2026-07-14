---
status: retired
priority: deferred
tier: sonnet
type: feature
created: 2026-07-10
archived: 2026-07-15
---
> Archived 2026-07-15 after the fleet projection-sync delivery. The TUI now
> compares each project's Claude and Codex projections independently with the
> installed CLI, and the existing upgrade report names stale instructions,
> skills, and hooks. That covers the useful compatibility question without a
> second Doctor policy surface. Reopen only for an observed cross-agent load
> mismatch that these canonical projection reports cannot explain.

# Doctor compatibility report (retired)

The original branch→PR policy and merge closure gate shipped in managed block
v7. The remaining read-only compatibility idea is now superseded by Projection
Sync plus `horus upgrade-project` dry-run output. Per-project policy overrides or
new CI rungs still require field evidence before becoming backlog work.
