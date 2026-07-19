---
status: open
priority: high
readiness: deferred
readiness_reason: "Deferred with the X5 branch pending the owner preserve/narrow/split/drop review."
created: 2026-07-18
last_refined: 2026-07-19
tier: high
type: feature
parallel: unsafe
phase: explore
created_by: owner
branch: vision-branch-x5-safe-execution-boundaries
surface: horus/terminal_sessions.py, horus/tmux_runner.py, horus/adapters/base.py, horus/run_executor.py, horus/registry.py, new resource-control primitive
---

# x5-linux-agent-cgroup-containment — one bounded systemd scope per Horus session

## Why

A Horus-managed agent child caused system-wide memory pressure and froze GNOME.
Current tmux panes already live in systemd scopes, but those scopes have unlimited
RAM, swap, CPU, and process counts. The first hard safety rung is a named, bounded
cgroup around every attended and worker launch. Evidence:
[[2026-07-18-agent-host-freeze-incident]].

## Design questions to resolve

- Dedicated parent `horus-agents.slice` plus `horus-session-<id>.scope` per launch.
- Common wrapper used by current-TTY, tmux runner, native-window, headless adapter,
  and detached worker launch paths; descendants inherit the scope.
- Relative machine-aware defaults (`MemoryHigh`, `MemoryMax`, `MemorySwapMax`,
  `CPUQuota`, `TasksMax`) plus bounded owner overrides.
- Active `systemd-oomd`/`OOMPolicy` behavior and how a scope limit is distinguished
  from provider/tool failure.
- Scope name, effective properties, pressure counters, and termination reason stored
  in the forward-readable registry/receipt.
- Linux with a healthy user systemd manager is contained by default. Failure to create
  a required scope refuses launch; an explicit `--uncontained` escape is visible and
  never persisted silently.
- Document the boundary honestly: ordinary descendants are contained, but same-user
  access to Docker or `systemd-run` can escape without a stronger sandbox.

## Acceptance

- Every Horus launch surface places the agent and normal tool descendants in its named
  session scope under the parent slice.
- Active systemd properties are read back before reporting launch success.
- A controlled allocator exceeding the session ceiling kills/throttles only that
  scope; GNOME, proxy, TUI, and a sibling Horus session remain responsive.
- CPU and PID stress probes are likewise confined.
- Registry/CLI/TUI name `resource-limit` termination and show the effective envelope.
- tmux reattachment and graphical-session restart persistence still work.
- Unsupported/non-systemd platforms label the absence and do not claim containment.

## Non-goals

- No filesystem/network/credential sandbox; owned by later X5 cards.
- No container implementation.
- No universal hardcoded limit values before [[x5-resource-policy-calibration]].
