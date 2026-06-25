---
status: active
current_focus: "First Codex usage/rollover warning shipped via read-only rollout telemetry in `horus close` + dashboard. Next: consolidate this repo's own .horus lanes, then continue toward MVP3 adapter/registry work."
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

## Skills layer - cognitive routines as in-app skills (Claude-first)

> The files-only `horus` CLI commands are the deterministic signal layer + the
> headless/fresh-session path. The context-aware LLM parts ship as native Claude
> Code **skills** that run inside the app, so they see the live context window (work
> /decisions not yet on disk), not just the files. This pulls the interactive LLM
> routines out of MVP3 — the native app provides the agent runtime + subscription
> auth + context. See decisions 2026-06-25 "Cognitive Routines Ship As Claude Skills".

Phase 1 — keystone skill + plumbing (done 2026-06-25):

- [x] Author `horus-consolidate` `SKILL.md`: calls `horus consolidate` for signals,
  folds in live session context, applies routing rules to edit `.horus/**`. Content
  lives as a string in `horus/skills.py` (like `templates.py`) — ships in the wheel,
  no package-data config.
- [x] `horus init` scaffolds project skills into `.claude/skills/<name>/SKILL.md`
  (`--no-skills` opt-out; version-aware, no-clobber).
- [x] `horus skill install [--user] [--force]` + `horus-skill-version` marker; `horus
  doctor` skill presence/staleness check; on-demand nudge from the file-only commands.
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
- [ ] Triggering eval (skill-creator description-optimization, `claude -p`) — BLOCKED:
  `claude` CLI is installed (`~/.local/bin/claude.exe`, on PATH now) but **not logged
  in** (`claude /login` needed); harness auth ≠ CLI auth. Needed to tune skill triggering.

Phase 2 — rest of the cognitive layer (done 2026-06-25):

- [x] `horus-distill-history` skill (calls `horus distill-history`).
- [x] `horus-infer` skill — LLM bootstrap of `.horus/` from canonical docs. Was
  MVP3-deferred only for lack of an LLM; now an in-app skill. Added the `horus infer`
  CLI backend (discover canonical docs + detect placeholder lanes) as its signal layer.

Phase 3 — portability (deferred behind Claude-first):

- [ ] rulesync projection/import for Codex + other tools (rulesync supports skills
  natively for Claude Code and "simulates" Codex via `.codex/skills/`). Author native
  `SKILL.md` now (no coupling); project later. Decide if it also subsumes `reconcile`.

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
