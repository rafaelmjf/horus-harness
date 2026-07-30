---
status: open
priority: high
created: 2026-07-30
created_by: agent
readiness: ready
readiness_reason: "Root cause is proven from two independent logs, and the fix is bounded because the test already promises the isolation in its own docstring — this is making the code honour a contract it states. No shape decision remains."
autonomy: attended
phase: converge
type: bug
tier: high
parallel: safe
vision_facet: "Distribution"
surface: tests/test_hosts_herdr.py (test_live_herdr_server_lifecycle:317-352), horus/hosts/herdr.py (_run:89 — no socket override), tests/test_terminal_sessions.py (the 2026-07-13 tmux precedent, :297-315)
---

# herdr-live-test-stops-owner-server — the live host test kills the owner's real agent sessions

## What happened — 2026-07-30, measured

Three live agent sessions died mid-work: Claude on `fabric-utils`, Claude on
`fabric-build`, and Codex on `horus-harness`. The Codex session was working *in this
repo* on `feat/tui-click-activate` and had uncommitted changes at the time.

The cause was this repo's own test suite. `test_live_herdr_server_lifecycle` runs against
the **default** herdr server — the one holding the owner's sessions — and its `finally`
block stops it:

```python
finally:
    herdr_host._run("server", "stop")
```

Its docstring claims otherwise:

> *"Isolated via a private config dir, and the config dir is kept SHORT because herdr
> derives its API socket from it..."*

No such config dir is ever set. `monkeypatch` is in the signature and never used for
isolation; `tmp_path` is only passed as the new workspace's `--cwd`. The test is
gated solely on `shutil.which("herdr")`, so it skips on CI and **runs on the owner's
machine**, where herdr is installed and in daily use.

## Evidence

Codex ran the *full* suite (not a filtered selection) three times at `09:57:19`,
`09:57:30`, `09:57:35`:

```
uv run python -m compileall -q horus tests && uv run pytest -q
```

`~/.config/herdr/herdr-server.log` then records the test's steps in order, ending in the
shutdown that HUP'd every pane:

| test step | server log (2026-07-30) |
|---|---|
| `host.ensure_ready()` | (server already up — reused, not started) |
| `workspace create --label horus-live-test` | `09:58:44.335 method="workspace.create"` → `w3`, pane 10 (a `workspace.rename` follows, consistent with `--label`) |
| `pane run <pane> "sleep 120"` | — |
| `pane close <pane_id>` | `09:58:44.469 method="pane.close"` |
| **`finally: _run("server", "stop")`** | `09:58:44.502 server shutdown initiated` |
| | `09:58:44.606→45.977 pane.exit 1, 6, 4, 7 — signal: Hangup` |

The client exited 4ms *after* the server decided to shut down
(`09:58:44.506 herdr exiting pid=3769632`), which is why this presented to the owner as
"the UI closed with exit 1" rather than as a test killing their work.

**Control that rules out the other suspect.** `PaneDied for unknown pane` is a real herdr
defect (see [[herdr-server-shutdown-fragility]]) but is *not* what killed these sessions:
panes 8 and 9 produced the identical warning at `09:53:30` and `09:53:56` and the server
survived both. Only the run containing `server stop` was fatal.

## The precedent this ignores

This is the same class of incident as **2026-07-13**, and the guard written for it was
never extended to the second host. From `tests/test_terminal_sessions.py:297`:

> *"Isolation is mandatory here (PRD Rules, 2026-07-13 incident): every tmux subprocess
> call this module makes is routed through an explicit `-S <path>` socket for a throwaway
> server, so this can never see or touch the default tmux server / any real session on
> it."*

tmux gets `-S`. herdr gets nothing: `horus/hosts/herdr.py:89` is

```python
return subprocess.run(["herdr", *args], ...)
```

with no socket override anywhere in the module — even though herdr exports
`HERDR_SOCKET_PATH` into every pane (`herdr.py:77`), so the primitive plainly exists.

## Fix

Two changes, both small; the second is the one that removes the catastrophic step.

1. **Never stop a server you did not start.** `ensure_ready()` already knows whether it
   started one. Only `server stop` in that case. One conditional, and the blast radius
   of this test drops from "all the owner's sessions" to nothing.
2. **Give `_run` a socket/config-dir override and point the live test at a throwaway
   server** — i.e. implement the isolation the docstring already claims. Mirrors the tmux
   `-S` precedent and makes the whole module testable against a real herdr without
   touching the daily one. Keep the config dir short: herdr derives its API socket path
   from it and a long path overflows `sun_path` (observed 2026-07-29).

Worth considering as belt-and-braces: refuse to run a live host test at all while the
registry holds a `running` session on that host.

## Secondary leak — test state reaches the real `~/.horus`

Related and probably the same root: the production registry contains obvious fixture
rows — `12345678-1234-1234-1234-123456789abc` (agent `fake`, project `x`), plus
`aaaaaaaa-`/`bbbbbbbb-`/`cccccccc-`/`dddddddd-` prefixed ids — and
`~/.horus/logs/runs/12345678-1234-1234-1234-123456789abc.jsonl` was **written at
09:55:42Z**, inside the same test window. `_home()`
(`tests/test_terminal_sessions.py:42`) does redirect `HOME`/`USERPROFILE`, so the leak
comes from a path that does not use it. Worth pinning while the above is in hand.

## Open question

Panes 8 and 9 were created by `cli:tab:create` at `09:53:25` and `09:53:51` — 4s and 6s
after Codex's two *filtered* runs of `tests/test_terminal_tui.py
tests/test_terminal_sessions.py`. That is the herdr host's tab-create path
(`herdr.py:219`), but no test in those two files calls a launch verb with herdr
available (the only `_only_available(monkeypatch, "herdr")` at
`test_terminal_sessions.py:124` just asserts `default_target()`). Source not pinned —
resolve by correlating a full-suite run against the server log rather than by guessing.
