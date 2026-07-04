---
status: active
current_feature: "Hub pre-work batch: D structured run-log event stream (codex GPT-5.5) + E horus run worktree/posture ergonomics (claude/work Opus 4.8) — the two seams horus-hub consumes, run under the skill-v8 orchestration contract."
supervisor_tier: frontier
worker_tier: frontier (feature supervisors)
continuity_tier: economy
delegation_basis: "Second orchestration batch under skill v8. Two bounded, parallelizable slices with crisp gates and disjoint surfaces; both are prerequisites the hub's read model (D) and launch path (E) build on. Orchestrator (this session) plans/routes/accepts on deterministic signals, implements nothing; lessons from the pilot pre-applied: claude worker spawns full-auto from the start; codex brief carries a sandbox-runnable gate."
last_updated: 2026-07-04
---

# Execution Plan — hub pre-work

Two workers, two worktrees, wave of one. Merge sequencing per skill v8: after the
first PR lands, watch main's push CI before arming the second.

## Active Phases

| phase | status | difficulty | mode | worker_agent | worker_tier | delegation_basis | handoff_note | review gate |
|---|---|---|---|---|---|---|---|---|
| D-runlog-events | merged (PR #113; orchestrator reproduced 746 green + live probe; zero bounces; main push CI green post-merge) | medium | delegated | codex (auto-edit, read-only .git — orchestrator owns commit/PR) | frontier | Backend seam with a crisp pytest gate; hub Phase 2 consumes run logs — harden before building on it | `.horus/temp/D-runlog-events.md` (worker creates in worktree) | required CI green + orchestrator runs the handoff gate command + live probe: a fake run writes JSONL events and registry reconciliation reads them |
| E-run-ergonomics | delegated | medium | delegated | claude (account work, model opus, posture full-auto) | frontier | CLI/launch slice; the pilot's two manual footguns; hub Phase 4 calls this exact path | `.horus/temp/E-run-ergonomics.md` (worker creates in worktree) | required CI green + orchestrator live probe: `horus run --agent fake --worktree` creates the worktree + tracked session; `--worker` applies the posture matrix |

## Phase specs

### D-runlog-events (codex)

Structured event stream for tracked runs, replacing text-line scraping as the
machine interface. Pinned design:

- **Sidecar JSONL** per session: `~/.horus/logs/runs/<session-id>.jsonl`, written
  alongside the existing human-readable `.log` (which stays; `horus tail` keeps
  tailing the `.log`).
- Events (one JSON object per line, `ts` aware-UTC ISO, `event` field):
  `start` (session_id, agent, account, project, pid, argv summary) and
  `result` (status exited/failed, rc, ended_at). No heartbeat in this slice —
  note it as a follow-up.
- **Registry reconciliation prefers the JSONL** (`result` event → terminal state)
  and falls back to the existing text-line parsing for legacy logs — old logs
  must keep working; no migration.
- Fences: own `horus/runlog.py`, the run-side event emission, and the
  reconciliation reader in `horus/registry.py`. Do NOT touch `horus/cli.py`
  run-flag parsing, launch plumbing, or worktree logic (phase E owns those);
  no PRD.md edits.
- Sandbox-runnable gate (codex sandbox may lack network):
  `python3 -m compileall -q horus tests` + targeted
  `pytest tests/test_runlog.py tests/test_registry.py` if deps resolve; the
  orchestrator's full-suite run is the first complete pass otherwise.

### E-run-ergonomics (claude/work)

The pilot's manual footguns become flags. Pinned design:

- **`horus run --worktree <branch>`**: creates (or reuses) a git worktree at
  `<repo-parent>/<repo-name>-wt-<branch-slug>` on `<branch>` (creating the
  branch from the current HEAD if missing), then runs the session with that
  worktree as `--path`. The registry row records the worktree path. Refuse
  politely when the target path exists and is not a worktree of this repo, or
  when the repo is bare/has no git. No auto-cleanup in this slice (manual
  `git worktree remove`) — note as follow-up.
- **`--worker`**: posture preset applying the skill-v8 matrix — `claude` →
  `full-auto`, `codex` → `auto-edit`; explicit `--posture` wins over the preset.
  Help text names the headless-stall rationale.
- Fences: own `horus/cli.py` run subparser, launch/worktree plumbing (a new
  helper module is fine, e.g. `horus/worktree.py`). Do NOT touch
  `horus/runlog.py` or registry reconciliation (phase D owns those); no PRD.md
  edits.
- Gate: full suite green + the live probe above; branch → PR, do not merge.

## Notes — orchestrator contract

- Worktrees: D in `~/projects/horus-wt-events` (branch `feat/runlog-events`),
  E in `~/projects/horus-wt-runergo` (branch `feat/run-worktree`), both spawned
  `--watch`.
- Acceptance on signals only (required CI, handoff gate command, live probes);
  bounce = resume the same session with the exact failure.
- While workers run, the orchestrator handles `upgrade-project --all`
  propagation (block v4 + skill v8 → gym-coach, ttrpg) as continuity mechanics.
- **Pilot findings (running log):** —
