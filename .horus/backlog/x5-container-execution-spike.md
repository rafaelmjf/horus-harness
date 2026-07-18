---
status: open
priority: medium
created: 2026-07-18
tier: high
type: spike
parallel: safe
phase: explore
created_by: owner
branch: vision-branch-x5-safe-execution-boundaries
surface: research + disposable PoCs for rootless container, dedicated user, VM/microVM execution modes
---

# x5-container-execution-spike — decide where stronger isolation earns its integration cost

## Why

Cgroups protect host availability but not files, credentials, network, Docker, or a
same-user process deliberately launching outside its scope. The owner is adding
always-on services and Hermes bots, so Horus needs evidence on the stronger boundary
for untrusted work without blindly containerizing host-integrated development.

## Questions

- Rootless Docker/Podman versus dedicated Unix user versus VM/microVM.
- Repository mounts, per-account agent config/auth, secret mounts, UID ownership, and
  cleanup.
- Network defaults and explicit egress/localhost proxy access.
- tmux attachment/persistence and terminal geometry.
- Docker socket/Docker-in-Docker escape and projects that genuinely need containers.
- Host-level probes (systemd, desktop, browser, services) and when container mode
  cannot verify the changed surface.
- Performance/cold-start cost and cross-platform availability.
- Whether an isolated mode can stay a launch property rather than becoming a Horus
  execution/orchestration runtime.

## Acceptance

- At least one disposable PoC per viable boundary runs a real bounded coding-agent
  task and records setup/runtime/cleanup costs plus escape surface.
- The result names a tight `container`/isolated-mode contract, or a no-go with the
  missing prerequisite.
- It identifies which workloads remain `contained-host` by necessity and which must
  use stronger isolation.
- No production runtime or user-global credential migration ships from this spike.

## Non-goals

- No distributed execution plane.
- No promise of identical containers on all three OSes.
- No weakening of cgroup/service containment while the spike runs.
