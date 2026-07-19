---
status: open
priority: medium
readiness: deferred
readiness_reason: "Deferred with the X5 branch pending the owner preserve/narrow/split/drop review."
created: 2026-07-18
last_refined: 2026-07-19
tier: high
type: feature
parallel: safe
phase: explore
created_by: owner
branch: vision-branch-x5-safe-execution-boundaries
surface: cross-platform execution-environment contract; Linux systemd/cgroup v2, Windows Job Objects/sandbox options, macOS launchd/seatbelt/container options
---

# x5-cross-platform-containment-contract — honest safety guarantees on Linux, Windows, and macOS

## Why

The immediate incident and strongest native primitive are Linux-specific. Horus ships
on three OSes, so “contained” cannot mean cgroup on one machine and a warning elsewhere.
The product needs a common vocabulary with explicit platform-specific guarantees and
gaps, not false parity.

## Research/design

- Linux: cgroup v2, systemd scopes/slices, systemd-oomd, service hardening, rootless
  containers.
- Windows: Job Objects for CPU/memory/process trees; restricted token/AppContainer,
  Windows Sandbox/containers, terminal/session integration, service equivalents.
- macOS: launchd resource controls, `sandbox-exec`/seatbelt realities, process groups,
  containers/VMs, Terminal/tmux integration.
- Common dimensions: memory, swap, CPU, PIDs, I/O, filesystem, credentials, network,
  privilege/escape, persistence, observability, and termination reason.
- Capability probing and launch refusal/degradation behavior.

## Acceptance

- One execution-environment schema describes guarantees dimension-by-dimension rather
  than a single protected boolean.
- Each OS has a tested minimum availability-containment implementation plan and a
  named stronger-isolation option or explicit unsupported gap.
- CLI/TUI/doctor render the actual platform guarantee and owner override consistently.
- Cross-OS CI covers pure policy/command generation; live disposable probes cover the
  native primitive on each available OS before claiming support.

## Non-goals

- No identical implementation or security strength across OSes.
- No promise of full container/VM isolation in this design card.
- No regression of today's three-OS launch compatibility while a platform is pending.
