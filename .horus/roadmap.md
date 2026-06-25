---
status: active
current_focus: "Claude Code usage→closure parity shipped (reads 5h/weekly % via OAuth /usage endpoint; Stop hook injects the closure routine at threshold). Next: real-world validation when a limit actually hits ~90%, then companion status signals / mascot polish."
last_updated: 2026-06-25
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
- [ ] Evaluate `rulesync` for broader sync/projection (AGENTS/CLAUDE plus other tools),
  where it may still subsume or complement `horus reconcile`.

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
- [x] Add a minimal context menu: Open Dashboard, Run Close Check, Quit.
- [x] Show a basic status indicator: neutral/ok, warning, needs-closure. Initial
  data can come from existing `doctor`/`close`/usage checks; no live registry yet.
- [x] Keep it optional and local-only; Horus must still work as CLI + files when
  the companion is not running.
- [ ] Fix app launch so no terminal window remains open when the companion starts
  from a user-facing shortcut or command.
- [ ] Improve the wing animation beyond the current simple transparent-frame
  flap; make it feel integrated with the mascot rather than mechanically shifted.
- [ ] Replace or regenerate the mascot asset if cleaner than cutting the current
  image: remove white fringe pixels around the silhouette, but preserve intentional
  white regions such as the hat.
- [ ] Later: surface native hook events, usage threshold warnings, stale summaries,
  uncommitted continuity, and per-project switching.

## MVP 3 - Agent Execution (the core wedge; next major phase)

> DEFERRED until working on a machine with the official CLIs installed + logged in.
> `claude`/`codex` are not present on the current machine, so the subprocess-driving
> layer can't be end-to-end tested here. Approach is locked below so resumption is clean.
>
> Locked decisions (2026-06-25): build order = spawn + registry FIRST, then the live
> oversight app. First real adapter = Claude Code. Thin owned adapter against a shared
> contract; a fake adapter can validate orchestration anywhere. This phase also unlocks
> autonomous closure + agent-assisted infer.

- [ ] Define the adapter contract (`spawn`, `resume`, `parse_event`, `permission_flags`) + a fake adapter for tests.
- [ ] Session/process registry: `(agent, account, project, environment, pid, session_id, status)`; survives restarts.
- [ ] Claude Code adapter: `claude -p --output-format stream-json`, `--resume`, `CLAUDE_CONFIG_DIR` per account, permission posture.
- [ ] Spawn + resume one headless session in a project under a chosen account; capture output; track state.
- [ ] Multi-account isolation via per-account home dirs (`CLAUDE_CONFIG_DIR`) + startup identity check.
- [ ] Codex adapter (second) to prove the abstraction.
- [ ] Turn the static dashboard into a live oversight app (process status + controls) on top of the registry.
- [ ] Persist the registry in SQLite (now re-justified: real live processes to track).
- [ ] Restrict autonomous closure edits to `.horus/**`, `AGENTS.md`, `CLAUDE.md`.
- [ ] **LLM-based `horus infer`** (replaces the removed deterministic version): drive the official CLI to distill `.horus/` from the project's canonical docs — follow doc pointers (README → status/roadmap → CLAUDE.md → linked docs like docs/HISTORY.md), produce clean project + roadmap with planned/in-progress/done items, mark superseded source docs as stale, and prompt the user when intent is unclear.

## Later

- [ ] Optional Telegram bridge.
- [ ] Optional Tailscale-exposed dashboard.
- [ ] Optional VM/worker mode.
- [ ] Optional `rulesync` integration.
- [ ] Optional `horus reconcile instructions --ai`.
- [ ] Optional private session sync outside git.
- [ ] Propagate managed-block content updates across repos when Horus's canonical block changes (currently no mechanism; `reconcile` only syncs the two files within one repo).
