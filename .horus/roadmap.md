---
status: active
current_focus: "MVP0/MVP1 shipped (init, doctor, dashboard, session/close, reconcile). Next: MVP2 session registry and context-rollover."
last_updated: 2026-06-24
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
- [x] Add a simple `horus doctor project` check.
- [x] Add a simple `horus doctor instructions` drift check for `AGENTS.md` / `CLAUDE.md`.
- [x] Add `horus forget` / prune for stale registered projects.
- [x] Add `horus reconcile instructions` deterministic managed-block sync.

## MVP 2 - Session Continuity

- [ ] Add SQLite registry for sessions and events.
- [ ] Define session states including `closing`, `needs_closure`, and `closed_stale`.
- [x] Add session summary creation/checking (`horus session new`).
- [x] Add closure verification, no agent spawned (`horus close`).
- [x] Add agent-delegated closure prompt (`horus close` prints the ritual for the in-loop agent).
- [ ] Add stale-session closure thresholds.
- [ ] Add context rollover heuristics.

## MVP 3 - Agent Execution

> Deferred: Claude Code / Codex apps already allow running both from the same project folder by hand, so multi-session execution is not blocking. This phase also unlocks the autonomous (non-delegated) closure summarizer.


- [ ] Add concrete account config for Codex.
- [ ] Implement Codex adapter command building.
- [ ] Start and resume a real Codex session.
- [ ] Associate sessions with project/account/environment.
- [ ] Restrict closure mode to `.horus/**`, `AGENTS.md`, and `CLAUDE.md`.
- [ ] Add Claude adapter after Codex flow is proven.

## Later

- [ ] Optional Telegram bridge.
- [ ] Optional Tailscale-exposed dashboard.
- [ ] Optional VM/worker mode.
- [ ] Optional `rulesync` integration.
- [ ] Optional `horus reconcile instructions --ai`.
- [ ] Optional private session sync outside git.
