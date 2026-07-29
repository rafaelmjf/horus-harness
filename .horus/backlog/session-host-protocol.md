---
status: open
priority: medium
created: 2026-07-29
created_by: owner
readiness: shaping
readiness_reason: "UNGATED 2026-07-29 — herdr-host-probe answered all four questions, so the capability set is now derived from two real hosts. Two shape decisions remain before this is Ready, both surfaced by the probe: how a host without argv-exec/exit-code semantics (herdr `pane run` types into a shell) fits the pane_runner contract, and whether the herdr host ships with the protocol or follows it. Owner call in a refine pass."
phase: converge
type: feature
tier: high
parallel: unsafe
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
- **`herdr`** — probed live on v0.7.5 (2026-07-29; full evidence in `herdr-host-probe`).
  Capabilities: `persistent=True`, `attach=True`, `viewer_argv=True`, `state=True`
  (`idle`/`working`/`blocked`/`done`/`unknown`), **`liveness=False`** — it exposes no
  attached flag and no activity clock, so its panes are never reaped. Three things the
  probe found that this protocol must absorb:
  - **A new obligation tmux doesn't have: `ensure_server`.** The herdr CLI does *not*
    autostart its server; `workspace create` fails outright without one. So the host
    interface needs a "make the host available" step, which for tmux is a no-op.
  - **No argv-exec and no exit code.** `herdr pane run` *types the command into the
    pane's shell* (probed: quoting was not preserved), so the runner is a child of a
    shell rather than the pane's root process, and nothing plays the role of tmux's
    `new-session <cmd>` + `wait` returncode. The `pane_runner` already records its own
    status in the registry, so this works — but "the host reports the exit code" cannot
    be part of the contract.
  - **Isolated config dirs collide with socket-path limits.** herdr derives its API
    socket from its config dir, and a long path fails with *"local socket name length
    exceeds capacity of sun_path"* (hit on the first attempt). Horus gives every account
    an isolated config dir, so per-account herdr isolation needs deliberately short
    paths — a constraint on the design, not an implementation detail.
  - **The viewer frames a whole session, not one pane.** `session attach` renders herdr's
    entire UI. Horus's tmux model (one session per agent, so `attach -t` frames exactly
    one agent) does not map directly; whether `agent attach <target>` narrows it is
    untested and worth settling before the browser-viewer path is wired.

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

## Reviews

- **2026-07-29 — Stage A landed (PR #441): the protocol exists, every leak is
  closed, no behavior change.** `horus/hosts/` holds `base.py` (protocol +
  `Capabilities`), `tmux.py`, `current.py`, and `runnerspec.py`; `terminal_sessions`
  is the façade with an unchanged public API. Verified by the full suite (2350
  passed) plus a re-run of the nested-tmux live probe through the new layer, with
  byte-identical results.

  Two design calls made while building, both worth keeping:

  - **`viewer_argv` takes the ref, not a record.** The first pass had
    `launch_window` look the record up to build the argv; two tests caught it. A
    viewer is a property of the host's own naming, so it must not depend on a
    registry lookup succeeding — and taking the ref is also exactly what herdr's
    focus-then-attach needs.
  - **`liveness` gates reaping structurally**, not by convention: a host without it
    is never even asked for candidates (there is a test asserting `live_refs()` is
    not called). The positive-confirmation rule is now something the interface
    cannot express wrongly.

  Settling the two shape decisions this card was holding:

  1. **The `pane_runner` contract**: the host is never asked for the agent's
     outcome. `reports_exit_code` is declared but is *informational* — the registry
     is the single source of outcome truth, written by the runner itself, which is
     already true on every host today. A host that types a command into a shell is
     therefore the normal case, not a degraded one.
  2. **The herdr host is a separate PR**, so Stage A stayed a strict
     no-behavior-change refactor and a failure cannot be ambiguous between the two.

  Remaining on this card: the herdr host (Stage B), and renaming `tmux_runner` →
  `pane_runner` with a shim — deferred deliberately, because the module name is
  embedded in the runner specs of sessions running right now, and it is cosmetics.

- **2026-07-29 — Stage B landed (PR #442) and the front door with it (PR #443).**
  The herdr host is ~370 lines and needed **no caller change** — registering it made
  it work in the TUI, the terminal app, `horus open` and `--target herdr` through
  `launch_on()`, which is the result Stage A was for. Verified end-to-end on a real
  server; full evidence in `.horus/backlog/archive/herdr-host-probe.md` and the PR.

  Two implementation facts only a live server could have produced, both now pinned
  by tests: `herdr pane focus` is *directional* (bringing a session into view is
  `workspace focus <workspace_id>`, read from `pane get` rather than parsed off the
  ref), and agent state comes from `pane get`.`agent_status` — `agent explain`
  errors `agent_not_found` on an undetected pane, which is a normal state.

  #443 then added the cockpit front door the owner asked for (`horus tui tmux` /
  `horus tui herdr`, positional by owner preference) plus a persisted
  where-to-host default in the TUI Defaults screen. It also fixed a **latent
  resolution bug** this card's design had not anticipated: `resolve()` ignored the
  host Horus was running *inside*, so a cockpit in a herdr pane launched agents onto
  tmux — different servers, no way to switch back. `hosts.enclosing()` now ranks
  below the env override and an explicit config choice but above `AUTO_ORDER`.

  **All that remains on this card is the `tmux_runner` → `pane_runner` rename**
  (needs a shim; the module name is embedded in the runner specs of sessions running
  right now). Its `tier: high` / `parallel: unsafe` stamps describe the refactor that
  has now shipped, not a rename — worth rescoping or carving out in the next refine
  pass rather than me deciding here.
