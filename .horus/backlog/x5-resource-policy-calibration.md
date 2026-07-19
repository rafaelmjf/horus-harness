---
status: open
priority: low
created: 2026-07-18
last_refined: 2026-07-19
tier: medium
type: feature
parallel: safe
phase: explore
created_by: owner
branch: vision-branch-x5-safe-execution-boundaries
surface: resource policy/defaults, machine probes, doctor/control readout, measured pressure/termination datums
---

# x5-resource-policy-calibration — tune limits from machine capacity and real agent workloads

## Why

A hard boundary with arbitrary constants can kill healthy long-context sessions or be
so loose it fails to protect the desktop. Limits must scale with machine capacity,
concurrency, and workload evidence while staying understandable and owner-overridable.

## Questions

- Parent-slice budget versus per-session/service ceilings under multiple concurrent
  agents.
- Percentage versus absolute limits; minimum/maximum clamps for small and large hosts.
- `MemoryHigh` reclaim behavior, `MemoryMax` kill behavior, swap allowance, CPU quota,
  PID limits, I/O weight, and systemd-oomd policy.
- Interactive latency and false-kill cost versus desktop survival margin.
- Distinct defaults for attended agent, worker, proxy, listener, keep-warm, dashboard,
  and network bot.
- What pressure/termination measurements are useful without becoming continuous
  monitoring or an automatic router.
- Owner defaults/overrides and how doctor/Control show effective versus configured.

## Acceptance

- A reproducible workload matrix measures representative Claude/Codex/GPT sessions,
  tool fan-out, tests/builds, keep-warm, proxy, and bot services on at least the
  dogfood Linux host.
- A documented policy derives bounded defaults from RAM/CPU/concurrency with safe
  clamps and names confidence/unknowns.
- Controlled stress proves the policy preserves GNOME and sibling workloads while
  normal sessions complete.
- Overrides are validated, visible, and cannot silently disable the parent safety
  budget.
- Any observability surface remains compact and read-only; no cost/usage auto-routing.

## Non-goals

- No one-size-fits-all benchmark score.
- No continuous fleet monitoring SaaS.
- No implementation of the platform primitives themselves.
