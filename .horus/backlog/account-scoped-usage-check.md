---
status: open
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
- Tests cover Claude and Codex mappings plus incomplete/native-lifted telemetry.

## Execution

Scoped implementation with a deterministic CLI test gate. It is valuable before the
next dispatch-heavy campaign, but the current campaign can use an explicit environment
override plus owner-provided readings, so it does not block project migration.
