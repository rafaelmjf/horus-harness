---
status: open
priority: medium
created: 2026-07-30
created_by: agent
readiness: shaping
readiness_reason: "Proven end-to-end by hand on 2026-07-30 — three dead sessions were rehosted onto tmux and showed up normally in the TUI, so the mechanism is demonstrated rather than theorised. Blocked on [[agent-thread-id-and-interactive-resume]] for the thread id, and needs one shape call: whether a rehosted session gets a runner or is a first-class 'adopted' session with declared reduced capability."
phase: explore
type: feature
tier: medium
parallel: unsafe
vision_facet: "Dashboard / cockpit"
surface: horus/registry.py (update / reconcile:420-453), horus/hosts/ (a rehost verb on the host protocol), horus/hosts/runnerspec.py, horus/cli.py, horus/terminal_tui.py (Sessions view)
---

# session-rehost-recovery — move a dead session's agent thread onto a live host

## Why — proven by hand, 2026-07-30

When the herdr server died it took three live agent sessions with it
([[herdr-live-test-stops-owner-server]]). Their registry rows went `stale` with dead pids
and dead `target_ref`s (`herdr` / `w2:p5`, `w2:p6`, `w2:p3`), and nothing in the product
could bring them back — the herdr session file persists only `cwd`, so there was nothing
to reattach to.

All three were nonetheless fully recoverable, because the durable state was never in the
terminal host: the agent transcripts were intact under
`~/.horus/accounts/<agent>-<alias>/`, and the registry still knew the agent, account,
project and delivery evidence. **The terminal host is the disposable part.** That is the
insight worth building on, and it generalises well past herdr — a reboot, an OOM kill, or
`tmux kill-server` loses sessions the same way.

## What was done manually — the spec

Reproduced for all three sessions; ~20 minutes of hand work, no data loss:

1. **Resolve the agent's thread id.** Claude's from its transcript filename under
   `CLAUDE_CONFIG_DIR/projects/<slug>/<uuid>.jsonl`; Codex's from the `session_meta`
   header of `CODEX_HOME/sessions/YYYY/MM/DD/rollout-*.jsonl`. Both were absent from the
   registry — see [[agent-thread-id-and-interactive-resume]].
2. **Relaunch interactively on a live host**, in the project cwd with the account's config
   dir: `CLAUDE_CONFIG_DIR=… claude --resume <id>` /
   `CODEX_HOME=… codex resume <id>`. History came back intact; the Codex pane even showed
   its `■ Conversation interrupted` marker at exactly the point it was HUP'd.
3. **Match the host's layout convention.** One tmux session per agent named
   `horus-<session_id[:12]}` (`hosts/tmux.py:143`), plus `set-option mouse on` as the host
   does. The first attempt used one session with three windows and was wrong: `attach` and
   `stop` both key on the tmux *session* name, so `horus stop` on any one would have killed
   all three.
4. **Rewrite the registry row** — `status=running`, live `pid`, `launch_target=tmux`, the
   new `target_ref`, and the recovered `agent_session_id`.

Result: all three appeared in `horus sessions --running` and in the TUI as normal
`tmux · <id>` rows, resolved to `TmuxHost`, and survived `reconcile()`.

## Conflicts and constraints — checked, 2026-07-30

**Nothing blocks this outright.** The specific things it touches:

- **`reconcile()` will undo a careless implementation.** `registry.py:449` flips any
  non-terminal row to `stale` when `process_alive(pid)` fails, so a rehosted row must carry
  a genuinely live pid. Using the *agent* process (not a runner) made liveness honest —
  the row goes stale by itself when the agent exits.
- **Reviving a `stale` row is legitimate.** `_jsonl_result` (`registry.py:60-70`) only
  honours `exited`/`failed`, so a `stale` row is not pinned by its run log. This is what
  made reusing the original run ids safe, which in turn preserved `fabric-build`'s
  `delivery_pr_number=49` and `delivery_pushed_sha`. Worth an explicit test — it is
  load-bearing and currently incidental.
- **Prefer `update()` over `upsert()`.** A fresh `SessionRecord` resets the whole delivery
  block to defaults; on 2026-07-30 that would have silently dropped the PR linkage.
- **`runnerspec` is the open shape call.** The manual rows skipped it, so there is no
  runner process and no spec file — meaning no real returncode
  (`reports_exit_code`). Either a rehosted session gets a runner, or "adopted" becomes a
  first-class state with honestly declared reduced capability. This is the same question
  [[session-host-protocol]] already carries for hosts without argv-exec semantics
  (herdr's `pane run` types into a shell), so the two should be answered together.
- **Reaping.** tmux declares `liveness=True`, so confirm an adopted session whose pid the
  runner does not own cannot be reaped out from under the owner. Related:
  [[optional-host-ci-coverage]].
- **Naming.** Do not call this `resume`; three meanings already exist. See the collision
  table in [[agent-thread-id-and-interactive-resume]].
- **Not a conflict:** [[session-agent-state-awareness]] is complementary — that surfaces
  `working`/`idle`/`blocked` for *live* sessions, this one moves *dead* sessions back to
  live. Both want the same Sessions view.

## Sketch

A host-protocol verb plus a cockpit action, roughly `horus sessions --rehost <id>
[--target tmux]`: take a `stale` row with a known `agent_session_id`, relaunch the agent's
thread interactively on an available host, and rewrite the row in place. In the TUI, a
stale row with a recoverable thread grows a **Reopen** action.

The honest limit worth stating up front: this recovers the *conversation*, not in-flight
work. Anything the agent had not written to disk when it was killed is gone. On
2026-07-30 that cost nothing — the Codex session's uncommitted diff was still on disk and
both Claude sessions had committed — but that was luck, and it is the argument for
`horus checkpoint`-style habits rather than something this card can fix.
