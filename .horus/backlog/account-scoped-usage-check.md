---
status: claimed
priority: high
tier: sonnet
created: 2026-07-15
type: feature
parallel: safe
surface: horus/cli.py, horus/claude_usage.py, horus/codex_usage.py
---

# Account-scoped usage check for safe dispatch

The dispatch contract requires checking the isolated target account before a worker
is launched, but `horus usage check` currently reads only the ambient login. During a
real cockpit campaign, checking the Claude `work` account required manually exporting
its mapped `CLAUDE_CONFIG_DIR`; the ambient result described a nearly exhausted
different account.

## Acceptance

- `horus usage check --target claude|codex --account <alias>` resolves the existing
  isolated account mapping without changing the ambient login.
- Output names the alias, telemetry source/freshness, available windows, and any
  incomplete signal; no alias, email, or usage reading is committed to a project.
- Unknown aliases fail clearly and never fall back silently to the ambient account.
- Existing no-`--account` behavior and hook behavior remain compatible.
- **Overseer==worker collision warning:** when a dispatch would route a worker to the
  same isolated account the overseer session is running under, warn explicitly (shared
  usage pool, not true isolation). Observed in the campaign: the only isolated `claude`
  alias (`work`) was also the overseer, so worker and overseer shared a rate-limit pool.
  Advisory only — it warns, it does not block or reroute.
- Tests cover Claude and Codex mappings, incomplete/native-lifted telemetry, and the
  overseer==worker collision warning.

## Execution

Scoped implementation with a deterministic CLI test gate. It is valuable before the
next dispatch-heavy campaign, but the current campaign can use an explicit environment
override plus owner-provided readings, so it does not block project migration.
