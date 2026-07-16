---
status: shipped
priority: high
tier: inline
created: 2026-07-16
type: bug
parallel: unsafe
surface: horus/cli.py, horus/native_hooks.py, horus/templates.py, Claude/Codex hook projections
shipped_pr: 267
shipped_sha: 14f312cd797bc4971eb5657019d13b65b9544b09
---

# Worker guard for destructive global-state cleanup

An unattended full-auto worker intended to clean an isolated probe ran
`rm -rf ~/.horus/logs/runs` without first scoping `HOME`. It deleted the real
machine-local historical run logs. Durable registry/datums/git state survived, but
review cannot undo destructive global-state commands.

## Acceptance

- In a tracked Horus worker (`HORUS_RUN_WORKER=1`), the shared shell PreToolUse guard
  denies clear destructive commands targeting user-global `.horus`, `.claude`, or
  `.codex` paths.
- The guard covers Claude Bash/PowerShell and the matching Codex hook surface.
- Normal user sessions remain unaffected, and workers can still delete explicitly
  isolated temporary paths or project-relative `.horus/temp` files.
- Read-only commands and quoted prose that merely mention protected paths are not
  blocked.
- The deny message instructs the worker to create an isolated probe home first and to
  clean only the exact directory that probe created.
- Tests reproduce the observed `rm -rf ~/.horus/logs/runs` command and representative
  POSIX/PowerShell spellings without broad shell-policy parsing.

## Boundaries

- This is a narrow last-resort guard for known global state, not a general command
  sandbox or an attempt to parse every shell language.
- Do not block project-owned `.horus/` writes or normal attended maintenance.

