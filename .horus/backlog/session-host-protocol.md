---
status: open
priority: medium
created: 2026-07-29
created_by: owner
readiness: gated
readiness_reason: "Blocked on herdr-host-probe: the capability set must be derived from two real hosts, not guessed from one. Design the protocol with the probe's three answers in hand."
phase: converge
type: feature
tier: high
parallel: unsafe
depends-on: herdr-host-probe
vision_facet: "Dashboard / cockpit"
surface: horus/terminal_sessions.py → horus/hosts/, horus/pty_host.py, horus/run_executor.py, horus/cli.py, horus/terminal_tui.py, horus/terminal_app.py, horus/dashboard.py, horus/config.py
---

# session-host-protocol — one pluggable session host (tmux · current · herdr)

## Why — owner, 2026-07-29

Today tmux is *the* session host and everything else is an `else` branch. The owner wants
Horus launchable in tmux, in a plain terminal (the existing Windows/no-tmux fallback), or
in herdr — which means "can this host do X" has to become a **declared capability** rather
than a string comparison against `"tmux"` scattered across six files.

The valuable half of this card is independent of herdr: it promotes the no-tmux fallback
from an `if` branch into a first-class host with honest, declared limits.

## The seam is already ~80% there

Everything outside `terminal_sessions.py` uses exactly nine verbs (call-site sweep,
2026-07-29): `default_target` · `launch_tmux`/`run_attached` (create + attend) ·
`launch_window` (create + OS-window viewer) · `launch_detached_run` (one-shot worker) ·
`attach_session` · `stop_session` · `is_attachable`/`access_label` · `reap_orphans` —
plus one that is not a function yet: **"give me the argv that attaches a viewer to this
ref"**, currently hardcoded in two places.

### The leaks to close

| Leak | Site |
|---|---|
| `launch_target == TMUX` decides attachability | `terminal_sessions.py:72` |
| `record.launch_target != "tmux"` raw string | `run_executor.py:134` |
| `default_target() == TMUX` gates the managed web launch | `pty_host.py:119` |
| hardcoded `["tmux","attach-session","-t",ref]` (browser viewer) | `pty_host.py:209` |
| same, for native windows | `terminal_sessions.py:369` |
| `choices=("current","tmux")` in argparse | `cli.py:5142`, `cli.py:5223` |
| `if default_target() != TMUX:` fallback branch | `terminal_sessions.py:336` |

### Capabilities a host declares

`persistent` (survives client detach) · `attach` · `switch` (in-place client switch — see
`tui-nested-tmux-navigation`) · `viewer_argv` · `liveness` · `mouse_setup` (tmux needs a
per-session `set-option mouse on`; herdr is mouse-native; `current` does nothing) ·
`state` (working/idle/blocked — tmux: no).

**`liveness` is the load-bearing one.** It turns the reaping rule into something
structural instead of remembered: a host that cannot answer "is this ref attached, and
how long has it been idle" declares `liveness=False` and its sessions are never reaped at
all. Today that safety lives in one careful function plus a PRD rule; three hosts is
exactly the situation where "each reaper is careful" stops holding.

### The three hosts

- **`current`** — the Windows/no-tmux path, declaring `persistent=False, attach=False,
  liveness=False`. Behavior identical to today; the difference is it stops being an
  `else`.
- **`tmux`** — everything today, plus nested `switch-client`.
- **`herdr`** — mapping in `herdr-host-probe`; capabilities set by what that probe found.

### Selection

`[terminal] host = "auto"|"tmux"|"current"|"herdr"` in config.toml, plus the existing
`HORUS_TERMINAL_TARGET` override. `auto` resolves herdr-if-configured → tmux → current.

## Acceptance

- A `SessionHost` protocol with the nine verbs and the capability flags; `horus/hosts/`
  holds `tmux.py`, `current.py` (+ the window viewer), and — if the probe cleared it —
  `herdr.py`. Every leak in the table above is gone: no caller compares a host id to a
  literal, and no caller builds a tmux argv.
- The refactor lands as a **no-behavior-change PR** first: same launches, same
  attachability labels, same reaping, same `--target` semantics, proven by the existing
  suite passing unmodified except where a test asserted a now-private detail.
- `--target tmux|current` keeps working forever for scripts, per the standing rule that
  scripted `horus open --target` behavior stays explicit and stable. New host ids are
  additive; argparse choices are built from the host registry.
- `registry.launch_target` holds the host id, and `is_attachable`/`access_label` answer
  from capabilities. A row whose host is unknown to this install degrades to
  "original terminal only" rather than offering a fake attach.
- `tmux_runner.py` → `pane_runner.py` with a `tmux_runner` shim retained: the module name
  is embedded in live runner specs and in already-running sessions, so removing it breaks
  sessions mid-flight.
- Reaping is per-host and gated on `liveness`; the tmux reaper's positive-confirmation
  invariant is preserved verbatim, not re-derived.
- Test matrix: each host × (create, attend, viewer, stop, reap, attachability label).
  Every tmux-touching test uses a private `-S` socket with inherited `TMUX` unset.
- Gate: full suite green on the exact SHA, plus live probes — a tmux launch/attach, a
  `current` launch on a no-tmux path, and one browser-terminal viewer through
  `pty_host`.

## Guardrails

- The capability flags must be the **only** switch. A caller that special-cases a host id
  defeats the point and reintroduces the leak.
- The test matrix triples here; that is the real cost of this card and the reason `tier:
  high`. Attach/viewer/reap × three hosts is where regressions will come from.
- Do not make herdr a dependency for anyone who has not selected it.

## Open decisions

- Whether `launch_window` stays a distinct verb or becomes `create + viewer_argv` composed
  by the caller. [refine] — mechanical; settle while writing the protocol.
- Whether `switch` is its own capability or just `attach` behaving differently inside a
  host. [refine].
- Whether the herdr host ships in the same PR as the protocol or a follow-up. [refine] —
  default: follow-up, so the refactor stays no-behavior-change.

## Source

Owner session, 2026-07-29 — "can we add a layer and make Horus launchable in tmux, in a
normal terminal, or in herdr?". Call-site sweep and leak table gathered in that session.
Depends on `herdr-host-probe`. Related: `tui-nested-tmux-navigation` (ships first; its two
functions move into `hosts/tmux.py` here), `session-agent-state-awareness`.
