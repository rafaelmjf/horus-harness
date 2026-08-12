---
status: shipped
priority: medium
created: 2026-07-29
created_by: owner
readiness: ready
autonomy: attended
order: 15
topic: dashboard-cockpit
type: spike
tier: medium
parallel: safe
surface: throwaway herdr install; findings land in this card's Reviews (no product code)
shipped_pr: 440
shipped_sha: 3d594a0
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

- ~~Whether a `no` on question 1 kills the herdr host entirely~~ — **settled 2026-07-29:
  Q1 is yes.** A herdr host is viable for every surface, including the dashboard and
  scheduled workers, provided Horus supervises `herdr server` itself.

## Source

Owner session, 2026-07-29. Blocks `session-host-protocol`. Sibling:
`session-agent-state-awareness` (the feature herdr would supply for free, and which is
worth building on tmux regardless).

## Reviews

- **2026-07-29 — PROBE RUN, all four questions answered. Verdict: a herdr host is
  viable on every surface; the one hard limit is reaping.** herdr **v0.7.5**, prebuilt
  `herdr-linux-x86_64` release binary (21 MB, static-pie — no install script, nothing
  written under the real `$HOME`; verified `~/.config/herdr` and `~/.local/state/herdr`
  still absent afterwards, and the real tmux server kept all its sessions). Probe ran
  with a private `XDG_CONFIG_HOME`/`HOME` and was fully torn down (`herdr server stop`,
  no leftover processes).

  **Q1 — headless creation: YES, with one obligation.** `herdr server` runs detached with
  no TTY and no client. Against it:
  `herdr workspace create --cwd <dir> --label horus-<id> --env KEY=VAL` returns JSON with
  `workspace_id`/`tab_id`/`pane_id` (`w1:p1`) and honours `--cwd`. **But the CLI does NOT
  autostart the server** — with none running, `workspace create` fails
  `Os { code: 2, NotFound }`. So a herdr host must start and supervise `herdr server`
  itself (a `horus`-managed unit or a start-if-absent preflight), which tmux gives for
  free. Panes survived both PTY clients being killed, confirming the server/client split.

  **Q2 — kill: YES. Liveness: PARTIAL, and it fails the reaping test.**
  `herdr pane close <pane_id>` works and **kills the running process** (probed: pid alive
  before → dead after, pane gone from `pane list`).
  `herdr pane process-info --pane <id>` is *better* than tmux for confirming a runner:
  it returns `foreground_processes[].{pid, argv, cmdline, cwd}` plus `shell_pid`.
  **But there is no attached flag and no activity clock anywhere** — not in
  `api snapshot` (only `agents`/`panes`/`tabs`/`workspaces`/`focused_*`), and confirmed
  against the full bundled schema (`herdr api schema --json`, 248 KB: no `attached`,
  no `activity`, no `idle_since`/timestamp field on a pane). Horus's reaping invariant
  needs four conditions; herdr can answer 1–2 (Horus's own registry + that pid) but **not
  3 (not attached) or 4 (idle past a grace window)**. So exactly as this card predicted:
  **a herdr host declares `liveness=False` and its panes are never reaped.** Leaking an
  idle pane is cheap; killing a live agent is not.

  **Q3 — viewer under a bare PTY: YES.** Both `herdr session attach <name>` and a bare
  `herdr` client, spawned via `pty.openpty()` + `Popen` with `TERM` set, stayed alive and
  emitted alt-screen + mouse-tracking sequences (`\x1b[?1049h`, `\x1b[?1006h`) — streamable
  to xterm.js exactly like the tmux viewer. **Shape caveat:** it attaches the whole
  *session UI* (sidebar + tabs + panes), not one pane. With tmux, Horus creates one session
  per agent so `attach -t <ref>` frames exactly one agent; herdr's unit is a session
  containing many panes, so a browser tab would show herdr's entire interface unless
  `herdr agent attach <target>` narrows it (untested — needs a detected agent pane).

  **Q4 — state: the enum is real and richer than expected, but it is a maintained
  screen-scrape.** `AgentStatus` = **`idle` · `working` · `blocked` · `done` · `unknown`**
  (from the schema), and `herdr agent wait <target> --until <status> --timeout <ms>` waits
  on it — directly useful for supervising a worker. Detection is a **versioned per-agent
  TOML manifest fetched from the network** (`herdr server agent-manifests` listed 20 agents;
  claude `2026.07.13.1`, codex `2026.07.18.1`, and it auto-fetched on first run). Reading
  the shipped `claude.toml`: prioritised region-scoped rules — `working` from a braille
  spinner in the OSC title, `blocked` from `after_last_horizontal_rule` containing
  "enter to select" + "esc to cancel" plus a navigation hint, `idle` from `^\s*❯` in
  `prompt_box_body`. Strict, as advertised — and **coupled to Claude's exact UI wording,
  which is why it needs a remotely-updated manifest.**

  **What this means for the two dependent cards.**
  - `session-host-protocol` is **unblocked**. Capabilities for the herdr host:
    `persistent=True`, `attach=True`, `viewer_argv=True`, `state=True`,
    **`liveness=False`**, plus a new obligation the tmux host doesn't have —
    *ensure the server is running*. Two protocol shapes need adjusting from what that
    card assumed: (a) `pane run` **types the command into the pane's shell** rather than
    exec'ing an argv (probed: `sh -c 'echo X; sleep 300'` lost its quoting and ran as two
    commands), so the `pane_runner` is a child of a shell, not the pane's root process,
    and **there is no exit-code observation** the way tmux's `new-session <cmd>` + `wait`
    gives — the runner must report its own outcome (it already does, via the registry);
    (b) a herdr **socket path is derived from its config dir**, and a long path exceeds
    `sun_path` (hit immediately: the scratchpad path failed with *"local socket name
    length exceeds capacity of sun_path"*). Horus gives every account an isolated config
    dir, so a herdr host must keep those paths short — a real constraint, not a detail.
  - `session-agent-state-awareness`: the probe **changes the recommendation**. herdr's own
    approach shows the true cost of mechanism (1) — a screen-scraper is not a one-off, it
    is a versioned manifest per agent, remotely updated, because it tracks another
    product's UI strings. Horus should not take on that treadmill. Prefer **(2) agent
    lifecycle hooks** (`native_hooks.py` already exists) as the authoritative source, and
    **(3) host-supplied state** where the host already pays that cost. Note `herdr pane
    report-agent` accepts *pushed* state, so Claude hooks could drive herdr's sidebar too.
