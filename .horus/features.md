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
| Agent-skills layer (`horus-consolidate` / `-distill-history` / `-infer`) | — | bundled in `horus/skills.py`; `init` scaffolds `.claude/skills/`; `horus skill install`, version markers, doctor check + nudge; in-app context-aware counterparts to the CLI routines |
| `horus infer` (agent-delegated) | — | discover canonical docs + detect placeholder lanes + emit bootstrap ritual; backs the `horus-infer` skill (replaces the removed deterministic infer) |
| Codex usage/rollover closure signal | — | `horus close` + dashboard read local Codex rollout `token_count` events; warn at 90% by default before another large turn |

## In progress

| Capability | Notes |
|---|---|
| Routine + skill validation on a real project | invoke on fabric in a CLI-equipped session; tune skill triggering (`claude -p`); harmonize siblings → `roadmap.md` |

## Planned

| Capability | Notes |
|---|---|
| rulesync projection to Codex / other tools | Phase 3; native Claude skill → simulated `.codex/skills/` |
| Autonomous routine variant (Horus spawns the agent) | the spawning half of consolidate/distill; MVP3 |
| Agent execution layer (Claude adapter, spawn+registry, live oversight) | MVP3; deferred until a CLI-equipped machine |
| LLM-based `horus infer` | distill `.horus/` from canonical docs; lands with MVP3 |
