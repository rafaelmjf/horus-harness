---
title: "Boundary-based continuity granularity"
status: claimed
priority: now
tier: sonnet
parallel: unsafe
type: feature
surface: horus/config.py, horus/closure.py, horus/resume_preflight.py, horus/terminal_tui.py, horus/cli.py
created: 2026-07-15
created_by: owner
---

# Boundary-based continuity granularity

Make handoff-boundary continuity the default so an uninterrupted owner/agent
campaign can ship several related deliveries without rewriting PRD frontmatter
and a session note after every PR.

Keep delivery evidence and engineering safety independent from narrative
granularity: commits/branches/PRs, deterministic gates, dispatch receipts, and
commit/push checkpoints remain mandatory. Dispatch, agent/account/machine
changes, pauses, releases, and session end are real continuity boundaries.

## Acceptance

- Shared continuity choices are `handoff` (default), `delivery`, and `manual`.
- Required PR freshness accepts durable git delivery evidence in handoff/manual
  mode; delivery mode retains the per-PR canonical-continuity requirement.
- A fresh machine can detect and report product commits since the latest
  canonical continuity commit without relying on a local marker.
- Stop hooks no longer auto-harvest every commit into session notes under the
  default handoff mode; explicit/final closure still harvests in one batch.
- Resume preflight and the TUI visibly warn about pending continuity.
- TUI Defaults changes the same shared continuity setting used by CLI/hooks.
- Worker dispatch surfaces a pending-continuity warning before handing context
  away; it never silently treats stale PRD prose as complete.

## Execution

Owner-steered design inline; scoped implementation in bounded phases. Live
calibration at claim time: Opus 4.8 design tier 2/2 clean; Sonnet 5 scoped-impl
lead 27/31. No subagent handoff without explicit owner authorization.
