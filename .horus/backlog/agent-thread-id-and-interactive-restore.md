---
status: open
priority: high
created: 2026-07-30
created_by: agent
readiness: shaping
readiness_reason: "The gap is proven and both agent CLIs already support what is needed, so the mechanism is not in doubt. The naming question is settled — the Horus-facing verb is 'restore' (owner, 2026-07-30). One shape decision remains: whether recording the thread id is a launch-time parse of the agent's stream or an activity-time backfill from the transcript."
phase: converge
type: feature
tier: high
parallel: unsafe
vision_facet: "Continuity core"
surface: horus/registry.py (agent_session_id:145-147), horus/adapters/claude.py (interactive_command:169-191, build_command:114-118), horus/adapters/codex.py (interactive_command:132-152), horus/launch.py (prepare_interactive:55-118)
---

# agent-thread-id-and-interactive-restore — Horus cannot reopen a session it launched

## Why — 2026-07-30, found while recovering three lost sessions

An interactive session Horus launched cannot be reopened by Horus. Two independent gaps
stack, and either one alone is enough to make recovery impossible.

### 1. The agent's thread id is never recorded

`registry.SessionRecord` has the right field, and its comment describes exactly this
purpose (`registry.py:145-147`):

> *"`session_id` is Horus's durable run identity. The agent's resumable
> conversation/thread id arrives later (or is supplied by `--resume`), so it is
> deliberately separate and nullable for a newly-launched run."*

In practice it is never filled for an interactive launch. All three sessions live on
2026-07-30 had `agent_session_id=None` — including the Codex one, whose rollout id
existed only inside `~/.horus/accounts/codex-personal/sessions/2026/07/29/rollout-*.jsonl`
and was recorded nowhere Horus could see. Recovering them meant reading Codex's rollout
header and Claude's transcript filenames by hand.

Both ids are obtainable:

- **Claude** echoes its session id in the `system/init` event — already noted in
  `adapters/claude.py:8`.
- **Codex** cannot pre-assign a thread id, but writes a `session_meta` record carrying
  `session_id` as the first line of its rollout file.

### 2. The interactive path cannot resume even when given an id

`launch.prepare_interactive` accepts `session_id` (`launch.py:64`), which reads as resume
support. It is not:

| adapter | what `session_id` becomes | effect |
|---|---|---|
| claude | `["claude", "--session-id", <id>]` (`claude.py:178`) | **assigns** an id to a *new* session; an already-used id collides |
| codex | *discarded* (`codex.py:135-138`) | "accepted (satisfying the pty_host contract) but not forwarded to the CLI" |

Real resume exists only on the headless path — `build_command` adds `--resume`
(`claude.py:117-118`), and Codex uses `codex exec resume --json` (`codex.py:96`) — and
that path is deliberately not typeable: `base.py` launches it with
`stdin=subprocess.DEVNULL`, commented *"the prompt is an arg; don't let the child wait on
stdin"*.

So **`horus run --resume` gives a headless one-shot; the interactive path gives a fresh
session. There is no interactive thread-resume on any host.**

Both CLIs support it natively — verified from `--help`, 2026-07-30:

```
claude  -r, --resume [value]     Resume a conversation by session ID
codex   resume [OPTIONS] [SESSION_ID] [PROMPT]    Resume a previous interactive session
```

Confirmed working by hand the same day: three dead sessions were reopened with their full
history intact via `claude --resume <id>` and `codex resume <id>`, under
`CLAUDE_CONFIG_DIR` / `CODEX_HOME` for the right account.

## The naming collision — resolved: restore (owner, 2026-07-30)

"Resume" already meant three different things here, so the new capability is **restore**:

| term | meaning |
|---|---|
| `horus resume` | prints the project's continuity digest / resume *prompt* |
| TUI **fresh / resume / card-resume** launch modes (`terminal_tui.py:129`) | a *new* session seeded with the resume prompt (see [[fresh-vs-resume-context-split]]) |
| `horus run --resume <id>` | the agent's own conversation thread, headless |
| **restore** (new) | bring a vanished session's thread back on a live host |

Note the split this keeps clean: *restore* is the Horus-facing verb, while the agent CLIs'
own flags stay whatever they are (`claude --resume`, `codex resume`). A fourth sense of
"resume" in Horus's own vocabulary would have made
[[fresh-vs-resume-context-split]] harder to reason about, not easier.

## Shape

1. **Record the thread id at launch.** Decide between parsing it at launch (Claude's
   `system/init`; Codex's rollout `session_meta`) versus backfilling from the transcript
   on first activity. Launch-time is tighter but needs a read of the agent's stream that
   the interactive path does not currently do.
2. **Make `interactive_command` resume-capable.** Give it a real resume id distinct from
   the assign-an-id case, so Claude emits `--resume <id>` instead of `--session-id <id>`,
   and Codex forwards the id it currently drops.
3. Keep `session_id` (Horus's durable run identity) and `agent_session_id` (the agent's
   thread) strictly separate, as the existing comment already intends. On 2026-07-30 they
   happened to be equal for Claude and *different* for Codex — any code assuming they
   match will be wrong exactly half the time.

Unblocks [[session-restore]], which is unimplementable without step 1.
