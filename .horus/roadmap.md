---
status: active
current_focus: "MVP4 'unified terminal' is merged: the Control tab launches real agent sessions and hosts them as **in-app terminals** — the actual `claude` TUI under a PTY, rendered with xterm.js, persistent + re-attachable + pop-outable. The closure ritual was then **hardened** (branch `closure-freshness`): a deterministic freshness gate (`horus close --check`) + a sharper `horus-consolidate` skill (v3: explicit dashboard-contract checklist + per-session/backlog split) + an advisory PR continuity CI, so the dashboard's lanes can't silently go stale. The single biggest open de-risk remains the **Codex adapter** — the vendor-neutral contract is proven only at N=1 (Claude). Continuity stays the headline; resist over-building the terminal/IDE layer."
next_action: "Build the Codex adapter (horus/adapters/codex.py) against horus/adapters/base.py, with ClaudeAdapter as the reference — it proves the vendor-neutral contract (unproven at N=1) and makes the in-app terminal + launch + Control tab genuinely multi-agent. It needs interactive_command (the PTY terminal reuses it) + build_env (CODEX_HOME per account) + parse_event. Probe the real codex CLI for exec/resume flags + event-stream format; don't guess."
next_prompt: "Resume Horus. FIRST run `git fetch --all --prune` and verify branch state from the REMOTE (local refs lie — see history.md). MVP4 in-app terminal is merged: dashboard launches real claude TUIs via a cross-platform PTY (horus/pty_session.py) hosted in a persistent, re-attachable, pop-outable session-host (horus/pty_host.py), rendered with vendored xterm.js. Start a FRESH branch off main and PR it (squash-merge, auto-delete). Read .horus/ lanes + the latest .horus/sessions/ summary. Next slice: the **Codex adapter** (horus/adapters/codex.py) mirroring ClaudeAdapter — implement permission_flags/build_command/build_env(CODEX_HOME)/parse_event/interactive_command, register in adapters.get_adapter, probe the real `codex` CLI (don't guess), and confirm a Codex session launches in the in-app terminal. Also pending (own session): the continuity-debt pass (~74 done roadmap items, ~44 missing features rows, ~34 sessions to distill)."
last_updated: 2026-06-26
---

# Roadmap

## MVP 0 - Project Continuity Skeleton

- [x] Validate the initial concept against alternatives.
- [x] Reframe Horus from Telegram-first bot to project-centric continuity/control panel.
- [x] Decide `.horus/` should live inside each repo.
- [x] Choose initial `.horus/` structure: `project.md`, `roadmap.md`, `decisions.md`, `sessions/`.
- [x] Decide sessions should be local/ignored by default.
- [x] Add `AGENTS.md` and `CLAUDE.md` shared Horus-managed instruction blocks.
- [x] Define `horus init` behavior for creating `.horus/`.
- [x] Define session summary and closure templates.

## MVP 1 - Local Dashboard

- [x] Create Python package skeleton.
- [x] Build project registry that can discover configured projects and `.horus/` files.
- [x] Render a local read-only dashboard listing projects.
- [x] Show project summary, current focus, roadmap, decisions, and recent local sessions.
- [x] Surface latest change, roadmap progress, and a highlighted next step on the dashboard.
- [x] ~~Infer project state deterministically on init~~ — REMOVED 2026-06-25 (brittle parsing: truncated bullets, duplicated existing docs). `init` now scaffolds clean templates + `.horus/README.md`; rich population is the LLM-based `horus infer` under MVP3.
- [x] Add a simple `horus doctor project` check.
- [x] Add a simple `horus doctor instructions` drift check for `AGENTS.md` / `CLAUDE.md`.
- [x] Add `horus forget` / prune for stale registered projects.
- [x] Add `horus reconcile instructions` deterministic managed-block sync.

## MVP 2 - Session Continuity (file-first)

- [x] Add session summary creation/checking (`horus session new`).
- [x] Add closure verification, no agent spawned (`horus close`).
- [x] Add agent-delegated closure prompt (`horus close` prints the ritual for the in-loop agent).
- [x] Make `horus close` git-aware: work-commits-since-summary + uncommitted-continuity signals, clear verdict.
- [x] Add `horus close --commit [--push]` to stage+commit `.horus/` updates (close the multi-machine sync seam).
- [x] Surface first context-rollover signal in `horus close` and dashboard: read local Codex rollout `token_count` events and warn at `--usage-threshold` (default 90). No DB.
- [x] Add native Codex usage nudge: `horus usage check` plus `horus hook install --target codex`, which writes a `.codex/hooks.json` `Stop` hook. Hook mode prints only actionable closure warnings and exits 0.
- [x] Claude usage→closure **pre-task** trigger (2026-06-25): `hook install --target claude` now writes a **`UserPromptSubmit`** hook (fires before the agent starts a task → diverts an over-budget session to closure *instead of* starting it) plus `Stop` as a safety net. Re-armable sentinel (`REARM_SECONDS`) replaces the permanent once-per-session guard that wrongly suppressed re-fires.
- [x] Account-tagged sessions are **aliased** (2026-06-25): `current_account()` reads the logged-in email as the
  anchor, but session summaries distill upward into committed lanes, so the raw email must not appear. `config.alias_for()`
  resolves an email→alias map in `~/.horus/accounts.toml` (own file so the projects serializer can't clobber it), with a
  stable non-reversible `acct-<sha6>` fallback; `horus session new` records the alias, `horus account [--set ALIAS]` manages it.
- [ ] **Clearer session handoff / branch pickup** — IMPROVEMENT (flagged 2026-06-25 after a handoff named a branch that
  existed only on `origin`; the pickup agent trusted stale local refs and misjudged the state). Encode a fetch-first +
  verify-branch step at session pickup (done for now via `next_prompt`); consider also recording `branch:` + push/merge
  state in the session summary and surfacing it in `horus close`/dashboard. Possibly a `horus resume` command or a managed
  instruction-block step. See history.md.
- [ ] **Mid-task usage interruption (Codex-style "check between every action")** — IMPROVEMENT. `UserPromptSubmit`/`Stop` only fire at task boundaries; a single long turn can still blow past the limit. Add a `PreToolUse` hook that checks usage before each tool call (with a short ~60s cached read to avoid hammering the OAuth endpoint) and blocks → diverts to closure mid-task. Gate carefully to avoid spamming.
- [~] SQLite session/event registry + session states (`closing`/`needs_closure`/`closed_stale`) — DEFERRED. Premature at solo scale (file parsing is instant) and presupposes the deferred execution layer. Revisit when scale hurts perf or Horus runs sessions itself.

## Structure v2 - `.horus/` lanes + distillation routines (prototyping in fabric)

> Designed against `fabric-metadata-driven-medallion` as a live fixture (user-steered).
> Drift from canonical templates is intentional until the structure locks, then packaged.
> See decisions 2026-06-25 "Structure v2 + distillation routines".

File-structure (NOT LLM-dependent — done 2026-06-25):

- [x] Add `features.md` (capability ledger) + `history.md` (curated lessons) to `init` templates and `.horus/README.md`.
- [x] Update the managed instruction block (`templates.py`) to read/maintain the new lanes (dogfooded in this repo's AGENTS/CLAUDE).
- [x] Teach the dashboard to parse/surface `features.md` and `history.md` (capability badge + ledger table + collapsible history; added GFM table support to `markdown.py`).
- [ ] Propagate the updated managed block to the sibling repos (cross-repo propagation still manual; see "Later").

Distillation routines — **agent-delegated prototype shipped 2026-06-25** (pre-pass + emitted prompt, like `close`; runs on any machine with an in-loop agent). Contract in `docs/routines.md`.

- [x] **`consolidate`** — deterministic pre-pass (roadmap↔features overlap, done-but-unshipped, sessions-to-distill, missing lanes) + emitted routing ritual.
- [x] **`distill-history`** — source-log detection + size signals + emitted compression ritual.
- [ ] Autonomous variant (Horus spawns the summarizer/consolidator itself) — deferred to MVP3 with the execution layer.
- [ ] Validate the prototypes by invoking them in a CLI-equipped session on a real project (fabric) and harmonizing the siblings to structure v2.

## Native app layer - cognitive routines as in-app skills/hooks

> The files-only `horus` CLI commands are the deterministic signal layer + the
> headless/fresh-session path. The context-aware LLM parts ship as native Claude
> Code/Codex **skills** that run inside the app, so they see the live context window
> (work/decisions not yet on disk), not just the files. Periodic checks use native
> app **hooks** instead of skills. This pulls the interactive LLM routines out of
> MVP3 — the native app provides the agent runtime + subscription auth + context.
> See decisions 2026-06-25 "Cognitive Routines Ship As Claude Skills" and
> "Native App Functionality Comes Before Horus-Owned Sessions".

Phase 1 — keystone skill + plumbing (done 2026-06-25):

- [x] Author `horus-consolidate` `SKILL.md`: calls `horus consolidate` for signals,
  folds in live session context, applies routing rules to edit `.horus/**`. Content
  lives as a string in `horus/skills.py` (like `templates.py`) — ships in the wheel,
  no package-data config.
- [x] `horus init` scaffolds project skills into `.claude/skills/<name>/SKILL.md`
  and `.agents/skills/<name>/SKILL.md` (`--no-skills` opt-out; version-aware, no-clobber).
- [x] `horus skill install [--target claude|codex|all] [--user] [--force]` +
  `horus-skill-version` marker; `horus doctor` skill presence/staleness check;
  on-demand nudge from the file-only commands.
- [x] Validate `consolidate` *execution* via an independent agent (2026-06-25):
  it split correctly + flagged an unreachable verify-criterion → fixed (cross-reference
  is the split marker; `consolidate` now treats cross-referenced items as reconciled;
  skill bumped to v2). Verified end-to-end on the agent's real output (6/7 reconciled).
- [x] Validate `infer` + `distill-history` execution via independent agents
  (2026-06-25): both ran faithfully with zero invention (infer correctly *declined*
  to fabricate a decision). Fixes from their feedback: `--path` now errors on a
  nonexistent dir (was silent exit 0); `history.md` placeholder check is reachable
  (template-body compare, not a required `##`); `infer` surfaces empty `decisions.md`
  gently; infer/distill skills → v2 (already-distilled source, pointer placement,
  size heuristic, forward roadmap-shaped content, no-pointer-if-canonical).
- [ ] Triggering eval follow-up: `claude /login` was completed in the previous session;
  direct `claude -p` probing confirmed real skill triggering works, but the
  skill-creator `run_eval` proxy appeared incompatible with Claude Code 2.1.191 and
  the custom real-mechanism harness had not produced a final matrix before handoff.

Phase 2 — rest of the cognitive layer (done 2026-06-25):

- [x] `horus-distill-history` skill (calls `horus distill-history`).
- [x] `horus-infer` skill — LLM bootstrap of `.horus/` from canonical docs. Was
  MVP3-deferred only for lack of an LLM; now an in-app skill. Added the `horus infer`
  CLI backend (discover canonical docs + detect placeholder lanes) as its signal layer.

Phase 3 — portability (started with direct Codex skill projection):

- [x] Direct Codex project-skill projection: use Codex's native repo skill location
  `.agents/skills/` for the bundled Horus skills. This is simpler than `rulesync` for
  Horus's own skills because both Claude and Codex consume `SKILL.md`.
- [x] Direct Codex hook projection: install `.codex/hooks.json` with a `Stop` hook
  for usage rollover warnings (`horus usage check --hook`). Skills do the closure
  work; hooks decide when to nudge.
- [x] Claude Code usage→closure parity (2026-06-25): `horus/claude_usage.py` reads the
  5h/weekly % from the OAuth `/usage` endpoint (`GET /api/oauth/usage`); `horus usage
  check --target claude` + `horus hook install --target claude` install a `Stop` hook
  that injects the closure routine via `{"decision":"block","reason":…}` at threshold,
  once per session. Dogfooded into this repo's `.claude/settings.json`.
- [x] OAuth token auto-refresh (2026-06-25): the on-disk `accessToken` is routinely
  stale between runs (Claude Code refreshes in-process), which made the hook go dark
  and never fire. `_oauth_token()` now refreshes an expired token from `refreshToken`
  via `POST https://api.anthropic.com/v1/oauth/token` (client_id
  `9d1c250a-…`, CLI `User-Agent` to clear Cloudflare 1010) and persists the rotated
  pair. Refresh tokens are single-use — always persist or the next refresh 400s.
- [ ] Evaluate `rulesync` for broader sync/projection — folded into the dedicated
  "Cross-tool interface sync" milestone track below (the 3rd-target trigger).

## Native-app-first feature design

- [x] Record the product rule: for every new Horus feature, define the native Claude
  Code/Codex behavior first (instructions, skills, hooks, repo config), then decide
  whether Horus-owned sessions are needed.
- [ ] Add this lens to future feature specs: "native Claude path", "native Codex path",
  "Horus-owned/session path if needed".

## Companion app / mascot - visible Horus presence (next)

Intent: make Horus feel active without prematurely owning agent sessions. The first
app slice should be a tiny always-on-top companion that acts as a doorway to the
dashboard and later becomes the place for continuity/status nudges.

- [x] Choose the lightest viable desktop shell for Windows-first development
  (Python/Tk, PySide, Tauri, or another small option) with packaging implications
  noted before building.
- [x] Add `horus app` (or `horus mascot`) to start/detect the local dashboard and
  show a small always-on-top mascot/status bubble.
- [x] Replace the placeholder drawing with the packaged pixel mascot image and
  remove window chrome/taskbar decoration.
- [x] Add subtle idle animation (blink/bob/wing motion) so the mascot does not
  feel frozen.
- [x] Replace the wing overlay with real transparent PNG animation frames generated
  from the mascot image; runtime remains Pillow-free.
- [x] Clicking the mascot opens the dashboard at `http://127.0.0.1:8765`.
- [x] Open the dashboard as a chromeless **app-mode window** (Edge/Chrome `--app=`),
  not a browser tab, so it reads as a companion app (2026-06-25). `companion.open_dashboard`
  prefers app-mode, falls back to a tab. Upgrade path: PySide/pywebview for a true
  native window + taskbar identity.
- [x] Fix console-window strobing on dashboard refresh (2026-06-25): `gitstate` git
  subprocesses now pass `CREATE_NO_WINDOW` on Windows (the overview fires many git
  calls per refresh).
- [x] Single-instance companion (2026-06-25): `acquire_singleton_lock` binds a fixed
  localhost port (8764) as a process-lifetime mutex; a second `horus app` exits
  instead of stacking another mascot. OS releases it on death (no stale-PID files).
- [ ] **BUG: the dashboard *server* (8765) leaks — not covered by the singleton**
  (found 2026-06-25: 13 orphaned `horus dashboard` processes on one machine). The
  8764 mutex guards only the mascot; the dashboard subprocess has no single-instance
  guard and isn't reaped when the companion dies, so launches/restarts accumulate
  servers. Whichever bound the port first keeps serving its **old in-memory build**
  (Python doesn't hot-reload), so the dashboard shows stale UI/values after code
  changes until every orphan is killed. Fix: before spawning, detect a healthy
  `horus dashboard` already on 8765 and reuse it (or make the server single-instance
  the same way), and have the companion terminate its dashboard child on exit.
- [x] Add a minimal context menu: Open Dashboard, Run Close Check, Quit.
- [x] Show a basic status indicator: neutral/ok, warning, needs-closure. Initial
  data can come from existing `doctor`/`close`/usage checks; no live registry yet.
- [x] Keep it optional and local-only; Horus must still work as CLI + files when
  the companion is not running.
- [x] Fix app launch so no terminal window remains open when the companion starts
  from a user-facing shortcut or command. (2026-06-25) `horus app` now re-execs
  under `pythonw.exe` detached on Windows (`companion.relaunch_without_console`,
  `HORUS_DETACHED` loop guard, `--no-detach` opt-out). Trade-off: the detached
  child has no console, so a GUI startup failure is currently silent — log-file /
  error-dialog fallback is a follow-up if it bites.
- [x] Improve the wing animation beyond the current simple transparent-frame
  flap; make it feel integrated with the mascot rather than mechanically shifted.
  (2026-06-25) idle_1/idle_2 now lift the green wing a few px over the body (no
  tear: vacated strip shows the body behind), and `animate()` eases
  rest→lift→peak→lift→rest.
- [x] Replace or regenerate the mascot asset if cleaner than cutting the current
  image: remove white fringe pixels around the silhouette, but preserve intentional
  white regions such as the hat. (2026-06-25) `scripts/regen_mascot.py` defringes
  (peels near-white edge pixels touching transparency; interior whites survive)
  + drops keying specks. All 5 frames regenerated; runtime stays Pillow-free.
- [ ] Later: surface native hook events, usage threshold warnings, stale summaries,
  uncommitted continuity, and per-project switching.

- [x] `test_claude_usage.py::test_findings_ok_when_unavailable` non-hermeticity fixed
  (2026-06-25): the test now stubs `latest_usage` to `None`, so it no longer warns on a
  logged-in machine whose 5h window is over threshold.

## MVP 2.5 - Git-aware multi-project overview (next)

> Goal: a trustworthy overview of all projects from any machine. Decided
> 2026-06-25 (see decisions "Git Is The Cross-Machine Transport"): git already
> carries the durable lanes (project/roadmap/decisions/features/history), so the
> overview needs no server, no session hosting, no Tailscale. The gap is that the
> dashboard reads local clones with **no freshness signal** — so make it git-aware.
> Config stays per-machine (paths are local); sessions stay local and distill into
> the committed lanes. Deterministic signal layer only (no LLM), like `doctor`/`close`.

- [x] `horus/gitstate.py` (2026-06-25): best-effort git signals for a repo via
  subprocess — branch, last commit (short hash + relative time + subject), dirty
  (uncommitted y/n), behind/ahead vs upstream **from existing refs** (no implicit
  network), remote URL. Non-repo → None, never raises. CLI peer `horus status`
  reuses `dashboard.load_project`; self-check in `__main__`.
- [x] Surface freshness on the dashboard (2026-06-25): overview cards get a compact
  git badge (branch · last-commit-rel · ↓behind ↑ahead · uncommitted), yellow when
  stale; the project detail view gets a full **Git** card (commit, up-to-date /
  behind-with-`git pull --ff-only` / no-upstream, dirty, remote URL).
- [x] Latest session summary rendered in full on the detail view (2026-06-25): the
  goal of the slice — a prominent "Latest session" card showing the newest local
  session body, with a filename fallback on the overview when frontmatter has no summary.
- [x] Overview redesigned to per-project **columns** (2026-06-25, from user draft):
  each column = name + "why this exists" one-liner + Last-session-summary box +
  Roadmap box (highlighted next item, ▶ Start-a-session CTA, Remaining-top-items) +
  Main-features in Idea/In-progress/Shipped buckets with names (`routines.feature_items`).
  Pills kept (status, sessions, git, health).
- [ ] "Fetch all" refresh action: `git fetch` across registered projects to update
  behind/ahead. Fetch does not touch the working tree, so the dashboard's
  read-only-on-files invariant holds. Pull (which mutates) is NOT auto-run.
- [ ] Fold staleness into the existing warning/verdict surface (reuse `close`'s
  uncommitted-`.horus/` check): "behind origin — pull to refresh" / "uncommitted
  continuity". Show the exact `git pull --ff-only` command rather than a button.
- [ ] Defer: a one-click pull endpoint (breaks read-only-files invariant — add only
  if showing the command proves too much friction).
- [ ] Optional ops, no code: document `tailscale serve` of the read-only dashboard so
  phone/laptop can glance at *that machine's* view over the tailnet.
- [ ] Optional, YAGNI for now: store each project's remote URL in the registry so the
  same project can be recognized across machines (only if cross-machine dedup is wanted).

## MVP 3 - Agent Execution (the core wedge; next major phase)

> No longer deferred: `claude` 2.1.191 is installed AND logged in on this machine, so
> the subprocess-driving layer is now end-to-end testable here (was the only blocker).
>
> Locked decisions (2026-06-25): build order = spawn + registry FIRST, then the live
> oversight app. First real adapter = Claude Code. Thin owned adapter against a shared
> contract; a fake adapter can validate orchestration anywhere. This phase also unlocks
> autonomous closure + agent-assisted infer.

- [x] Define the adapter contract (`spawn`, `resume`, `parse_event`, `permission_flags`) + a fake adapter for tests
  (2026-06-25). `horus/adapters/`: `base.py` is the contract — `AgentAdapter` ABC with four pure methods
  (`permission_flags`/`build_command`/`build_env`/`parse_event`) plus shared `spawn`/`resume`, subprocess streaming,
  and `AgentRun` session-id/status tracking; `SpawnSpec`/`AgentSession`/`AgentEvent`/`PermissionPosture`/`EventType`
  normalize the I/O. `fake.py` (`FakeAdapter`) implements the whole contract in memory via a JSON-lines stream that
  mirrors stream-json's shape, so orchestration is testable with no CLI. `get_adapter(name)`. 12 tests.
- [x] **Claude Code adapter** (2026-06-25). `horus/adapters/claude.py` (`ClaudeAdapter`): fills the four pure methods
  against the contract — `claude -p --output-format stream-json --verbose`, `--resume <id>`, posture→`--permission-mode`
  (PLAN/READ_ONLY→plan, AUTO_EDIT→acceptEdits, FULL_AUTO→bypassPermissions), `--model`, comma-joined
  `--allowedTools`/`--disallowedTools`, `CLAUDE_CONFIG_DIR` per account. `parse_event` maps the real 2.1.191 stream-json
  (system/init→SESSION_STARTED carrying the id; assistant text/tool_use; user tool_result; result; ignores
  rate_limit_event/thinking_tokens/post_turn_summary). Contract refined: `parse_event` now returns a **list** (one
  assistant line can carry text+tool_use); base sets `stdin=DEVNULL` (skips Claude's 3s stdin wait). 10 tests on real fixtures.
- [x] **Spawn + resume one headless session, capture output, track state** (2026-06-25) — PROVEN LIVE on this machine:
  spawn returned "STORED" + session id; resume of that id recalled "42" from the first turn (context carried across a
  fresh process); status/returncode tracked. The MVP3 first proof point.
- [x] **Session/process registry** (2026-06-25). `horus/registry.py` — `Registry` over
  `~/.horus/registry.json` (file-first, machine-local since it tracks PIDs), records keyed by
  session_id with exactly the `AgentSession` shape. `SessionRecord.from_session` bridges the adapter;
  `track(registry, run)` registers on first id + records final status while passing events through;
  `reconcile()` corrects stale `running` records via cross-platform `process_alive` (POSIX `os.kill(.,0)`;
  Windows `OpenProcess`+`WaitForSingleObject` — never `os.kill`, which terminates on Windows); `prune()`;
  `horus sessions [--prune]` CLI. 10 tests. SQLite stays the later step (below) if scale/concurrency demands it.
- [x] **Multi-account isolation** (2026-06-25). `accounts.toml` gained a `[config_dirs]` section
  (alias→`CLAUDE_CONFIG_DIR`, preserved alongside `[aliases]`); `ClaudeAdapter` defaults its `config_dirs`
  from `config.load_account_config_dirs()` and sets `CLAUDE_CONFIG_DIR` per account. Startup identity check:
  `verify_account()` reads `<config_dir>/.claude.json` and confirms its email aliases back to the requested
  account; `_launch` raises `AccountMismatch` (before any subprocess) when a mapped account's login doesn't
  match. `horus account --set-dir [--alias-name]` manages the map and surfaces it. 10 tests.
- [x] **Live oversight dashboard** (2026-06-25, status view). The dashboard now reconciles
  `horus/registry.py` on load and renders a "Live sessions" card (status dot + agent/account/
  project/pid/session/updated) on the index, plus a `/sessions` route. Read-only invariant kept.
- [x] **`horus run` launch command** (2026-06-25) — the glue that makes a user-facing test run
  possible: spawn (or `--resume`) an agent session via the adapter, `track()` it into the registry
  (so it shows in `horus sessions` + the dashboard), stream events to stdout. `--agent/--account/
  --model/--posture/--resume/--path`. Also made `claude_usage` account detection `CLAUDE_CONFIG_DIR`-aware
  so `horus account` can see a second account. Fixed a latent multi-account bug from PR #6: config-dir
  paths with Windows backslashes broke TOML parsing → silently empty map; now stored forward-slashed.
- [x] **`horus open` — attended interactive sessions** (2026-06-26). Opens the real `claude`
  TUI in its own terminal window (Windows `CREATE_NEW_CONSOLE`, so the returned PID is the
  child's and dies on exit), under a chosen account (`CLAUDE_CONFIG_DIR`) + project (cwd), with a
  pre-assigned `--session-id` so it's tracked before any output. Registers a **`running`** record
  → the dashboard finally shows live sessions, not just finished ones. `horus/launcher.py`;
  `ClaudeAdapter.interactive_command`; same identity guard as headless. Proven live: two windows
  (work/horus-harness, personal/agentic-ttrpg) tracked running across two accounts. 3 tests.
- [~] **Oversight controls**: actions on a tracked session from the dashboard. The **POST surface
  shipped** (PR #11 — `/launch`, same-origin-guarded, loopback-only; → features.md), which was the
  blocker. Still open: terminate/resume of a *windowed* session from the UI (in-app PTY terminals
  already have kill via `/pty/kill`). CLI `horus sessions --prune` covers cleanup today.
  - [x] **Live-session indicator + reopen shortcut** (2026-06-26, branch `feat/control-tab-ui`): a
    header "● N live" badge (count of `running` registry records, links to Control, on every page) and a
    per-card copyable `cd <project>; claude --resume <id>` "reopen in a native window". Stays read-only —
    a browser can't raise a desktop window.
  - [x] `horus focus <session_id>` (2026-06-26) — OS-level raise of a running session's terminal.
    `launcher.focus_window_for_pid`: matches the pid's whole descendant tree (Toolhelp snapshot, so a
    child `conhost` counts) against visible top-level windows (`EnumWindows`) and `SetForegroundWindow`s
    the first. Id-prefix lookup like git hashes. Surfaced on the live cards as "raise the running window".
    **Bug caught only by live-testing** (history.md): ctypes defaults handle args to 32-bit int → 64-bit
    HWND/HANDLE truncation made it silently no-op; fixed by declaring `argtypes`/`restype`. Ceilings:
    Windows-only; `SetForegroundWindow` is subject to the OS foreground lock; a session hosted in a shared
    Windows Terminal process (window not a pid descendant) won't match → clear failure message + fallback.
- [ ] **Codex adapter (THE next step)** — second adapter to prove the vendor-neutral contract,
  unproven at N=1. `horus/adapters/codex.py` mirroring `ClaudeAdapter`: `permission_flags` /
  `build_command` / `build_env` (`CODEX_HOME` per account) / `parse_event` / `interactive_command`
  (the in-app PTY terminal reuses it), registered in `adapters.get_adapter`. Probe the real `codex`
  CLI for exec/resume flags + event format; don't guess. → unblocks multi-agent terminal/launch.
- [ ] Persist the registry in SQLite (re-justified once concurrency/scale hurts; JSON file shipped first).
- [ ] Restrict autonomous closure edits to `.horus/**`, `AGENTS.md`, `CLAUDE.md`.
- [ ] **LLM-based `horus infer`** (replaces the removed deterministic version): drive the official CLI to distill `.horus/` from the project's canonical docs — follow doc pointers (README → status/roadmap → CLAUDE.md → linked docs like docs/HISTORY.md), produce clean project + roadmap with planned/in-progress/done items, mark superseded source docs as stale, and prompt the user when intent is unclear.

## MVP 4 - Unified in-app terminal (the cockpit)

> Shipped this milestone: the Control tab launches real sessions and hosts them as
> in-app terminals (the real agent TUI under a PTY, rendered with xterm.js). Decided
> 2026-06-26: keep the viewer in Horus (not a VS Code extension), local + persistent +
> re-attachable, cross-platform PTY. See features.md for the capabilities and
> decisions.md ("Unified in-app terminal", "Cross-platform PTY") for the why.

- [x] Dashboard **launch buttons + first POST surface** (PR #11): `/launch` via shared
  `horus/launch.py`; same-origin-guarded, loopback-only, projects-by-index. → features.md
- [x] **Cross-platform PTY** (`pty_session.py`): `pywinpty` (Windows, conditional dep) +
  stdlib `pty` (macOS/Linux, dep-free). → features.md
- [x] **Persistent session-host** (`pty_host.py`) + **xterm.js** viewer (vendored, no CDN):
  real TUI in-app, scrollback replay, re-attach across tabs/reloads, multi-viewer. → features.md
- [x] **Pop-out** a session into its own window (a second viewer of the same host-owned PTY). → features.md
- [ ] **Codex in the terminal** — falls out of the Codex adapter (above); the PTY host already
  calls `interactive_command`, so it works once Codex implements it.

Deferred (noted as future direction, low value for now):

- [ ] **Standalone session-host daemon** — survive a Horus *restart* (today re-attach only
  spans tabs/reloads while the dashboard process runs).
- [ ] **Remote / cross-machine attach** — run the host per machine, attach over a tailnet with
  auth (Tailscale was already reserved for live state). Protocol kept transport-agnostic for this.
- [ ] **Monitor sessions Horus did NOT start** (read-only) — discover foreign `claude`/`codex`
  sessions from the transcripts they already write (`~/.claude/projects/<slug>/<uuid>.jsonl`;
  Codex rollouts already read by `codex_usage`), surfacing project/last-activity/message-count.
  Plus a "continue this here" bridge via `claude --resume <id>` into a Horus-owned PTY. Cannot
  *attach/drive* a foreign PTY — observe only. Optional process-scan layer (cwd→project) wants psutil.
- [ ] Literal OS-level drag gestures / re-dock automation (pop-out covers the practical need).
- [ ] Register in-app PTY terminals in the registry so `horus sessions` / usage cards see them.

## Cross-tool interface sync (Claude ↔ Codex ↔ Gemini CLI ↔ Copilot …)

> The differentiator is NOT a new converter — `rulesync` already projects rules/skills/
> commands/MCP across 20+ tools. Horus splits this into two layers and only *owns* the one
> that's inherently its own. See decisions 2026-06-25 "rulesync: stay direct at two tools;
> own the behavioral layer always" and the `codex-plan-review.md` compatibility section.
>
> - **Layer 1 — artifact projection** (instructions, `SKILL.md`, commands, MCP): commodity;
>   `rulesync` does it. Horus stays direct/zero-dep at two tools, adopts rulesync at the 3rd.
> - **Layer 2 — behavioral/semantic adapters** (hook control protocol per tool; usage-signal
>   *source* per tool; per-account config-dir env var): inherently Horus's; never portable.
>   This is where the value is and Horus owns it regardless.

Already shipped (Claude + Codex): dual-write `SKILL.md` to `.claude/skills/` + `.agents/skills/`;
`reconcile instructions` for the `AGENTS.md`↔`CLAUDE.md` managed block; per-tool usage→closure
hooks (Claude OAuth `/usage` + `decision:block`; Codex rollouts + `Stop`).

- [ ] **`horus doctor compat` (observe first)** — per project, report what *each* installed agent
  (claude/codex/gemini/copilot) would actually load: which instruction files, skills, MCP, hooks.
  Read-only; solves the real pain ("which instructions/skills are active here, for this agent?").
- [ ] **Canonical + projections, formalized** — `.horus/compat.toml` declares canonical surfaces
  (`AGENTS.md`, `.agents/skills/`) + per-target projection policy; generated `CLAUDE.md` /
  `.claude/skills/` are marked-generated with drift detection. Extends today's ad-hoc dual-write.
- [ ] **3rd/4th target via rulesync (trigger: Gemini CLI / Copilot)** — shell out to / document
  `rulesync` for Layer-1 projection (`GEMINI.md`, `.cursor/rules`, `.github/instructions/…`),
  never embed (it's npm/Node). Horus wraps it with provenance, diff-before-install, and trust UX.
- [ ] **Per-tool behavioral adapters (Layer 2)** — as each agent gets an execution adapter, add its
  usage-signal source + hook control protocol + config-dir env var (Claude `CLAUDE_CONFIG_DIR`,
  Codex `CODEX_HOME`, …). Pairs 1:1 with the adapter work in MVP3/4.
- [ ] **Skill-projection security/trust** — provenance, diff before install/update, explicit trust
  per project/account, warn on scripts/hooks/MCP/auto-approve, never silently install a
  personal-sourced skill into a work account (projecting into N agents multiplies blast radius).

## Closure ritual hardening (shipped 2026-06-26)

> Why: lanes drifted (stale `current_focus`, growing backlog) despite the ritual
> running several times. Fix keeps LLM-authors / Python-detects. See features.md
> ("Closure freshness gate", "Continuity PR check") + decisions.md.

- [x] **`horus close --check`** freshness gate (`routines.freshness_signals` +
  `closure.freshness_gate`) — non-zero while a dashboard field is stale. → features.md
- [x] **`horus-consolidate` skill v3** — explicit dashboard-contract checklist +
  per-session-close vs backlog-consolidation split (the structural reason the ritual
  got half-done). Mirrored in `templates.py` CLOSURE_PROMPT.
- [x] **Advisory PR continuity CI** (`.github/workflows/continuity.yml`) — the
  pre-merge closure nudge. → features.md
- [ ] Promote the CI check from advisory to a required gate once proven (drop the
  `|| echo ::warning::` fallbacks).

## Later

- [ ] **One-time continuity-debt paydown (now tooled).** The drift backlog: `horus
  consolidate` reports ~39 roadmap↔features overlaps, ~44 done items without a
  `features.md` row, ~35 sessions to distill. Now a clean, supported job (skill v3's
  "backlog consolidation" mode + `horus close --check` to verify). Distill old sessions,
  move shipped capabilities into `features.md`, cross-reference each split, prune done
  roadmap items — so the freshly-hardened ritual starts from a clean baseline. Sizable;
  dedicated pass, not mid-feature.
- [ ] Optional Telegram bridge.
- [ ] Optional Tailscale-exposed dashboard.
- [ ] Optional VM/worker mode.
- [ ] Optional `rulesync` integration.
- [ ] Optional `horus reconcile instructions --ai`.
- [ ] Optional private session sync outside git.
- [ ] Propagate managed-block content updates across repos when Horus's canonical block changes (currently no mechanism; `reconcile` only syncs the two files within one repo).
