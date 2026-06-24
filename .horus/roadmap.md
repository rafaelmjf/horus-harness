---
status: active
current_focus: "Bootstrap repo-local project continuity, then build the smallest dashboard around it."
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
- [ ] Define `horus init` behavior for creating `.horus/`.
- [ ] Define session summary and closure templates.

## MVP 1 - Local Dashboard

- [ ] Create Python package skeleton.
- [ ] Build project registry that can discover configured projects and `.horus/` files.
- [ ] Render a local read-only dashboard listing projects.
- [ ] Show project summary, current focus, roadmap, decisions, and recent local sessions.
- [ ] Add a simple `horus doctor project` check.
- [ ] Add a simple `horus doctor instructions` drift check for `AGENTS.md` / `CLAUDE.md`.

## MVP 2 - Session Continuity

- [ ] Add SQLite registry for sessions and events.
- [ ] Define session states including `closing`, `needs_closure`, and `closed_stale`.
- [ ] Add session summary creation/checking.
- [ ] Add closure ritual prompt and verification.
- [ ] Add stale-session closure thresholds.
- [ ] Add context rollover heuristics.

## MVP 3 - Agent Execution

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
