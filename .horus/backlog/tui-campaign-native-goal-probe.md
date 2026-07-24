---
status: open
priority: medium
created: 2026-07-24
created_by: owner
readiness: deferred
readiness_reason: "Live Codex 0.144.6 proved native goal RPCs exist, but using them from Horus Campaign requires the still-experimental app-server/remote-TUI host surface. Reactivate when Codex exposes a stable spawn-time goal setter or promotes that launch contract."
phase: explore
type: spike
vision_facet: "Dashboard / cockpit"
---

# tui-campaign-native-goal-probe — make Campaign a persistent native goal, not an ordinary prompt

## Why

Horus's TUI already has the right owner-facing abstraction: **Campaign** asks
what outcome should become true and which projects it covers, then launches a
normal attended agent session with that bounded brief. Codex now has stable
persisted goals and automatic continuation, but Horus hands Campaign to Codex
as an ordinary positional first prompt. The owner must still type `/goal`
manually to turn that outcome into native completion criteria.

The spirit was to adopt the native capability through the smallest supported
seam — not to build a Horus goal engine, inject terminal keystrokes, or move
orchestration into the continuity layer.

## Live findings — 2026-07-24

Probed against installed `codex-cli 0.144.6` without launching another model:

- `codex features list` reports `goals` as **stable** and enabled.
- Official Goal-mode guidance exposes `/goal` in an interactive CLI session;
  the goal becomes the first prompt plus completion criteria and keeps the
  existing sandbox/approval policy.
- `codex --help` and `codex resume --help` expose no `--goal` or other
  spawn-time goal setter.
- The officially documented version-matched schema generator, run **without**
  experimental API opt-in, includes `thread/goal/set`, `thread/goal/get`, and
  `thread/goal/clear`. `ThreadGoalSetParams` accepts `threadId`, `objective`,
  `status`, and an optional token budget.
- An isolated stdio app-server probe initialized a thread, set an active goal,
  and read it back with zero model tokens and no turn:

  ```text
  objective: Probe native goal persistence without starting a model turn.
  status: active
  tokensUsed: 0
  ```

The seam is real, but it is not available to Horus's current direct Codex TUI
launch. Horus would have to own an app-server lifecycle, create the thread,
set its goal over JSON-RPC, and attach the interactive TUI through
`codex --remote … resume <thread-id>`. The `codex app-server` command and schema
generation surface are still labelled **experimental**, and the official
documentation says the local app-server command is primarily for development
and debugging and may change without notice.

Sources: [Long-running work](https://learn.chatgpt.com/docs/long-running-work.md),
[Codex app-server](https://learn.chatgpt.com/docs/app-server.md), the installed
CLI help/schema, `horus/routines.py::campaign_prompt`, and
`horus/terminal_tui.py::_run_campaign_prompt`.

## Verdict

**Defer / no build on the current upstream surface.**

Do not move the otherwise-thin Campaign launch onto an experimental daemon and
remote-client lifecycle merely to pre-set the same goal the owner can establish
with one native `/goal` command. Manual `/goal` remains the cheaper, more native
path for the first `intent-preserving-goal-campaign` experiment.

Reactivate when either:

1. Codex exposes a stable `--goal`/spawn-time goal option for the interactive
   CLI; or
2. app-server plus remote-TUI attachment becomes a stable supported launch
   contract suitable for third-party clients.

At that point, re-probe the live schema and add the smallest capability-gated
adapter path; Claude and other adapters may ignore the request until they expose
an equivalent native capability.

## Non-goals

- No Horus-owned goal persistence, continuation, or completion engine.
- No pseudo-typing `/goal` into a PTY.
- No nested model run to test the transport.
- No new session mode or change to fresh/resume/card launch context.
- No app-server daemon adoption while its host contract remains experimental.
- No artificial cross-provider parity.

## Source

Owner-approved `wildcard` proposal and bounded Goal-mode probe, 2026-07-24.
Related: `intent-preserving-goal-campaign`, `session-process-cadence`,
`fresh-vs-resume-context-split`.
