---
status: active
current_feature: "GitHub project onboarding + workflow policy (Tracks A/B/C)"
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
last_updated: 2026-06-29
---

# Execution Plan

Fluid, optional plan for the currently active roadmap item. Replace this when
the next substantial feature starts; distill finished work into `roadmap.md`,
`features.md`, `decisions.md`, and `history.md` rather than preserving this as a
timeline.

> **STATUS: ACTIVE — user approved 2026-06-29 to implement through A2 if no blockers.**
> Phases C-min → A1 → A2 run sequentially under supervisor review; A3/A4/C-full/B remain
> planned for a later go-ahead.

## Active Feature

Manage GitHub-tracked projects from the dashboard, across three tracks (see
roadmap.md "GitHub project onboarding", "Dashboard artifact-staleness flag",
"Workflow policy + settings panel"; rationale in decisions.md 2026-06-29 "GitHub
Onboarding + Workflow Policy"):

- **Track A** — surface untracked GitHub repos (opt-out), onboard them in one action.
- **Track B** — passively flag tracked projects whose Horus-projected artifacts lag the
  installed CLI (independent, small).
- **Track C** — a configurable branch→PR→auto-merge workflow policy + dashboard Settings
  panel that Horus-driven git actions consume.

**Locked decisions** (do not re-litigate without the user): untracked repos shown opt-out;
ignore list + `github_owners` per-machine with a blank-owner dashboard warning; default
integration = branch→PR→auto-merge unless review; agent-instruction projection and
per-project policy override are deferred.

## Model Policy

Use tiers instead of hard-coded model names. Resolve them locally per agent,
account, and current model availability.

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting, small docs from explicit notes | maintainer |
| standard | narrow implementation phases with tests | worker |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

Sequential A/C phases run in order (each depends on the prior); **B is independent** and
can be slotted in anytime. Status vocabulary: `planned` → `delegated` → `accepted`
(or `blocked`).

| phase | status | difficulty | worker_tier | depends on | handoff_note | review gate |
|---|---|---|---|---|---|---|
| C-min | accepted | moderate | standard | — | `.horus/temp/C-min.md` | ✅ 33 tests; integration.py + `[workflow]` config + `horus workflow` CLI; full suite green (1 known baseline) |
| A1 | accepted | moderate | standard | — | `.horus/temp/A1.md` | ✅ `DiscoveryResult(projects, untracked)` + verdict cache; caught extra caller `remote_start.py`; 401 pass / 1 baseline |
| A2 | accepted | low | standard | A1 | `.horus/temp/A2.md` | ✅ ignore list config + CLI + `filter_ignored` helper + blank-owner CTA; 424 pass / 1 baseline |
| A3 | planned | hard | standard | C-min, A1 | `.horus/temp/A3.md` | onboard clone/init/integrate; dry-run path tested without real GitHub |
| A4 | planned | moderate | standard | A2, A3 | `.horus/temp/A4.md` | Not-tracked section + POST endpoints; same-origin/loopback guard tested |
| C-full | planned | moderate | standard | C-min | `.horus/temp/C-full.md` | Settings panel POST writes `[workflow]`; guard tested |
| B | planned | low | standard | — | `.horus/temp/B.md` | read-only badge from `upgrade_project(apply=False)`; no mutation on render |

### Phase detail

- **C-min — workflow policy foundation.** Add a `[workflow]` section to
  `~/.horus/config.toml` (`integration`, `commit`, `merge`) with a loader + resolver in
  `config.py`, and a reusable integration helper module (branch → commit → push →
  `gh pr create` → `gh pr merge --auto`, or stop at PR for review mode; `local-only`/
  `direct-push` paths too). Pure/mocked unit tests only — **no real GitHub calls in the
  suite.** Expose via a `horus workflow` show/set CLI command (the testable consumer).
  Supervisor refinement (2026-06-29): do **not** rewire the proven `close --commit` path in
  this phase — the first real git consumer is `horus onboard` (A3); keeps the foundation low-risk.
- **A1 — untracked discovery + verdict cache.** `discover()` returns Horus projects *and* a
  second list of untracked repos; extend the per-repo cache to store the not-Horus verdict
  keyed by `pushedAt` so unchanged repos skip the `gh api` check. New/changed repos always
  re-check. `gh` mocked in tests (extend `tests/test_github_catalog.py`).
- **A2 — ignore list + blank-owner warning.** `ignored_repos` in config (per-machine) with
  add/remove CLI; discovery/dashboard filter ignored repos into a collapsed "Hidden (N)"
  sublist. Dashboard shows a "configure a GitHub owner" CTA when `github_owners` is empty.
- **A3 — `horus onboard github:owner/repo`.** Clone into `workspace_root` if not present →
  `horus init` → integrate via the C-min policy. Reuse `cmd_start` + init machinery; refuse
  unsafe existing destinations. Tests exercise the non-network path (clone/integrate mocked).
- **A4 — dashboard Not-tracked section + actions.** Render untracked repos with per-repo
  **Onboard** / **Ignore** buttons over the existing same-origin-guarded, loopback-only POST
  surface (mirror `/launch`). Manual Refresh drives re-discovery. Opt-out only, never bulk.
- **C-full — Settings panel.** Dashboard panel (POST, same-origin + loopback guard) to edit
  the `[workflow]` policy via checkboxes/selects.
- **B — artifact-staleness badge.** Per local/cloned project, call
  `upgrade.upgrade_project(root, apply=False)` read-only on load; show "⚠ Horus artifacts
  outdated" + the `horus upgrade-project --apply` command when any non-skip action exists.

## Worker Handoff Contract

Implementation workers should write a brief note in `.horus/temp/` when a phase
finishes. Keep it factual and reviewable:

- changed files / behavior;
- tests run and result;
- risks or follow-ups;
- suggested durable `.horus/` updates.

**Supervisor brief convention (pilot finding 2026-06-29):** each worker brief states the
**known pre-existing test-failure baseline** so a worker does not misattribute an unrelated
red test to its own change. Current known-failing baseline:
`tests/test_config.py::test_workspace_root_defaults_and_round_trips` (non-portable
forward-slash path assertion on Windows; unrelated to this work — a fix is queued as a
separate task).

The supervisor reviews the diff and the handoff, then updates the durable lanes.

Useful commands:

- `horus execution prompt --target codex` prints a supervisor prompt shaped for
  Codex subagents/custom agents.
- `horus execution prompt --target claude` prints the Claude Code equivalent.
- `horus execution handoff C-min` creates `.horus/temp/C-min.md` for a worker note.
