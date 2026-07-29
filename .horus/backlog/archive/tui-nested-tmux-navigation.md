---
status: shipped
priority: medium
created: 2026-07-29
created_by: owner
readiness: ready
autonomy: attended
order: 5
phase: converge
type: bug
tier: medium
parallel: safe
vision_facet: "Dashboard / cockpit"
surface: horus/terminal_sessions.py, horus/terminal_tui.py, horus/terminal_app.py, tests/test_terminal_sessions.py
shipped_pr: 439
shipped_sha: 755347a
---

# tui-nested-tmux-navigation — make `horus tui` usable *inside* tmux (switch-client, not refuse)

## Why — observed live, 2026-07-29

The owner tried running `horus tui` itself inside tmux (so the TUI is one pane and
agents are others) and found it "conflicts with our launch configs". It does, in three
specific places, all written when "the TUI is outside tmux" was assumed:

| Site | Behavior when `$TMUX` is set |
|---|---|
| `terminal_sessions.py:48` (`default_target`) | returns `current`, so a TUI launch takes over the TUI's own pane via `run_attached` — no tmux backing, so the row is `original terminal only`, not attachable, unreachable from the phone |
| `terminal_sessions.py:161` (`launch_tmux`) | forcing `HORUS_TERMINAL_TARGET=tmux` fails outright: *"already inside tmux; use --target current"* |
| `terminal_sessions.py:392` (`attach_session`) | refuses — so the Sessions screen's attach action is **dead for every session** |

Net effect: running the TUI in tmux is strictly *worse* than running it in a plain
terminal. The attach refusal is a plain bug, not a design choice.

## The key insight — no nesting is actually required

The TUI and every `horus-*` agent session share **one tmux server**, so the client can
be *moved* rather than nested. Probed on an isolated socket, 2026-07-29:

- `tmux switch-client -c <client> -t horus-a` moved a live attached client from the
  TUI's session to an agent session, `rc=0`. This is the exact substitute for
  `attach-session` when `$TMUX` is set, and it means **no nested client** — so no
  doubled prefix keys, no second server.
- `tmux link-window -s horus-a:0 -t <tui-session>:` succeeded and left `horus-a`
  intact (window count unchanged) while the TUI session gained a second window. So an
  agent can appear as a **tab** in the TUI's own session, non-destructively.

Also worth documenting rather than building: from inside any attached agent,
`Ctrl-b s` / `Ctrl-b ( )` already switches across every running Horus session. That
navigator exists today and nothing mentions it.

## What to build

- `attach_session`: when `$TMUX` is set, `tmux switch-client -t <target_ref>` instead of
  returning an error. Outside tmux, unchanged (`attach-session`).
- `default_target`: drop the `$TMUX → CURRENT` special case; agents get a persistent
  host either way.
- `launch_tmux`: drop the inside-tmux refusal; route its attach through the same
  nested-aware path.
- Optional, and the literal "tabs" ask: an action that runs
  `link-window -s <ref>:0 -t <current-session>:` to tab an agent into the TUI's view.
  **Never `join-pane`** — it *moves* the process, the source session dies, and the
  registry row is orphaned.

## Acceptance

- With `horus tui` running inside tmux: a launch creates a real `horus-<id12>` session
  (attachable, phone-reachable), and attach from the Sessions screen switches the client
  to it rather than erroring.
- `Ctrl-b L` (or choose-tree) returns to the TUI session with its frame intact.
- Outside tmux, every path behaves exactly as today — `attach-session` still blocks
  until detach.
- The status strings are corrected. `switch-client` returns *immediately* where
  `attach-session` blocked until detach, so "Detached from X" / "Session X returned to
  Horus" are wrong in the nested case and must say what actually happened.
- `tests/test_terminal_sessions.py:445` (which asserts the current refusal) is updated,
  and new nested tests cover switch/launch/attach. Per the standing rule, every
  tmux-touching test routes through a private `-S <path>` socket with inherited `TMUX`
  unset — a fake `$HOME` does **not** sandbox tmux.
- Gate: full suite green on the exact SHA, plus a live probe of the real flow (TUI in
  tmux → launch → switch → return).

## Guardrails

- Reaping is untouched. Nothing here relaxes the positive-confirmation invariant.
- Do not introduce a second tmux server or a nested client anywhere.

## Known rework cost

`attach_session` and `default_target` are exactly the functions `session-host-protocol`
will move into `horus/hosts/tmux.py`. That relocation is mechanical (~15 min) and is
accepted deliberately: this card fixes a bug users hit today and should not be gated
behind a refactor.

## Source

Owner session, 2026-07-29 — evaluating multi-session management after trying to run the
TUI in tmux. Sibling cards: `herdr-host-probe`, `session-host-protocol`,
`session-agent-state-awareness`.
