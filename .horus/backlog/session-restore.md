---
status: open
priority: high
created: 2026-07-30
created_by: agent
readiness: shaping
readiness_reason: "Proven end-to-end by hand on 2026-07-30 — three vanished sessions were restored onto tmux and showed up normally in the TUI, so the mechanism is demonstrated rather than theorised. The detection half needs no new plumbing either: `stale` + `termination_reason=None` already means 'vanished'. Blocked on [[agent-thread-id-and-interactive-restore]] for the thread id, and needs one shape call: whether a restored session gets a runner or is a first-class 'adopted' session with declared reduced capability — which also decides how trustworthy the vanished signal is."
phase: explore
type: feature
tier: medium
parallel: unsafe
vision_facet: "Dashboard / cockpit"
surface: horus/registry.py (reconcile:445-452, snapshot:295-303, termination_reason:149), horus/hosts/ (a restore verb on the host protocol), horus/hosts/runnerspec.py, horus/cli.py, horus/terminal_tui.py (launch branch :2607, Sessions view)
---

# session-restore — detect sessions that vanished, and offer to restore them

## Why — proven by hand, 2026-07-30

When the herdr server died it took three live agent sessions with it
([[herdr-live-test-stops-owner-server]]). Their registry rows went `stale` with dead pids
and dead `target_ref`s (`herdr` / `w2:p5`, `w2:p6`, `w2:p3`), and nothing in the product
could bring them back — the herdr session file persists only `cwd`, so there was nothing
to reattach to.

All three were nonetheless fully recoverable, because the durable state was never in the
terminal host: the agent transcripts were intact under
`~/.horus/accounts/<agent>-<alias>/`, and the registry still knew the agent, account,
project and delivery evidence. **The terminal host is the disposable part.** That
generalises well past herdr — a reboot, an OOM kill, or `tmux kill-server` loses sessions
the same way.

Two halves, and neither is much use without the other: a restore verb nobody discovers, or
a warning you cannot act on.

## Naming — restore, not resume (owner, 2026-07-30)

"Resume" already means three different things here, so the new capability is **restore**:

| existing | meaning |
|---|---|
| `horus resume` | prints the project's continuity digest / resume *prompt* |
| TUI **fresh / resume / card-resume** launch modes (`terminal_tui.py:129`) | a *new* session seeded with the resume prompt (see [[fresh-vs-resume-context-split]]) |
| `horus run --resume <id>` | the agent's own conversation thread, headless |
| **restore** (new) | bring a *vanished* session's thread back on a live host |

## Half 1 — detection needs no new plumbing

The signal is already in the data model and merely unnamed. `termination_reason` has a
working taxonomy:

| value | set at | means |
|---|---|---|
| `natural` | `run_executor.py:227` | ran to completion |
| `stopped` | `terminal_sessions.py:367` | the owner stopped it |
| `orphan-reaped` | `terminal_sessions.py:416` | reaped |
| `launch-error` | several | never really started |
| *(nothing)* | — | **vanished** |

`reconcile()` stales any non-terminal row whose pid is gone (`registry.py:447-448`) and
leaves `termination_reason` as `None`. So:

> **`status == "stale" and termination_reason is None`** already means *"this session
> disappeared and nobody recorded why."*

A clean exit cannot produce it, because the runner records `exited`/`failed` with a
returncode first (`tmux_runner.py:101`), and `_jsonl_result` only honours those two
(`registry.py:66`).

**Proposal:** have `reconcile()` name the transition it is already making — e.g.
`termination_reason="vanished"` — so the condition is explicit and queryable rather than
inferred from a null. One line, at the one site that persists it. Note `snapshot()`
(`registry.py:295-303`) computes the same `stale` for *display* without persisting; keep
the write in `reconcile()` only.

### The host-level fingerprint

A dying host looks different from one agent crashing, and the difference is worth using.
On 2026-07-30 three rows staled within two seconds — `09:58:57`, `09:58:58`, `09:58:59` —
all sharing `launch_target=herdr`. When two or more sessions on the *same host* vanish
inside a short window, that is one host event, not N session events, and deserves a single
louder message ("the herdr server went away and took 3 sessions") instead of three
separate notices.

### The caveat that keeps it honest

A session with **no runner** goes stale on a clean exit too, because nothing records the
outcome — which is exactly the state of the three sessions restored by hand on 2026-07-30,
since they skipped `runnerspec`. So `vanished` is only trustworthy for sessions that have a
runner. That ties the detection half directly to the runner shape call below: get it wrong
and the warning cries wolf on every ordinary exit.

## Half 2 — the offer, at the moment it is useful

The owner's framing, and it is the right one: **warn at launch, not only in a list.** The
hook is `terminal_tui.py:2607` (`if isinstance(result, _Launch):`), before the dispatch to
`launch_window` / `_launch`. If the project about to be launched into has a restorable
vanished session, offer restore *instead of* silently starting a fresh one — showing what
would come back (agent, when it vanished, last activity) so the choice is informed.

Two rules worth fixing now:

- **Offer, never auto-restore.** Someone who genuinely wants a fresh session must not have
  a resurrected thread forced on them; that would be a worse surprise than the one this
  fixes.
- **Passive surfacing too.** A vanished row in the Sessions view should read as vanished
  and carry a **Restore** action, so the launch-time warning is not the only route in.

## The restore mechanism — what was done manually, as the spec

Reproduced for all three sessions; ~20 minutes of hand work, no data loss:

1. **Resolve the agent's thread id.** Claude's from its transcript filename under
   `CLAUDE_CONFIG_DIR/projects/<slug>/<uuid>.jsonl`; Codex's from the `session_meta`
   header of `CODEX_HOME/sessions/YYYY/MM/DD/rollout-*.jsonl`. Both were absent from the
   registry — see [[agent-thread-id-and-interactive-restore]].
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

- **`reconcile()` will undo a careless implementation.** `registry.py:448` stales any
  non-terminal row when `process_alive(pid)` fails, so a restored row must carry a
  genuinely live pid. Using the *agent* process (not a runner) made liveness honest — the
  row goes stale by itself when the agent exits.
- **Reviving a `stale` row is legitimate.** `_jsonl_result` (`registry.py:60-70`) only
  honours `exited`/`failed`, so a `stale` row is not pinned by its run log. This is what
  made reusing the original run ids safe, which in turn preserved `fabric-build`'s
  `delivery_pr_number=49` and `delivery_pushed_sha`. Worth an explicit test — it is
  load-bearing and currently incidental.
- **Prefer `update()` over `upsert()`.** A fresh `SessionRecord` resets the whole delivery
  block to defaults; on 2026-07-30 that would have silently dropped the PR linkage.
- **`runnerspec` is the open shape call**, and it now decides two things rather than one:
  whether a restored session reports a real returncode, *and* whether the `vanished`
  signal is trustworthy. Either a restored session gets a runner, or "adopted" becomes a
  first-class state with honestly declared reduced capability. Same question
  [[session-host-protocol]] already carries for hosts without argv-exec semantics
  (herdr's `pane run` types into a shell), so answer them together.
- **Reaping.** tmux declares `liveness=True`, so confirm an adopted session whose pid the
  runner does not own cannot be reaped out from under the owner. Related:
  [[optional-host-ci-coverage]].
- **Not a conflict:** [[session-agent-state-awareness]] is complementary — that surfaces
  `working`/`idle`/`blocked` for *live* sessions, this one moves *vanished* sessions back
  to live. Both want the same Sessions view, so build them with that in mind.

## Sketch

A host-protocol verb plus two cockpit surfaces: `horus sessions --restore <id>
[--target tmux]` takes a vanished row with a known `agent_session_id`, relaunches the
agent's thread interactively on an available host, and rewrites the row in place. In the
TUI, a vanished row grows a **Restore** action, and the launch path offers restore before
starting something fresh in the same project.

The honest limit worth stating up front: this restores the *conversation*, not in-flight
work. Anything the agent had not written to disk when it was killed is gone. On
2026-07-30 that cost nothing — the Codex session's uncommitted diff was still on disk and
both Claude sessions had committed — but that was luck, and it is the argument for
`horus checkpoint`-style habits rather than something this card can fix.

## Reviews

### 2026-07-30 — Rafael Figueiredo (manual)

2026-07-30 — **priority medium → high** (owner, resume session). Elevated together with [[agent-thread-id-and-interactive-restore]] so the pair is analysed as ONE restore capability rather than two independently-scheduled cards. The owner's reasoning: these are the general improvements that arrived with the herdr incident bugs, they share that context, and splitting them across sessions would force re-deriving it. Priority only — readiness stays `shaping` and the blocking relationship on the thread-id card is unchanged, because both open shape calls are still open.

### 2026-07-30 — Rafael Figueiredo (manual)

2026-07-30 — **superseded in practice: delivered as part of the restore campaign** (#456/#457/#458), rather than as a separate build. Both halves this card specified are in: detection (`reconcile()` writes `vanished`, with the card's own caveat honoured — the signal is gated on whether the launch target records its own exit, so runnerless `local` rows are left unlabelled instead of crying wolf on every ordinary quit) and the offer (vanished rows appear in the TUI Sessions list labelled `vanished — restorable`, with a Restore action; never automatic, as the card required). Two of this card's framings were corrected by the code: the runner-vs-'adopted' shape call dissolved (interactive launches already have runners, so restore needs no new session state), and the host-level fingerprint plus a `horus sessions --restore` CLI verb were deliberately NOT built — the owner's stated surface was `horus tui`, and an unused verb is another surface to keep honest. The honest limit the card states is unchanged and now surfaced in the UI text: restore reopens the conversation, not in-flight work.
