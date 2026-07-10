# Bug: `horus app` wedges silently when a stale companion holds the singleton lock

## Status

Reproduced on 2026-07-10 against installed `horus 0.0.34` on Windows 11
(`win32`). Root-caused from source; primary finding is solid and reproduced
end-to-end. One secondary observation (double-spawn) is flagged as
needs-confirmation.

## Summary

`horus app` silently does nothing when an orphaned companion process from an
earlier session is still holding the singleton lock. The user runs `horus app`,
the terminal returns immediately, no window opens, and **no message or log is
produced**. The dashboard server itself is healthy — the failure is entirely in
the companion launch path.

Observed live: a user's `pythonw -m horus app` companion from a session **two
days earlier** (2026-07-08, build 0.0.29) was still resident and holding
`127.0.0.1:8764`. Every subsequent `horus app` (build 0.0.34) hit the held lock
and exited 0 without opening anything. The user's report was simply "horus app
is not opening the local dashboard" — with no error to go on, because there
isn't one.

## Reproduction

1. Launch `horus app` and leave the detached companion running. Close its
   dashboard window (the `pythonw` process stays alive, still holding 8764).
2. Run `horus app` again.
3. Result: returns 0 immediately; no window; no stdout; no `companion.log`
   entry. The old companion keeps owning the lock indefinitely across reboots of
   the *terminal* (though not the machine).

Confirmed instrumentation during the incident:

```text
# singleton port held by a stale companion (not the current invocation)
TCP    127.0.0.1:8764   LISTENING   12536   # pythonw -m horus app  (2-day-old)
TCP    127.0.0.1:8765   LISTENING   11392   # that companion's dashboard child

# the no-op, only visible because --no-detach kept it inline:
$ horus app --no-detach
Horus companion already running; not starting another.
```

Killing the four orphaned `pythonw` processes freed 8764/8765; a fresh
`horus app` then bound the singleton and served HTTP 200 normally.

## Causal trace

### 1. The diagnostic message is swallowed in the default (detached) path

`cmd_app` (`horus/cli.py:1676`) relaunches windowless **before** the
companion logic runs:

```python
def cmd_app(args):
    ...
    if not getattr(args, "no_detach", False) and companion.relaunch_without_console():
        return 0            # parent exits here, silently, freeing the terminal
    ...
    return companion.run_companion(...)
```

`relaunch_without_console` (`horus/companion.py:309`) spawns
`pythonw -m horus app` with `stdout/stderr = DEVNULL`. The "already running"
check lives inside `run_companion`, which now runs only in that **detached,
DEVNULL** child:

```python
# horus/companion.py:611
lock = acquire_singleton_lock()          # binds 127.0.0.1:8764
if lock is None:
    print("Horus companion already running; not starting another.")
    return 0
```

So in the normal path the message prints to `DEVNULL` and the parent has
already returned 0 to the terminal. **The user gets zero feedback** — the
message is only visible with `--no-detach`. There is also **no
`log_companion_event`** on this branch, so nothing lands in
`~/.horus/logs/companion.log` either.

### 2. The lock has no staleness/liveness/version check

`acquire_singleton_lock` (`horus/companion.py:79`) is a bare
`bind(("127.0.0.1", 8764)); listen(1)`. Holding the lock is treated as proof
that "another companion is alive and owns a usable window." Neither is
guaranteed: the holder may be a zombie, an orphan whose window was closed, or a
**different/older build**.

Contrast the dashboard port (8765), which *does* have staleness handling:
`_replace_stale_dashboard` (`horus/companion.py:175`) reads
`/health` for pid+version and kills a Horus dashboard whose `version !=
__version__` (the comment even cites "a 3-day-old PID surviving many
quit/reopen cycles"). There is **no analogous reaper for the singleton port
8764** — so the exact stale-orphan problem that dashboard adoption already
solves is left wide open on the companion lock.

### 3. No window-raise across processes

Even when the lock-holder is genuinely alive, a new `horus app` cannot bring
its window forward: `raise_dashboard_window` /
`launcher.focus_window_for_pid` operate on the *in-process* browser handle
(`horus/companion.py:451`), and the new invocation has no handle to the other
process's window. So "already running" can't even mean "I raised the existing
window for you."

### Secondary observation (needs confirmation): double-spawn

From a verified-clean state (0 horus `pythonw`, 8764/8765 free), a **single**
`horus app` left **two** `-m horus app` and **two** `-m horus dashboard`
processes; only one held 8764 and one held 8765. The relaunch guard
(`HORUS_DETACHED=1` + `python.exe`-only check at `companion.py:322-328`) looks
correct and should prevent a grandchild, so this may be an interaction between
the pre-warm thread's `ensure_open` and dashboard spawning, or a measurement
artifact from a noisy test sequence. Worth confirming because duplicate
companions are the raw material that accumulates into the stale-lock wedge
above.

## Why this matters

- The user-facing symptom is "the app is broken and gives me nothing" — the
  single hardest failure mode to self-diagnose. The tool *knows* exactly what's
  wrong ("already running") and throws that knowledge away in the default path.
- Orphaned companions survive terminal restarts and build upgrades, so the
  wedge is sticky: upgrading `horus` does not clear it, and the new build never
  reaps the old holder.
- The recovery today requires the user to know about the singleton port, list
  `pythonw` processes, and `taskkill` them — none of which is discoverable from
  the tool.

## Recommended behavior

### 1. Surface the condition before detaching (P0)

Check the singleton **in `cmd_app`, in the parent, before
`relaunch_without_console`**, so any feedback reaches the user's terminal:

- If the lock is free: proceed to relaunch as today.
- If held: do not silently return 0. Print an actionable line naming the holder
  PID and the recovery command, and `log_companion_event` the decision.

### 2. Reap a stale companion on 8764, mirroring the dashboard path (P0/P1)

Add the singleton analogue of `_replace_stale_dashboard`:

- Resolve the holder via `_pid_listening_on(8764)`.
- Establish liveness + identity. The bare socket carries no protocol, so give
  the companion a tiny sidecar on startup — e.g.
  `~/.horus/cache/companion.json` with `{pid, version, dashboard_port,
  window_handle, started_at}` — and validate the holder against it (PID alive?
  cmdline still `-m horus app`? version == current?).
- If the holder is dead-but-lock-lingering, a foreign/older version, or has no
  reachable window: kill it (`_kill_pid_tree`) and reacquire.
- If it is genuinely current and alive: **raise its window** using the recorded
  pid via `focus_window_for_pid`, then exit 0 — that is the correct "already
  running" behavior.

### 3. Add an explicit escape hatch (P1)

`horus app --restart` (or `--force`): unconditionally kill the current
companion + its dashboard child and relaunch fresh. This is the one-command
recovery the incident required, and a safe thing to document.

### 4. Investigate the double-spawn (P2)

Confirm or refute that one `horus app` yields two companions/dashboards from a
clean state. If real, ensure exactly one companion and one dashboard per launch
(the loser of the singleton race should exit promptly and not have spawned a
second dashboard first).

## Acceptance criteria

- Running `horus app` while a **stale/zombie/old-version** companion holds 8764
  reaps it and opens normally — no manual `taskkill` required.
- Running `horus app` while a **current, live** companion holds 8764 raises the
  existing window and exits 0; it does not spawn a duplicate.
- In every held-lock case the user gets terminal feedback **and** a
  `companion.log` line — never a silent 0-exit with no window.
- `horus app --restart` kills the existing companion tree and relaunches.
- A single `horus app` from a clean state leaves exactly one `-m horus app` and
  one `-m horus dashboard` process.
- Tests cover: free lock (normal launch), stale-holder reap, live-holder raise,
  foreign/old-version holder, and the `--restart` path.

## Relevant code

- `horus/cli.py:1676` — `cmd_app`: relaunch-then-run ordering; where the
  pre-detach singleton check belongs.
- `horus/companion.py:79` — `acquire_singleton_lock`; `SINGLETON_PORT = 8764`.
- `horus/companion.py:175` — `_replace_stale_dashboard`: the reaper to mirror
  for the singleton port.
- `horus/companion.py:309` — `relaunch_without_console`: DEVNULL detach + the
  `HORUS_DETACHED` guard.
- `horus/companion.py:584` — `run_companion`: the `lock is None` branch that
  prints to a swallowed stdout with no log.
- `horus/companion.py:451` — `raise_dashboard_window` /
  `launcher.focus_window_for_pid`: in-process only; needs a pid-based path for
  cross-process raise.
- `tests/test_companion.py` — current companion coverage.
