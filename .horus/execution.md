---
status: active
current_feature: "Approved 2026-07-01 batch: read-only session discovery (parsers + dashboard panel), cross-machine flow guards (close fetch-first, catalog ignore-in-place), self-update pill/button, orphan-dashboard fix, archive-after-distillation"
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
delegation_basis: "Frontier supervisor + Sonnet-tier worker available on this runtime, so the delegation bar is lower (context hygiene + cheaper tier). Only phase 1 clears it: high-volume, low-ambiguity parser work against a designed contract with a pytest gate. Everything else is small or lifecycle-sensitive (process reaping, port reuse, git guards) where judgment loss dominates — direct."
last_updated: 2026-07-01
---

# Execution Plan

The 2026-07-01 approved batch. Priority order favors the user's imminent live test
(onboard on machine 1 → continue on machine 2): the cross-machine guards ship first,
session discovery runs delegated in parallel, lifecycle items follow.

## Model Policy

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting | maintainer |
| standard | narrow implementation phases with tests | worker (Sonnet-tier) |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

| phase | status | difficulty | mode | worker_tier | delegation_basis | handoff_note | review |
|---|---|---|---|---|---|---|---|
| 1-session-discovery-parsers | accepted | medium | delegated | standard | High volume (two transcript formats + fixtures + tests), low ambiguity (contract designed by supervisor below), crisp pytest gate. Worktree-isolated so direct work continues in parallel. | .horus/temp/1-session-discovery-parsers.md | ACCEPTED: supervisor reproduced 513 green in the worktree + reviewed the diff (reuses overhead/codex_usage matching, privacy rule kept). Worker flagged: Claude user/assistant type-set not checked against a real transcript — verify in phase 4. |
| 2-flow-guards | done | low | direct | — | Small git/consolidate logic; judgment > volume. Fetch-first guard on `close --push` + archive-after-distillation counting. | — | DONE: `remote_lane_divergence` + push refusal in closure.py; archive wording in ritual/skill v8; `sessions/archive/` gitignore rule; 2-clone test proves the refusal. |
| 3-ignore-in-place | done | low | direct | — | Small UI fetch+DOM change; user's eyeball is the gate. | — | DONE: delegated submit listener + `X-Horus-Fetch` → 204; non-JS keeps PRG. User to click-test after merge. |
| 4-session-discovery-panel | done | medium | direct | — | Dashboard wiring on top of phase 1's module; async `data-horus-src` pattern; UI gate is the user. | — | DONE: `/project-sessions?i=` async panel on project detail (agent/id/last-activity/msgs, max 8). Worker's Claude type-set flag resolved against a real transcript (user/assistant confirmed). User to eyeball after restart. |
| 5-self-update | done | medium | direct | — | Lifecycle-sensitive (server respawn, port reuse, owned-child reaping) — stay direct. | — | DONE: `horus/selfupdate.py` (PyPI JSON, 6h cache, offline-silent) + top-nav async pill + `/self-update` POST running `uv tool upgrade`. NO auto-restart — banner says restart Horus (no hot reload); auto-respawn deferred to MVP5 lifecycle. |
| 6-orphan-dashboard-fix | done | medium | direct | — | Lifecycle-sensitive process reaping; small volume. | — | DONE: `/health` identity endpoint + companion `_replace_stale_dashboard` — reuse only a same-version Horus server; kill stale-version (pid from /health) or legacy pre-/health Horus (pid via netstat, Windows); never touch a foreign server. User to verify quit/reopen on 8765. |

## Phase 1 contract (for the delegated worker)

New module `horus/session_discovery.py`, read-only, stdlib-only:

- `discover_claude_sessions(project_root, claude_dir=None) -> list[SessionInfo]` —
  map `project_root` to the Claude project slug dir (`~/.claude/projects/<slug>/`),
  parse `*.jsonl` transcripts. Reuse the slug/paths conventions already used by
  `horus/claude_usage.py` and `horus/cache_status.py` — do not invent a second mapping.
- `discover_codex_sessions(project_root, codex_home=None) -> list[SessionInfo]` —
  from Codex rollout files, reusing `horus/codex_usage.py` helpers where possible.
- `SessionInfo` dataclass: `agent`, `session_id`, `started_at`, `last_activity`,
  `message_count`, `cwd/project match basis`. NO transcript content beyond counts +
  timestamps (privacy rule: Horus never displays transcript content).
- Tolerant parsing: skip malformed lines/files, never raise on garbage input.
- Tests with small fixture files for both formats (happy path + malformed + empty dir).

## Worker Handoff Contract

The worker writes `.horus/temp/1-session-discovery-parsers.md` via
`horus execution handoff 1-session-discovery-parsers`: changed files, behavior,
tests run + result, risks, suggested durable `.horus/` updates. The supervisor
reproduces the gate and reviews the diff before marking accepted.

**Known pre-existing test baseline:** 503 green as of 2026-06-30; do not
misattribute a new red to an unrelated cause.
