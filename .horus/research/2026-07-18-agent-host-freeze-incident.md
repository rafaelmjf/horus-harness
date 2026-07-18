# Agent host-freeze incident — 2026-07-18

## Summary

During the first sustained GPT-in-Claude-Code session, a read-only diagnostic process
created severe host memory pressure. GNOME became unusable: commands stopped
responding, pointer movement was delayed, clicks failed, and input events were lost.
The owner switched to tty3 and recovered the graphical session with
`sudo systemctl restart gdm`. The Horus-managed tmux session, Claude process, and
CLIProxyAPI proxy survived and were reattached through `horus tui`.

**High-confidence trigger:** an unsafe binary self-scan executed through Claude Code's
shell `grep` wrapper. Exact peak RSS is unavailable after process exit, so this is an
evidence-based attribution rather than a measured heap profile.

## Timeline (local time)

- **19:07–19:09 approximately:** a wide-regex binary probe ran for its 120-second
  timeout against the Claude executable.
- **19:09:09:** the background task output file was finalized; the probe was stopped.
- **19:10:29:** first `systemd-resolved: Under memory pressure, flushing caches`.
- **19:10–19:20+:** repeated journald/resolved pressure flushes; DNS, Tailscale,
  Cloudflare, Telegram, and RustDesk operations timed out or overran.
- **19:13 onward:** snapd watchdog fired and repeated restart attempts timed out.
- **19:22–19:24:** Xorg reported the system too slow, delayed touchpad timers, lost
  input (`SYN_DROPPED`), then an AMDGPU page-flip warning during the VT switch.
- **19:25:** owner reached tty3 (one failed login attempt was recorded).
- **19:32:43:** owner ran `systemctl restart gdm` from tty3.
- **19:33:25:** old Xorg reported `Server terminated successfully` and GDM restarted.
- **After restart:** `horus tui` rediscovered the still-running session and attached.

No memory-pressure/system-too-slow/OOM signal was present in the preceding 40-minute
journal window. The first pressure signal followed the probe by 80 seconds.

## Trigger mechanics

The shell's `grep` is a function supplied by Claude Code. For ordinary arguments it
re-executes the Claude executable with `ARGV0=ugrep`. The target was that same
**265,210,864-byte** executable, and the expression requested broad text around a
match. This creates a pathological self-scan risk unlike a bounded fixed-string tool.
The process produced no useful output before timeout.

The immediate command was the trigger; the product-design failure is absence of a
containment boundary. A normal Horus-launched agent child could pressure the entire
graphical user session. A prose warning would not prevent the class.

## Pressure and recovery evidence

- No kernel or cgroup OOM kill: `oom=0`, `oom_kill=0`.
- The machine had swap and entered prolonged reclaim/thrashing instead of killing the
  offender early.
- Current cgroup v2/systemd-oomd support is present, but all Horus services reported:
  `MemoryHigh=infinity`, `MemoryMax=infinity`, `MemorySwapMax=infinity`,
  `CPUQuota=infinity`, and large default `TasksMax`.
- The proxy Docker container had no memory/swap/CPU/PID limit, no `no-new-privileges`,
  and no capability drop.

## Horus/proxy non-causality evidence

Steady-state samples after recovery:

| Component | RSS / memory | CPU sample |
|---|---:|---:|
| CLIProxyAPI | ~68 MiB | 0% |
| Horus TUI | ~41 MiB | 0% |
| keep-warm personal | ~17 MiB idle | 0% |
| keep-warm work | ~20 MiB idle | 0% |
| notify listener | ~24 MiB | negligible |
| active Claude Code | ~393 MiB | ~33% of one CPU while responding |

CLIProxyAPI accumulated about 60 seconds CPU over roughly 2.5 hours. In the actual
freeze window it handled **two** model requests, both successful HTTP 200 responses.
Keep-warm services had no launch/journal activity near the incident. Their historical
short-lived Claude child peaks (~379 MiB and ~207 MiB) did not overlap the freeze.

The proxy cgroup reported ~7.5 GB cumulative block reads over the run (~0.8 MB/s,
~14 IOPS average), but live `vmstat` showed no I/O wait and the proxy was idle during
pressure onset. This is worth observing, not evidence of causation.

## What the incident proved

1. Horus-managed tmux persistence works across a complete graphical-session restart.
2. Current agent/service execution is not availability-isolated from GNOME.
3. Resource containment and filesystem/network isolation are different guarantees.
4. Network-facing bots need a stronger boundary than trusted host-integrated
   development sessions.
5. The model-benefit question is separate: evaluate GPT Sol only after the host cannot
   be taken down by one child process.

## Durable follow-up

The safety control belongs in [[vision-branch-x5-safe-execution-boundaries]] and its
children, especially [[x5-linux-agent-cgroup-containment]] and
[[x5-persistent-service-resource-envelopes]]. This receipt is evidence, not the guard.
