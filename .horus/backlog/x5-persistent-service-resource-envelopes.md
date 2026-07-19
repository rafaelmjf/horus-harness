---
status: open
priority: high
created: 2026-07-18
last_refined: 2026-07-19
tier: high
type: feature
parallel: unsafe
phase: explore
created_by: owner
branch: vision-branch-x5-safe-execution-boundaries
surface: horus/schedule.py service unit writers, horus/proxy.py Docker command, dashboard/deploy units, doctor/control status
---

# x5-persistent-service-resource-envelopes — bound every Horus daemon and verify the live unit

## Why

The host-freeze audit found all generated Horus systemd services at infinite memory,
swap, and CPU limits, while the CLIProxyAPI Docker container had no memory/CPU/PID or
least-capability bounds. These services were not the incident trigger, but adding more
always-on bots without envelopes compounds host availability and security risk.
Evidence: [[2026-07-18-agent-host-freeze-incident]].

## Design

- Define service-class envelopes for proxy, notify listener, per-account keep-warm,
  dashboard, schedules/supervisors, and future network-facing processes.
- Generated systemd units carry machine-aware `MemoryHigh`/`MemoryMax`, swap, CPU,
  PID/task, restart/OOM policy, and pressure-management directives appropriate to the
  service.
- CLIProxyAPI `docker run` gains tested memory/swap/CPU/PID bounds plus
  `no-new-privileges`/capability reduction where compatible with OAuth refresh,
  localhost serving, and mounted auth/config writes.
- Installer success requires `systemctl show`/`docker inspect` to match the requested
  envelope and the service to reach active + perform its signal. A stale unlimited
  installed unit is drift, not success.
- Upgrades restart the pinned services so new bounds actually take effect.
- Control/doctor exposes effective limits and drift compactly; unknown never renders
  as protected.

## Acceptance

- Every installed Horus service has a bounded active cgroup/container appropriate to
  its workload and reports the exact properties.
- A service memory/CPU/PID stress fixture is contained without affecting unrelated
  services or the desktop.
- Keep-warm still completes a real account warm under its envelope; listener still
  polls; proxy serves Claude/GPT and refreshes OAuth; dashboard health remains green.
- Installer rolls back/refuses a service whose active properties or signal do not
  match, following the existing service self-verification ladder.
- Linux implementation degrades explicitly on macOS/Windows; it never writes unusable
  systemd/Docker policy there.

## Non-goals

- No agent-session cgroup (owned by [[x5-linux-agent-cgroup-containment]]).
- No complete bot credential/filesystem isolation (owned by
  [[x5-network-bot-isolation]]).
- No tuning verdict before [[x5-resource-policy-calibration]].
