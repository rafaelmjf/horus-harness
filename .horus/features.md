---
status: active
last_updated: 2026-06-25
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

## In progress

| Capability | Notes |
|---|---|
| Agent execution layer (MVP3) | shipped: adapter contract + `FakeAdapter` + `ClaudeAdapter` (`horus/adapters/`, spawn+resume **proven live**), the **session/process registry** (`horus/registry.py`), **multi-account isolation** (per-account `CLAUDE_CONFIG_DIR` + identity check), a **live oversight dashboard** (registry view), **`horus run`** (headless one-shot, tracked), and **`horus open`** (attended: real `claude` TUI in its own terminal per account+project, tracked as a live `running` session). Next: Codex adapter, oversight controls (terminate/resume), autonomous closure |
| Routine + skill validation on a real project | invoke on fabric in a CLI-equipped session; tune skill triggering (`claude -p`); harmonize siblings → `roadmap.md` |

## Planned

| Capability | Notes |
|---|---|
| rulesync projection to other tools | Phase 3; evaluate for broader AGENTS/CLAUDE/instruction sync beyond Horus's direct Claude/Codex skill and hook projection |
| Companion status signals | Build on the mascot: usage warning, stale session summary, uncommitted continuity, hook active/trusted state, dashboard server state |
| Autonomous routine variant (Horus spawns the agent) | the spawning half of consolidate/distill; MVP3 (now unblocked — adapters exist) |
| LLM-based `horus infer` | distill `.horus/` from canonical docs; lands with MVP3 |
