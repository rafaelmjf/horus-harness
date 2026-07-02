---
status: complete

current_feature: "UX-hardening batch (from the 2026-07-01/02 two-machine test): stale-build server artifact safety + self-update interpreter migration first, then projection-sync design, doctor machine checks, bulk projection refresh, sync-indicator badge"
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
delegation_basis: "Frontier supervisor + Sonnet-tier workers on this runtime → lower delegation bar (context hygiene + cheaper tier). Phases 4–6 clear it: independent, precisely specifiable, pytest-gated. Phases 1–2 are integrity/lifecycle-sensitive guards (server build identity, uv tool-env interpreter handling) where the guard design IS the work — direct. Phase 3 is a design conversation, not implementation."
last_updated: 2026-07-02
---

# Execution Plan

UX-hardening batch per roadmap `next_action`. Order: the two 2026-07-02 top items
(both root causes of the continue-leg failure — see history.md "The stale dashboard
'fixed' staleness against itself") ship first as direct work; then the design phase
unblocks the delegated trio. Design lenses from the roadmap track apply to every
phase: cross-platform (Windows/Linux/macOS) and cross-agent (Claude + Codex
projections must not drift).

## Model Policy

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting | maintainer |
| standard | narrow implementation phases with tests | worker (Sonnet-tier) |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

| phase | status | difficulty | mode | worker_tier | delegation_basis | handoff_note | review |
|---|---|---|---|---|---|---|---|
| 1-stale-build-guard | done | medium | direct | — | Integrity-sensitive: the guard that stops a stale server from writing artifacts must live in the server's own code path. Guard design is the work; judgment > volume. | — | DONE (PR #63, merged): `selfupdate.build_state()` compares loaded `__version__` vs on-disk dist metadata (stale only when disk NEWER — dev checkouts never warn); every page banners "restart Horus", and `/upgrade-project`, `/offboard`, `/github-onboard` refuse with an explanatory banner. Guard chosen over shell-out: uniform across endpoints, no PATH fragility; restart is needed anyway for badges. 543 green, CI 3.12+3.13 green. |
| 2-selfupdate-python-migration | done | medium | direct | — | Lifecycle-sensitive uv tool-env handling; small volume, subtle failure modes. | — | DONE (PR #64, merged): PyPI answer now carries `requires_python`; `run_upgrade` migrates a pinned env via `uv tool install --force --python <floor>`, uses `--reinstall` on the plain path (uv 0.11 rejects a bare `--refresh` on upgrade — found only by driving the real button), and post-verifies the on-disk dist reached latest (a stall reports the migration command, never success). README documents the one-time migration. Verified end-to-end on a live dev server incl. a forced-stale probe of phase 1. 547 green. Windows-machine migration itself is user-run (out of batch). |
| 3-sync-generation-design | accepted | medium | direct | — | Design phase: define "same generation" semantics for the projection-sync indicator. Supervisor + user; output is a contract for phase 6, no code. | — | ACCEPTED by user 2026-07-02: compare each surface to the installed CLI via per-target `upgrade_project` dry-runs, never surfaces to each other. The hook generation stamp was descoped from "prerequisite" to roadmap residual — the dry-run already covers hooks by content; the stamp only adds ahead-direction awareness. Rule promoted to decisions.md. |
| 4-doctor-machine-checks | accepted | medium | delegated | standard | High volume, low ambiguity: enumerable checks, each independently testable. Crisp pytest gate. | .horus/temp/4-doctor-machine-checks.md | ACCEPTED (PR #66, merged): Sonnet worker delivered `horus/doctor_machine.py` + `doctor machine` target (in `all`); reuses `continuity.Finding`, `selfupdate._python_floor`, `native_hooks` paths. Checks ALL command hooks incl. third-party (right call — any broken hook spams every tool call). Machine warns don't flip rc (fails do) — asymmetric with project/instructions sections, flagged for a decisions.md rule. Supervisor reproduced 562 green + drove the real surface (all-ok) + stripped-PATH probe (exact hook-spam diagnosis). |
| 5-upgrade-project-all | accepted | low | delegated | standard | Narrow: iterate registered projects, apply existing `upgrade_project` per repo, report per-project results. Builds on the shipped staleness comparison; pytest gate. CLI path — inherently safe from the phase-1 stale-server trap. | .horus/temp/5-upgrade-project-all.md | ACCEPTED (PR #65, merged): Sonnet worker delivered `--all` reusing the single-project plumbing; missing registry paths skip (other-machine entries), `--all`+`--path` refused (rc 2), dry-run rc 1 on any pending. Supervisor reproduced 552 green in the worktree + drove the real dry-run across the live registry (2 projects, all current). |
| 6-sync-indicator-badge | accepted | medium | delegated | standard | Implementation half of the projection-sync indicator, after phase 3 fixed the comparison contract. Read-only report + badge (no auto-sync). | .horus/temp/6-sync-indicator-badge.md | ACCEPTED (PR #68, merged): Sonnet worker delivered `horus/projection_sync.py` + project-detail badge; instruction actions attributed by filename (targets only routes skills/hooks); never raises (unknown → muted). Worker's nuance: a bare `init_project` is "behind" until hooks are installed — real projects post-`--apply` read in-sync. Supervisor reproduced 575 green + saw "Projections in sync" on the live detail page. Post-v0.0.9; ships next release. |

## Phase 3 design proposal (supervisor draft — needs user sign-off)

**Question:** what counts as "the same generation" across the Claude (`.claude/`)
and Codex (`.agents/`+`.codex/`) projections of one project?

**Proposal — compare each surface to the installed CLI, not to each other.**
Cross-surface direct comparison is ill-defined (different file shapes/locations);
the CLI's canonical output per target is the single source of truth, and
`upgrade_project(root, apply=False, targets=("claude",))` vs `("codex",)` already
computes exactly the needed per-surface staleness. Summarize per surface:

- **current** — zero `would-update` for that target;
- **behind (n)** — n pending items for that target;
- **ahead** — any "newer than this CLI" marker finding (block v-marker; skills).

Sync verdict per project: *in sync* when both surfaces are current; *"Codex
projection behind"* (or Claude) when exactly one has pending items; *"CLI
outdated"* when either is ahead (remedy = upgrade the CLI, matches the existing
badge's inverse direction).

**Prerequisite fold-in:** hook entries get a generation stamp (the roadmap
"Upgrade-project direction-awareness" residual) — without it hooks stay pure
content comparisons and an old CLI would offer downgrades. Open sub-question:
where to stamp (a marker key inside the managed hook JSON entry if Claude/Codex
tolerate unknown keys — must be verified per app — vs a sidecar
`.horus/projection-generation` record, which is drift-prone but schema-safe).

**Surfaces:** read-only `horus doctor compat` section + a per-project badge on
the dashboard detail page (badge = observable half; no auto-sync). Phase 6
implements against whichever variant the user approves.

## Phase 1 design sketch (supervisor)

- On-disk truth: resolve the installed dist version (`importlib.metadata` re-read is
  in-process and cached — must read the on-disk dist-info of the *installed tool env*,
  or probe `horus --version` via subprocess) and compare to the server's in-memory
  `horus.__version__`.
- When mismatched: every artifact-mutating endpoint (upgrade-project refresh,
  onboard→init) refuses with a "restart Horus — this dashboard runs an old build"
  banner; the staleness badge must not report against the in-memory generation.
- Prefer shelling out to the installed `horus` CLI for mutations where practical —
  then the write is always the on-disk generation even before restart.
- Pairs with (does not implement) the MVP5 post-upgrade auto-respawn.

## Worker handoff contract

Workers write `.horus/temp/<phase>.md` via `horus execution handoff <phase>`:
changed files, behavior, tests run + result, risks, suggested durable `.horus/`
updates. The supervisor reproduces the gate and reviews the diff before `accepted`.

**Known pre-existing test baseline:** 538 green as of 2026-07-02; do not
misattribute a new red to an unrelated cause.

## Out of batch (stay on roadmap)

Graceful hooks when CLI missing (per-OS subtlety), startup-failure visibility,
post-publish install smoke (CI), onboard commits its projected artifacts, macOS
validation pass (user-driven on real hardware), Windows machine env migration
(user runs `uv tool install --force --python 3.12 horus-harness` there).
