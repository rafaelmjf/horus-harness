---
status: open
priority: high
tier: opus
created: 2026-07-14
type: bug
parallel: exclusive
surface: horus/cli.py, horus/registry.py, horus/launch.py, horus/dashboard.py
---

# Reap process-tree orphans after failed runs, with positive confirmation

> Prioritized 2026-07-14 (owner triage): two real incidents make this the highest-value
> reliability feature after the bounded correctness batch. It needs an Opus design
> pass before Sonnet implementation because cross-platform process ownership and kill
> safety are ambiguous; do not generalize the tmux reaper blindly.

Dead workers have left children holding ports: a ghost probe server on 8899 corrupted
a supervisor probe (2026-07-04), and a setsid-detached dashboard orphan served the
hosted app for seven hours while systemd reported it dead (2026-07-12). The hosted
deploy version check caught the latter; the runtime did not.

## Required design boundary

- Distinct from the shipped tmux orphan reaper. Walk the failed run's process tree
  cross-platform using registry ownership/pid evidence.
- Put safety in code: act only on positive ownership + terminal failure confirmation;
  absence of a registry record is never permission to kill.
- At minimum, surface “tracked pid still has children” in `horus tail` and the
  dashboard before enabling termination.
- Define Linux/macOS process-group behavior and native Windows process-tree behavior,
  including PID reuse and already-exited races, before implementation.

## Verification

Design a deterministic fake-process-tree gate plus isolated live probes. Prove owned
failed trees are reaped, unrelated processes and missing-record trees survive, and
report-only fallback works where safe termination cannot be established.
