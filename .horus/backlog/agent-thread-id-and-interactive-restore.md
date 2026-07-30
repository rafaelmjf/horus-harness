---
status: open
priority: high
created: 2026-07-30
created_by: agent
readiness: ready
autonomy: attended
readiness_reason: "No shape decisions remain. Naming settled (the verb is 'restore', owner 2026-07-30) and the recording question settled by the code in #456: there is no stream on the interactive path, so the answer is asymmetric per adapter and is now declared as `assigns_interactive_thread_id`. Step 1 shipped; steps 2 (resume-capable `interactive_command`) and 3 (TUI restore surface) are mechanical against a proven id. Attended because verifying it means launching real agent sessions and reading their history back — a wrong thread id reopens somebody else's conversation, which no deterministic gate catches."
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

## Reviews

### 2026-07-30 — Rafael Figueiredo (manual)

2026-07-30 — **elevated as the lead of a paired analysis** (owner, resume session). Priority was already `high` and is unchanged; what changed is that [[session-restore]] was raised medium → high to sit alongside it, so the two are analysed together as ONE restore capability in the session that takes them. This card stays the lead because [[session-restore]] is blocked on it for the thread id — recording the id is the prerequisite half, and restoring is the payoff half. Owner's reasoning: these are the general improvements that arrived with the herdr incident bugs, they share that context, and splitting them across sessions would force re-deriving it. Both remain `readiness: shaping`; the two open shape calls (launch-time parse vs activity-time backfill here, runner-vs-adopted there) are unaffected by the priority change and are still what the paired session has to settle.

### 2026-07-30 — Rafael Figueiredo (manual)

2026-07-30 — **step 1 of 3 shipped in #456** (thread id recorded on interactive launches). Two things were settled by the code rather than by discussion, and both narrow what remains. (1) The stated shape decision — launch-time stream parse vs activity-time backfill — was a false dichotomy: **there is no stream on the interactive path** (`claude.py:171` says interactive runs don't stream stream-json back; an attended Codex TUI streams nothing either), so stream parsing is a headless-path capability and was never available here. (2) The answer is **asymmetric per adapter**, now declared as `assigns_interactive_thread_id`: Claude pre-assigns via `--session-id` fed the same id `launch.py:113` uses as Horus's run identity, so its thread id is free and knowable at launch; Codex mints its own into a rollout file and is recovered afterwards by `recover_interactive_thread_id` (correlating cwd + `originator=codex-tui` + a time window, returning None rather than guessing between two candidates). Verified against the owner's real rollout files and by a live isolated tmux launch of a real `claude`. Remaining: step 2 — make `interactive_command` resume-capable (Claude emits `--resume <id>` instead of `--session-id <id>`; Codex forwards the id it currently drops) — and step 3, the TUI restore surface. Owner decided 2026-07-30 that **existing vanished rows are NOT backfilled**: restore applies going forward only.

### 2026-07-30 — Rafael Figueiredo (manual)

2026-07-30 — **step 2 of 3 shipped in #457**: `interactive_command` now takes a `resume_id` distinct from `session_id`, because on this path the two mean opposite things — Claude's `--session-id` ASSIGNS an id (and collides if reused) while `--resume` reopens, and Codex DROPS `session_id` (it cannot pre-assign) but FORWARDS `resume_id` as the `resume` subcommand, since that one is its own id. The #456 adapter asymmetry deliberately stops at the resume boundary: a restore knows the thread id for both agents because it is the thing being reopened, so `agent_session_id` is recorded either way — otherwise a restored Codex session would return unrecorded and be unrestorable a second time. Verified live side-by-side through Horus's own argv against a real 2026-07-29 conversation: the restored pane showed genuine prior history (PRD frontmatter, `last_updated: 2026-07-29`, a real `horus close --commit --push` call with output) while a fresh pane was empty. Method note for whoever repeats it: an isolated HOME makes BOTH panes sit on Claude's first-run theme picker, which reads as failure — use the real config (the probe calls only `prepare_interactive`, which is pure, so it writes no registry row). Remaining: step 3, the TUI restore surface, plus naming the `vanished` transition in `reconcile()` gated on runner presence.

### 2026-07-30 — Rafael Figueiredo (manual)

2026-07-30 — **step 3 of 3 shipped in #458; the card's work is complete.** Detection needed no new plumbing, as the card predicted: `reconcile()` now NAMES the `vanished` transition it was already making, gated on `_records_its_own_exit` (keyed on the host registry, so old rows and future hosts are both covered) — tmux/herdr via their runner, `current` by waiting in-process, `local` not at all, so runnerless rows stay unlabelled rather than accused. The card's second open shape call — runner vs a first-class 'adopted' state — **dissolved on inspection**: both hosts already write a runnerspec for ordinary interactive launches (`tmux.py:144`, `herdr.py:326`), so the three hand-restored sessions lacked runners only because they were repaired BY HAND outside Horus. Restore is an ordinary interactive launch with one flag swapped, so it inherits the runner, a real returncode and honest liveness; no `adopted` state was introduced. `restore_session` reuses the ORIGINAL row and snapshots the delivery block, because the host reaches the row through `upsert`, which overwrites every dataclass field — the card's `update()`-over-`upsert()` warning was correct and is now enforced. A live probe caught a bug the unit tests could not: `reg` was not forwarded to `host.launch`, so a caller's registry was ignored while success was reported; the fake host accepted `**kw` and never asserted on it. Known gap, deliberate and narrow: history was visually confirmed for a direct `--resume` launch, not for a TUI-initiated restore specifically.
