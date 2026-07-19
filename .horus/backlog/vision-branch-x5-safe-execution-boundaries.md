---
status: open
priority: high
created: 2026-07-18
last_refined: 2026-07-19
tier: frontier
type: feature
parallel: safe
phase: explore
created_by: owner
surface: execution-environment contract across agent launches, system services, containers, bot runtimes, and three OSes
---

# vision-branch-x5 — safe execution boundaries and guardrails

> **Vision branch (`phase: explore`, no forced current Vision facet).** The host-freeze
> incident proved a new independent problem: Horus can persist work safely while still
> allowing one agent child to pressure the whole workstation. Explore the smallest
> deterministic execution boundary that protects availability and gives untrusted or
> network-facing work a real security boundary.

## Why

A wide binary self-scan caused prolonged memory pressure, swap/service starvation,
and a frozen GNOME session. The owner recovered through tty3; Horus tmux/Claude/proxy
survived and reattached. The command was accidental, but the design failure was no
kernel/runtime envelope around Horus-launched descendants. Evidence:
[[2026-07-18-agent-host-freeze-incident]].

This direction is separate from X4's model/harness/account plane. Any model can emit a
pathological command; model quality should be judged only after the machine is safe.

## Distinctions the branch must preserve

- **Availability containment:** RAM/swap/CPU/PID/I/O pressure cannot freeze siblings or
  GNOME.
- **Security isolation:** files, credentials, network, Docker, and privilege/escape
  paths are bounded.
- **Accidental child containment:** ordinary descendants stay in their cgroup.
- **Adversarial escape resistance:** a process cannot start work outside its boundary.
- **Host-integrated development:** real tmux/systemd/desktop probes remain possible.
- **Untrusted/bot execution:** stronger identity/container boundary is expected.

A cgroup solves the first and much of the third; it is not automatically a sandbox.

## Principles

1. Safety is enforced by kernel/runtime configuration, never an instruction line.
2. Safe-by-default; uncontained execution is a deliberate visible escape hatch.
3. Limits are measurable and tunable, not arbitrary constants fossilized in code.
4. One failed session/service cannot pressure GNOME or sibling work.
5. Platform capability is explicit; unsupported never masquerades as protected.
6. Network-facing bots receive a stronger boundary than trusted interactive work.
7. Horus remains the memory/planning plane; containment cannot grow into a general
   distributed orchestration runtime.

## Ordered children

1. [[x5-linux-agent-cgroup-containment]] — immediate Linux availability boundary.
2. [[x5-persistent-service-resource-envelopes]] — bound proxy/listener/keep-warm/
   dashboard/schedules and verify active properties.
3. [[x5-container-execution-spike]] — decide where a container/user/VM mode earns its
   integration cost.
4. [[x5-network-bot-isolation]] — stronger runtime for Telegram/Hermes/network-facing
   processes.
5. [[x5-cross-platform-containment-contract]] — honest Windows/macOS/Linux guarantees.
6. [[x5-resource-policy-calibration]] — scale and tune limits from evidence.

## Convergence criterion

Converged when: one small execution-environment contract protects host availability and gives bots/untrusted work a real isolation mode without turning Horus into an orchestration platform.

**Promote** to a Vision facet only if Horus can expose a small, understandable
execution-environment contract that protects host availability and gives bots/
untrusted work a real isolation mode across supported platforms. **Drop or split** if
this requires Horus to become an execution/orchestration platform, if limits cannot be
made predictable enough for normal agent workloads, or if containers destroy the
host integration that makes Horus useful.

## Branch acceptance

- A fresh owner can distinguish contained-host, isolated, and uncontained guarantees.
- One bounded failure cannot freeze the machine or kill sibling sessions/services.
- Every UI/CLI surface reports the actual boundary and limits, not an aspirational label.
- Cross-platform differences are named and tested; no false equivalence.
- The owner can evaluate model/harness quality independently of host-safety failures.
