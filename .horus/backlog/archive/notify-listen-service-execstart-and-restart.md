---
status: shipped
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: bug
parallel: safe
created_by: agent
surface: horus/schedule.py (_absolute_exec + restart_listen_service + unbuffered unit), horus/cli.py (`notify listen --restart`), scripts/deploy-hosted.sh
shipped_pr: 322
shipped_sha: 1b2ed2d0c8a8c5c7ad61605a0d163d7f09e068da
---

# notify-listen --service: absolute ExecStart + restart-on-upgrade

**Why (found live 2026-07-18):** `horus notify listen --service` (shipped v0.0.62,
#317) **crash-looped `203/EXEC`** on this machine. systemd resolves a bare
`ExecStart` command name against the service manager's own compiled-in PATH
(system bin dirs only), NOT the unit's `Environment=PATH` — so
`ExecStart=horus notify listen` never resolves where `horus` lives in
`~/.local/bin` (the normal `uv tool install` location). The unit tests stub
`_systemctl` and never exec the unit, so it escaped; the install/stop "live probe"
accepted `activating` without confirming the service reached `active`.

Separately, the persistent listener runs the pinned `~/.local/bin/horus`, so a
`uv tool install --force --refresh` (or `deploy-hosted.sh`) leaves it on the OLD
code until restarted — and `deploy-hosted.sh` restarted only the dashboard.

## Fix

- `schedule._absolute_exec` resolves the executable to an absolute path via
  `shutil.which`; `install_listen_service` bakes it into `ExecStart` (fallback to
  the bare name only when unresolvable).
- Unit gains `Environment=PYTHONUNBUFFERED=1` so the poller's status/errors reach
  the journal live (24/7 service, debugged remotely).
- `schedule.restart_listen_service()` + `horus notify listen --restart` re-adopt an
  upgraded pinned CLI; `deploy-hosted.sh` restarts the `--user` listener (if
  installed) after the install, non-fatal.

## Acceptance

- The installed unit's `ExecStart` is an absolute path; the service reaches
  `active` and logs `polling as owner chat …` (NRestarts steady), never `203/EXEC`.
- `notify listen --restart` restarts an installed listener; no-op otherwise.
- `deploy-hosted.sh` restarts the listener after upgrading, without failing the deploy.

## Reviews

- **2026-07-18 — lesson:** a long-running service's live probe MUST confirm it
  reaches `active` + does its job (journal), not just that the unit installs. Added
  a test asserting `ExecStart` is absolute (the specific regression).
