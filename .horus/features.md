---
status: active
last_updated: 2026-06-26
---

# Features — capability ledger

Complete **capabilities** (shippable packages), status-tracked. A feature is a
shippable unit of behaviour, not a task — bug fixes, corrections, and chores live
in `roadmap.md` and never appear here. The action points to build a planned or
in-progress feature live in `roadmap.md`; the *why* behind a shipped one is in
`decisions.md` / `history.md`.

Status: **Shipped** · **In progress** · **Planned**

## Shipped

| Capability | Since | Notes |
|---|---|---|
| Horus companion/mascot app | 2026-06-25 | `horus app` / `horus mascot`; borderless always-on-top Tkinter mascot, transparent packaged PNG frames, idle blink/bob/real wing-frame motion, starts/detects dashboard, opens it on click, context menu includes close check + quit; launches windowless on Windows (re-exec under `pythonw.exe`, `--no-detach` opt-out) so no console lingers |
| `horus init` — scaffold `.horus/` + managed instruction blocks | — | never clobbers; injects managed block into existing AGENTS/CLAUDE |
| `horus doctor` (project + instructions) | — | continuity health + cross-ref-normalized drift check |
| `horus dashboard` — read-only multi-project view | — | next-step banner, roadmap breakdown, sessions |
| `horus session new` | — | session summary from template |
| `horus close` (git-aware) | — | verify-first closure ritual; `--commit [--push]` |
| `horus reconcile instructions` | — | deterministic within-repo managed-block sync |
| `horus forget` / `horus prune` | — | drop stale registered projects |
| PyPI distribution via Trusted Publishing | — | `uv build`/`uv publish`, OIDC, no stored token |
| `.horus/` structure v2 (6 lanes: + `features.md` + `history.md`) | — | templates, README, managed block, dashboard rendering, GFM tables in `markdown.py` |
| `horus consolidate` (agent-delegated) | — | pre-pass: roadmap↔features overlap, done-but-unshipped, sessions-to-distill + emitted routing ritual; `docs/routines.md` |
| `horus distill-history` (agent-delegated) | — | source-log detection + size signals + emitted compression ritual; `docs/routines.md` |
| Agent-skills layer (`horus-consolidate` / `-distill-history` / `-infer`) | — | bundled in `horus/skills.py`; `init` scaffolds `.claude/skills/` + `.agents/skills/`; `horus skill install`, version markers, doctor check + nudge; in-app context-aware counterparts to the CLI routines |
| `horus infer` (agent-delegated) | — | discover canonical docs + detect placeholder lanes + emit bootstrap ritual; backs the `horus-infer` skill (replaces the removed deterministic infer) |
| Codex usage/rollover closure signal | — | `horus close` + dashboard read local Codex rollout `token_count` events; warn at 90% by default before another large turn |
| Codex project-skill projection | — | `horus init` / `horus skill install --target codex` write bundled Horus skills to `.agents/skills/` alongside Claude `.claude/skills/` |
| Codex native usage hook | 2026-06-25 | `horus usage check` plus `horus hook install --target codex`; writes `.codex/hooks.json` `Stop` hook that nudges at usage threshold without failing the turn |
| Claude usage→closure hook | 2026-06-25 | `horus/claude_usage.py` reads 5h/weekly % from the OAuth `/usage` endpoint; `horus usage check --target claude`; `horus hook install --target claude` writes a `.claude/settings.json` `Stop` hook that injects the closure routine via `decision:block` at threshold (once/session) |
| Aliased account-tagged sessions | 2026-06-25 | `horus session new` records *which* account ran a session via a local alias (`config.alias_for` + `~/.horus/accounts.toml`, `acct-<sha6>` fallback); `horus account [--set]`; the real email never lands in a commit |
| Dashboard Control tab | 2026-06-26 | `/control` route + header nav (Projects ↔ Control). Control-panel layout from the design mockup: **accounts column** with live usage **donut rings** per Horus-known account (`gather_accounts` reads the `accounts.toml` config-dir map + ambient login; alias-only, best-effort OAuth `/usage`); **projects column** with a launch ▶ that reveals copyable real `horus open "<path>" [--account <alias>]` commands; **live-session cards** (running processes only, from the registry) showing status/agent/pid + the account's 5h usage bar and, for Codex sessions, context window. Read-only, stdlib-only, no JS backend beyond clipboard copy. Header **"● N live" indicator** (count of `running` sessions, on every page, links to Control) + per-card jump-to-session shortcuts (`horus focus <id>` to raise the running window; `claude --resume <id>` for a new view) |
| `horus focus <session_id>` | 2026-06-26 | Raises a running session's terminal window by PID (`launcher.focus_window_for_pid`: Toolhelp descendant-tree match + `EnumWindows` + `SetForegroundWindow`; git-style id-prefix lookup). The true "open the native app" the read-only dashboard can't do. Windows-only, best-effort (foreground lock; shared-Terminal hosting may miss → clear fallback message) |
| Dashboard launch buttons (first POST surface) | 2026-06-26 | The Control tab *launches* sessions, not just shows commands (PR #11). `POST /launch` via shared `horus/launch.py` (used by `horus open` too); same-origin-guarded, loopback-only, projects-by-index, accounts validated. Account "+ session" (fresh) + project play (Fresh / Resume-with-continuity-prompt) + a **permission-posture select** (Ask / Plan / Accept-edits / Bypass → Claude `--permission-mode`, changeable later in the TUI). action points → roadmap.md (MVP4) |
| Cross-platform PTY (`pty_session.py`) | 2026-06-26 | One byte-oriented pseudo-terminal handle: `pywinpty`/ConPTY on Windows (conditional dep), stdlib `pty` on macOS/Linux (dep-free). read/write/resize/isalive/terminate |
| In-app terminal: PTY session-host + xterm.js | 2026-06-26 | The real `claude`/`codex` TUI runs under a PTY in a persistent **session-host** (`pty_host.py`) and renders with vendored xterm.js (local, no CDN) inside the dashboard. Bytes stream over SSE (`/pty/stream`); keystrokes/resize POST back (`/pty/input`,`/pty/resize`,`/pty/kill`). Sessions persist independent of viewers → **re-attach** across tabs/reloads; **multi-viewer**. action points → roadmap.md (MVP4) |
| Terminal pop-out window | 2026-06-26 | `⤢` opens a host-owned session in its own browser window (`/pty/term`) — a second viewer of the same persistent PTY. The practical "drag out"; "drag in" = the session stays a tab to re-attach. Only for Horus-started sessions |
| Closure freshness gate (`horus close --check`) | 2026-06-26 | Deterministic detection (`routines.freshness_signals`, never authoring) that the dashboard's read-surface is current with this session: `project.md`/`roadmap.md` `last_updated` vs newest session; empty `next_action`/`next_prompt`/`current_focus`; `next_action` matching already-shipped work. `--check` exits non-zero while stale, so closure isn't "done" until the dashboard is fresh. action points → roadmap.md |
| Continuity PR check (CI) | 2026-06-26 | `.github/workflows/continuity.yml` — advisory pre-merge gate running `horus close --check` + a git heuristic ("code changed but no lane updated"); annotates, doesn't block (sessions gitignored → not on CI). The PR-boundary closure nudge |
| Codex adapter | 2026-06-26 | `horus/adapters/codex.py` (`CodexAdapter`): all four contract methods + `interactive_command`. Spawn: `codex exec --json [-m model] [sandbox-flags] <prompt>`; resume: `codex exec resume --json <session_id> [prompt]` (exec resume has no `--sandbox`; only FULL_AUTO bypass forwarded). `CODEX_HOME` per-account isolation via `[codex_homes]` in `~/.horus/accounts.toml` (`config.load_account_codex_homes()`). JSONL event parsing: `thread.started` → SESSION_STARTED (`thread_id`); `item.completed/agent_message` → ASSISTANT_TEXT; `tool_call/tool_output/approval_request` → TOOL_USE/TOOL_RESULT/PERMISSION_REQUEST; `turn.completed` → RESULT. `interactive_command` runs bare `codex [flags] [prompt]` under the PTY host; Codex has no `--session-id` pre-assignment so session_id is Horus's internal `term_id`. 23 tests; live proof confirmed (`session_started → assistant_text → result`). `get_adapter("codex")` resolves; PTY host and dashboard launch buttons work unchanged. Vendor-neutral contract proven at N=2. → roadmap.md |

## In progress

| Capability | Notes |
|---|---|
| Agent execution layer (MVP3→4) | shipped: adapter contract + `FakeAdapter` + `ClaudeAdapter` + **`CodexAdapter`** (vendor-neutral contract proven at N=2), session/process registry, multi-account isolation (Claude `CLAUDE_CONFIG_DIR` + Codex `CODEX_HOME`), `horus run` + `horus open` + in-app PTY terminal. Now genuinely multi-agent. Still open: oversight terminate/resume from UI + autonomous closure. → roadmap.md |
| Routine + skill validation on a real project | invoke on fabric in a CLI-equipped session; tune skill triggering (`claude -p`); harmonize siblings → `roadmap.md` |

## Planned

| Capability | Notes |
|---|---|
| rulesync projection to other tools | Phase 3; evaluate for broader AGENTS/CLAUDE/instruction sync beyond Horus's direct Claude/Codex skill and hook projection |
| Companion status signals | Build on the mascot: usage warning, stale session summary, uncommitted continuity, hook active/trusted state, dashboard server state |
| Autonomous routine variant (Horus spawns the agent) | the spawning half of consolidate/distill; MVP3 (now unblocked — adapters exist) |
| LLM-based `horus infer` | distill `.horus/` from canonical docs; lands with MVP3 |
