---
status: open
priority: medium
created: 2026-07-29
created_by: owner
readiness: ready
autonomy: attended
order: 15
phase: explore
type: spike
tier: medium
parallel: safe
vision_facet: "Dashboard / cockpit"
surface: throwaway herdr install; findings land in this card's Reviews (no product code)
---

# herdr-host-probe — answer three questions before designing the host protocol

## Why — owner, 2026-07-29

The owner wants Horus launchable in tmux, a plain terminal, **or** [herdr](https://herdr.dev)
— a Rust/ratatui terminal multiplexer with a headless server, a thin client, and (the
feature with real pull) per-pane **agent state awareness**: `working` / `idle` / `blocked`
in a sidebar.

A `SessionHost` protocol designed against a single implementation reliably ends up
shaped like that implementation. Spending this probe as an **input** to the protocol
design is strictly cheaper than spending it as validation afterward and reopening the
interface. Hence: probe first, design second. herdr is **not installed** on this
machine — every claim below comes from its docs and is unverified.

## What herdr appears to offer (docs, 2026-07-29 — unverified)

```
create   herdr workspace create --cwd <project> --label horus-<id12>
         herdr pane run <target> "python -m horus.pane_runner <session_id>"
attach   herdr agent attach <agent>
state    herdr agent explain <target> --json     → working/idle/blocked
wait     herdr wait agent-status <target> --status done
read     herdr pane read <target> --source recent-unwrapped
fidelity herdr integration install <agent>   (lifecycle hooks > screen matching)
```

State detection is hierarchical: lifecycle hooks when installed, otherwise screen-manifest
matching against the pane buffer. Docs note "blocked detection is deliberately strict"
(only visible approval/permission prompts). `herdr pane report-agent` lets an external
tool *push* state in.

Encouraging structural fact: `tmux_runner.py` is **already host-agnostic** — it is just
"the command the pane runs", and it owns the registry PID handoff, status transitions,
and the `horus run` worker path. Any host that can run a command in a persistent pane
inherits all of that unchanged.

## The three questions

1. **Headless creation.** Does `herdr workspace create` work with no client attached, and
   does the CLI autostart the server? Horus creates sessions from the dashboard and from
   systemd timers with no TTY. *If no:* herdr cannot host web-requested or scheduled
   workers, and the host must declare that.
2. **Kill + liveness.** What is the real close/kill verb (the docs CLI page shows
   create/run/read but no close; the README mentions `herdr pane close`), and can herdr
   enumerate live panes with an attached flag and an idle clock — the equivalent of
   `tmux list-sessions -F '#{session_attached}\t#{session_activity}'`? *If no:* the host
   declares `liveness=False` and its sessions are **never reaped**, which is the correct
   failure mode (leaking an idle pane is cheap; killing a live agent is not).
3. **Viewer under a bare PTY.** Is there something that behaves like
   `tmux attach-session -t <ref>` when spawned into a PTY that has no terminal of its own?
   This is what `pty_host.py:209` needs for the browser terminal and
   `terminal_sessions.py:369` for native windows. *If no:* herdr is a desktop-only host,
   the hosted dashboard and Termius phone path stay tmux-only, and that becomes an
   explicit declared capability rather than a surprise.

## Acceptance

- Each of the three questions answered **yes/no with the exact command and its observed
  output**, recorded in this card's `## Reviews`. No product code is written.
- A fourth answer, opportunistic: does `agent explain --json` give state good enough to
  feed a Sessions-view sidebar, and what does it report for a Claude Code pane sitting on
  a permission prompt?
- Probe hygiene: throwaway install, no change to any Horus default, nothing left running.
  herdr runs its own server — confirm it does not touch the tmux server, and do not run
  the probe against real Horus sessions.

## Open decisions

- Whether a `no` on question 1 kills the herdr host entirely or just narrows it to
  attended desktop launches. [session] — depends on what the probe finds.

## Source

Owner session, 2026-07-29. Blocks `session-host-protocol`. Sibling:
`session-agent-state-awareness` (the feature herdr would supply for free, and which is
worth building on tmux regardless).
