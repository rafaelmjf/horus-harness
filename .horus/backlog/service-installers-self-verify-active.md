---
status: open
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: agent
surface: horus/schedule.py (install_listen_service self-verify + rollback; a shared _await_active helper), any future systemd-unit installer
---

# service-installers-self-verify-active — safety in code, not in the probe

**Why (observed field failure 2026-07-18, #322):** `horus notify listen --service`
returned SUCCESS on `enable --now`'s returncode alone, then crash-looped
`203/EXEC` — the installer never confirmed the service stayed `active`. It escaped
unit tests (they stub `_systemctl`) AND the live probe (accepted `activating`).
Per this repo's ladder (instruction → signal → gate; promote after a real
failure) and "safety in code, not the reviewer", the installer itself must verify
the running state so no model/account/probe can "install" a dead service.

## How

- After `enable --now`, poll `is-active` for a bounded window (e.g. ~10s); on
  reaching `active`, return; on timeout/`failed`, raise `ScheduleError` carrying
  the last journal lines (`journalctl --user -u … -n`), and roll back the
  half-installed unit (disable + remove) so a failed install leaves nothing armed.
- Factor a shared `_await_active(unit, timeout)` so the scheduled-dispatch path and
  any future unit installer reuse one verification, not a per-caller reinvention.

## Acceptance

- Installing a unit whose ExecStart cannot run raises with the journal tail and
  leaves NO unit behind (verified with a deliberately-broken ExecStart in an
  isolated probe).
- A good install returns only after the unit is observed `active`.
- Existing install/refuse/stop/restart tests still pass; the self-verify path has
  its own test (stubbed `is-active` returning active vs failed).

## Non-goals

- Not a general health-monitor — one-shot verification at install time only
  (Restart=always still handles later transient blips).
