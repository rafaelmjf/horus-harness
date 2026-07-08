---
status: active
current_focus: "v0.0.26 SHIPPED + RELEASED 2026-07-08 (PR #125 squash-merged; pytest 3.12/3.13 + freshness green on the commit, main push CI success, PyPI publish + install-smoke green on ubuntu/macOS/windows) — version-floor safeguards against an outdated CLI silently regressing `.horus/` to the retired six-lane structure. Two paired guards keyed off `horus_min_version` in PRD frontmatter: Lever A (agent-enforced) — new 'Version floor' section in the managed block (v5→v6) telling the session agent to check `horus --version` before any state-mutating command and STOP+upgrade if below (the only guard that binds an already-installed old CLI); Lever B (code-enforced) — `cli._enforce_version_floor` refuses (exit 4) when the running CLI is below the repo floor, wired into init/upgrade-project/close/reconcile/session/consolidate/infer/distill-history, `HORUS_IGNORE_VERSION_FLOOR=1` override. New `horus/versioning.py` owns the compare; scaffolds stamp via `templates.prd_md`, `upgrade-project` backfills/raises (never lowers). 895 tests green. Motivation: about to launch the fabric project on a machine still on horus 0.0.2."
next_action: "v0.0.26 is on PyPI. On the fabric machine: `uv tool install --force --python 3.12 horus-harness`, verify `horus --version` = 0.0.26, then `horus upgrade-project --apply` in the fabric repo (gives it the v6 block + horus_min_version stamp; from then both guards are live). Next feature candidates: #1 [ops] orphan reap (Sonnet/inline — kill the session's process tree on a failed RESULT), or the scheduled/usage-aware autonomous-continuation feature (Open, unscheduled, Opus design). [tier: Sonnet for orphan reap; Opus for the continuation design.]"
next_prompt: "Resume Horus. FIRST git fetch --all --prune and verify against origin. Read .horus/PRD.md — note the model-tier rule + per-step tier tags and the version-floor rule. v0.0.26 (version-floor safeguards) shipped + released. LEAD: #1 orphan reap (Sonnet) or the scheduled-continuation feature (Open, unscheduled, Opus design). Default worker tier = Sonnet; Opus for design + the verify gate."
execution_recommendation: "continue-as-is for orphan reap (#1, Sonnet/inline — small, clear gate). plan-execution only if implementing the scheduled-continuation primitives (several horus run flags + a scheduler — Opus supervisor + Sonnet workers). Default worker tier = Sonnet; reserve Opus for design + the verify/accept gate; Haiku for mechanical sweeps."
last_updated: 2026-07-08
horus_min_version: 0.0.26
---

# Horus — PRD

The one maintained continuity file. Structure: **PRD.md + sessions/** (prototype,
2026-07-03). The tooling reads this file's frontmatter directly (dashboard NEXT box,
`horus resume`, merge freshness gate — `resolve_focus`, Phase 1 of the v3-tooling
plan); the `project.md`/`roadmap.md` shims are deleted. The retired lanes
(`features.md`, `decisions.md`, `history.md`, `execution.md`) are preserved verbatim
in `archive/` and in git history.

## Vision

Horus is a lightweight, project-centric **continuity layer** for official coding-agent
CLIs (Claude Code, Codex, more later). The durable value is the memory plane, not
orchestration:

- repo-local `.horus/` files that any native agent session can use without Horus running;
- a read-mostly dashboard: projects, current focus, next step, sessions, accounts/usage;
- a closure ritual so work never disappears into a stale conversation;
- visibility into which agent/account/environment touched a project.

Model concretely: `project + agent + account + environment + session` — no abstract
identity profiles. Native-app-first: new capabilities are designed on Claude/Codex's own
surfaces (instructions, skills, hooks) before any Horus-owned session layer. Orchestration
is ceded to execution planes (e.g. Omnigent — see `research/omnigent.md`); Horus stays the
memory plane and interops via `.horus/`.

**Out of scope:** multi-user SaaS, agent marketplace, distributed worker control plane,
identity abstraction, memory beyond repo-local continuity.

**Continuity value finding (2026-07-03):** the proven spine is resume frontmatter +
session notes + fetch-first; the six-lane taxonomy was the overhead — hence this PRD.

## Backlog

Prioritized open work. Features and bugs in one list; jump order is allowed — this list
is a menu, not a contract. Mark bugs **[bug]**, ops chores **[ops]**.

### Now / next candidates

1. **[ops] Orphan reap after failed runs:** dead workers leave children holding
   ports (ghost probe server on 8899 corrupted a supervisor probe, 2026-07-04).
   On a `failed` RESULT — or `horus reap <session-id>` — kill the session's
   remaining process tree (registry has the pid); at minimum surface "pid still
   has children" in `horus tail`/dashboard.
2. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance
   on the untracked fold (user misread "only public repos visible" when 3 private repos
   were on the ignore list).
3. **[ops] Windows machine:** one-time `uv tool install --force --python 3.12 horus-harness`
   + `horus upgrade-project --all`; eyeball the mascot failure dialog + Skills tab on a
   desktop session; confirm VS Code task keybindings work under Flatpak.
4. **macOS validation pass** (needs real hardware): mascot/Tk, terminal spawning,
   owned-window defaults, hook execution. Install-smoke CI already covers install/CLI/
   dashboard `/health` per release.
5. **horus-hub follow-ups (harness side):** hub work continues in
   `rafaelmjf/horus-hub` (its PRD + execution.md). Parked here: JSONL heartbeat
   events; `--worktree` auto-cleanup; `--worker` could infer the agent from
   `--agent` (took a usage-error bounce 2026-07-04).

### Open, unscheduled

- **Scheduled / usage-aware autonomous continuation** (proven hand-rolled 2026-07-05:
  a systemd timer → `horus run` ran one pinned task and closed cleanly; the preflight
  refused an exhausted-window spawn). Make it first-class on the survival-kit substrate:
  `horus run --stop-at-usage <pct>` (self-checkpoint+close at a ceiling), `--at <time>` /
  `--after-usage-reset` (defer via known `resets_at`; replaces the `sleep`+timer),
  `--resume-plan` (cold session = `horus resume` handoff + "next *pinned* task → hold-merge
  → close → stop-at-usage"), an unattended posture, and registry/dashboard record of the
  run + PR. Local scheduling required (cloud routines can't reach local repos); continuity
  must pin a *specific* task. Full learnings: 2026-07-05 session note. Cross-ref: survival
  kit (v0.0.25), MVP3 autonomous closure.
- **Project-declared machine requirements** (`doctor` + `resume` + dashboard):
  a project commits `.horus/requirements.md` (frontmatter `kind: machine-requirements`
  with `tools:` name/probe/install/needed_for + optional `configs:`; body prose for
  non-probeable deps). `doctor project` probes each tool → warn findings (silent when
  absent); **`horus resume` prepends "⚠ this machine is missing: …" to the seed prompt**
  (must fire where sessions start); dashboard card gets a readiness badge. First consumer:
  fabric-metadata-driven-medallion (needs `fab`/`pbir`/PBI skills, declared there 2026-07-07).
- **Execution-workflow tuning:** small phase-status vocabulary
  (planned/delegated/accepted/blocked) in the skill + template (the gate-command +
  failure-baseline handoff fields shipped in v0.0.22). Also propagate the **model-tier
  suggestion** (Haiku/Sonnet/Opus per the model-tier rule) into the fresh-project
  template + execution skill + delegation rubric, so the per-step tier convention (now
  in this repo's PRD frontmatter) reaches every project — optionally a first-class
  `model_recommendation` frontmatter field wired through `resolve_focus`/dashboard
  rather than folded into `execution_recommendation` prose.
- **Skill map follow-ups** (gated on real use of the Skills tab): third-party skill
  copy with provenance/diff/trust; invocation tracking; rulesync only at a 3rd tool.
- **Context-cache visibility, active behavior:** decide how cold/expired sessions warn
  (companion, launch flow, hook, or dashboard-only).
- **Hook generation stamps:** hook configs are content-compared — an old CLI would offer
  a downgrade "refresh"; version-mark them like the managed block if payloads change.
- **Git-aware overview (MVP2.5):** "fetch all" refresh (fetch only, never pull);
  behind-origin / uncommitted-continuity staleness folded into the warning surface.
- **Doctor compat (observe):** per project, report what each installed agent would load
  (instructions, skills, MCP, hooks). Skills half shipped as the Skill map.
- **Workflow-policy refinements:** project the branch→PR→auto-merge default into the
  managed block; per-project override in `.horus/`.
- **Companion signals:** usage warnings, stale continuity, uncommitted `.horus/`,
  per-project switching, configurable mascot background.
- **CI gate promotion:** tests are required on this repo's main since v0.0.22;
  continuity check stays advisory → required once proven; decide if `init` installs
  the merge gate by default.

### Deferred (direction noted, not scheduled)

- **MVP3 agent execution:** oversight terminate/resume from UI; autonomous closure
  (edits restricted to `.horus/**` + managed blocks); LLM-based rich `infer`; SQLite
  registry only when scale hurts.
- **MVP5 app cohesion:** one lifecycle (mascot ⇄ dashboard window ⇄ server, owned
  windows, single-instance, post-upgrade auto-respawn); proper native app tier
  (PySide6/Electron/Tauri — pywebview tried and rejected).
- **Cross-machine proper app:** machine snapshots (paths, running sessions, dirty state).
- **`horus mcp` continuity server** — first Omnigent interop seam, only if adopted.
- **Docs website** once the surface stabilizes.
- Session-host daemon; remote attach; Telegram bridge; Tailscale dashboard;
  `reconcile --ai`; cross-repo managed-block propagation; VS Code full auto-run.

## Shipped

One line per capability; details in `archive/features.md`, git history, and the READMEs.

**Continuity core:** `horus init` (scaffold + managed AGENTS/CLAUDE blocks, never
clobbers) · `close` (verify-first; `--commit --push`, fetch-first cross-machine guard) ·
`session new` (account-aliased) · `doctor` (project/instructions/machine) · `consolidate` /
`distill-history` / `infer` (deterministic pre-pass + agent ritual; bundled Claude+Codex
skills) · `reconcile instructions` · closure freshness gate (`close --check`) + CI
continuity check + local pre-merge hook · sessions archive · `horus resume` handoff ·
**v3 PRD+sessions structure** (v0.0.21) · **signal-based acceptance** (v0.0.22: required
pytest on main + live-proven auto-merge) · **orchestration pilot** (v0.0.23: Ideas/
Brainstorm card + `horus brainstorm`, liveness-verified badges, hub design, skill v8) ·
**hub pre-work** (v0.0.24: JSONL run-event sidecars + `run --worktree`/`--worker`).

**Hooks & projections:** usage→closure hooks for Claude (OAuth `/usage`) + Codex
(rollouts), advisory + ask-never-force · pre-merge gates both agents · hooks guarded to
silent no-op on horus-less machines (v0.0.11) · projected artifacts committed as
continuity (v0.0.11) · `upgrade-project` (direction-aware managed block; `--all`
registry-wide) · projection-sync badge (per-surface vs installed CLI) · Skill map:
`horus skill map` + dashboard Skills tab, read-only presence across scopes (v0.0.13) ·
**usage-limit survival kit** (v0.0.25): 60s-cached usage snapshots, `horus run`
preflight (warn ≥80 / refuse ≥95 / `--force`, spawns export `HORUS_RUN_SESSION_ID`/
`HORUS_RUN_WORKER`), PreToolUse guard — 90% advisory + worker-aware emergency
state-save at ≥97%, never-deny · **commit-and-push checkpoint** (2026-07-08):
`closure.checkpoint_gate` (dirty working tree + unpushed commits, `enforce_push:false`
opt-out) in `close --check` + full `close`, plus a warn-default Stop hook
`horus checkpoint --hook` (`--block` opt-in) installed for Claude+Codex via
`HOOK_INSTALLERS`; merge gate stays freshness-only · **version-floor safeguards**
(v0.0.26): `horus_min_version` PRD-frontmatter stamp + two guards — managed-block
"Version floor" preflight (block v6, agent-enforced) and `cli._enforce_version_floor`
(exit 4, code-enforced) across every `.horus/`-mutating command; `horus/versioning.py`
owns the compare; `upgrade-project` backfills/raises the stamp; `HORUS_IGNORE_VERSION_FLOOR=1` override.

**Dashboard:** read-mostly multi-project view, sumi-e design, async heavy panels ·
project detail: launch card, context-cache estimate, recent-sessions (read-only
transcript discovery), open-continuity-PR nudge, token-overhead report · accounts rail
with usage rings + login-driven account wizard · settings/workflow-policy panel ·
self-update pill + button (v0.0.9) · stale-build artifact-write guard (v0.0.9) ·
startup-failure visibility (dashboard.log + mascot error, v0.0.12) · Live-sessions
"Reviewed ✓" per-row dismiss + review-contract footer (v0.0.17) · **mobile-friendly
in-app terminal** (2026-07-08): touch full-screen, on-screen key strip, responsive
tap targets, non-zoom viewport (PR #124, authored on-device).

**GitHub bridge:** remote catalog (`discover github`, cached incremental refresh) ·
onboard `github:owner/repo` (clone→init→integrate via workflow policy) · integrate()
direct-merge fallback for free-plan private repos (v0.0.12) + return-to-default-branch
(v0.0.14) · catalog dedup + Track-on-this-machine · ignore/unignore · `horus start`.

**Execution & adapters:** adapter contract + Fake/Claude/Codex adapters (multi-account
via `CLAUDE_CONFIG_DIR`/`CODEX_HOME`) · `run`/`open`/`focus` · execution workflow
(`prompt`/`handoff`, delegation rubric volume×ambiguity×runtime) · cross-agent worker
marking · hub-orchestrated cross-project delegation proven · per-run logs + `horus tail`
+ `run --watch` (v0.0.18) · run status from the terminal RESULT event · aware-UTC
registry timestamps · in-app PTY cockpit **retired 2026-06-30**.

**Companion & launch:** Tk mascot (windowless Windows, layered background Linux) · mascot
worker badge (per-agent running/awaiting-review/failed, click→dashboard, Dismiss menu,
v0.0.16) · owned dashboard window · VS Code launch + `vscode-task` resume/fresh tasks ·
same-version `/health` adoption guard.

**Distribution:** PyPI trusted publishing (uv, OIDC) · tests CI on floor+latest with
compileall gate · post-publish install smoke on ubuntu/windows/macos per release ·
Apache-2.0.

## Rules (load-bearing)

The invariants that constrain new work. Full rationale: `archive/decisions.md` +
`archive/history.md`.

- **Repo-local `.horus/` is the source of truth** — committed, vendor-neutral, works
  without Horus installed. Horus is a helper, never a required runtime.
- **Closure reaches the remote, fetch-first** — `close --commit --push`; refuse when
  origin has newer continuity. At session start: `git fetch --all --prune` and verify
  against the remote before trusting local refs or continuity prose.
- **Three disciplines, every session:** reproduce the gate via a deterministic signal
  you observe yourself — a *required* CI check green on the exact commit counts for
  the test gate; the *runtime* gate always stays yours (drive the real surface once,
  mocked tests bless nonexistent flags); never accept on a report's claims. Bound work
  to green committed-and-pushed checkpoints; safety in code, not review.
- **Hook guard invariant:** hooks signal via stdout JSON + exit 0; every committed
  command carries a per-OS silence guard (`|| exit 0` POSIX/Git Bash; PS 5.1-safe probe
  for Codex Windows). Never add an exit-code-signaling hook without revisiting this.
  Anything committed to the repo executes on every machine it reaches — strictest
  portability bar; the `horus` console script is the only guaranteed spelling.
- **Hooks advise and ask, never override** — injected context defers to the user's
  explicit command; Stop asks (close now vs push ahead); never strand uncommitted work.
  The emergency state-save keeps this bar: never denies the tool call; worker tree =
  full-tree commit to the disposable branch (+push, `-u origin` fallback); main
  checkout = `.horus/**`-only rescue ref via a temp `GIT_INDEX_FILE` — never touching
  the user's index/HEAD/worktree. Hook sentinels are machine-global under `/tmp`:
  probe session ids must be unique across supervisor/worker probes (re-arm suppression).
- **Three OS targets** (Windows/Linux/macOS); projections move together across agent
  surfaces (Claude + Codex), drift user-visible; sync compares each surface to the
  installed CLI, never surfaces to each other.
- **Every release:** cut promptly after meaningful merges; install smoke on all three
  OSes; tests on the `requires-python` floor (uv provisions it — floor tracks uv, not
  distro pythons). The bump is **three files together** — `pyproject.toml` +
  `horus/__init__.py` + `uv.lock` — each missed once (0.0.15, 0.0.19-broken); rerun
  the suite *after* the bump (the stale-build guard test catches a skew).
- **An outdated CLI must never silently regress `.horus/` structure.** Repos stamp
  `horus_min_version` (PRD frontmatter); two guards honor it — the managed-block
  Version-floor preflight (agent checks `horus --version`; the only guard that binds an
  *already-installed* old CLI, so it lives in block text, not code) and
  `_enforce_version_floor` (running CLI < floor ⇒ exit 4 on every mutating command).
  Set the stamp on scaffold, raise-never-lower via `upgrade-project`; bump
  `versioning.MIN_CLI_VERSION` only on a real structure break.
- **Dashboard contract:** read-mostly; every form POST is PRG; heavy/network panels load
  async, never in the page paint; a stale-build server never writes artifacts; empty
  nudge fragments return empty (no false "all clear").
- **Accounts:** login-driven setup into isolated dirs; TOFU identity adoption; the real
  email never lands in a commit; forward-slash every path written to TOML/JSON.
- **Git policy:** branch → PR → auto-merge; this repo's main requires pytest checks
  (admins exempt so continuity pushes land directly; fallback direct merge only on
  repos without required checks); offboard keeps `.horus/` by default; `.vscode/` is
  a user surface (static, secret-free, create-only).
- **Delegation is volume × ambiguity × runtime** — delegate high-volume/low-ambiguity
  with a clear gate, then reproduce the gate; stay inline for exploratory/debugging;
  workflow tests require a real distinct worker. Codex auto-edit workers get a
  read-only `.git` and no socket bind: the supervisor owns commit, push, and every
  runtime gate — write briefs accordingly.
- **Model tier is a delegation dimension — match it to the work, don't default to
  frontier.** Token burn ≈ (tool-call turns) × (resident context), and cache reads of
  that context are ~80% of cost — so keep the *expensive* tier's context small: push
  tool-heavy exploration/verification into subagents/workers that return distilled notes,
  not file dumps. Tiers: **Haiku** — mechanical verifiable sweeps (never the judgment
  gate); **Sonnet** — most implementation; **Opus** — design, ambiguity, the verify/accept
  gate. The main-session model can't swap per call, so cheaper execution comes only via a
  subagent/worker run on the **isolated** account (never the ambient one) — cheaper tier ×
  separate account is the double win. Full rationale: 2026-07-04 session note.
- **Orchestration (proven 2026-07-04, contract in execution skill v8):** parallel
  features run orchestrator > supervisor > worker — worktree per worker; claude workers
  `full-auto` (default posture stalls headless, exits 0 with zero diffs); bounce = resume
  the same session with the exact failure; after each merge, watch main's push CI before
  arming the next (non-strict checks let two green PRs land a red main). The orchestrator
  implements nothing and alone edits continuity. **Commit continuity before cutting a
  worker worktree from HEAD** (an uncommitted brief is invisible to the checkout) and
  **name any unreviewed-output branch in the handoff prose** (a tree back on main looks
  empty). Probe briefs must not hardcode port 8765 (the dashboard's). When a worker dies
  mid-run: checkpoint its output, reap orphaned processes holding probe ports before your
  own probes, and pass an explicit subject when squashing a single-commit branch.
- **Platform traps to remember:** `uv tool install horus-harness` without
  `--python 3.12` silently resolves an ancient version when uv's default python is below
  the floor (Linux + Windows); after a release the app/mascot can still be the old `uv
  tool` install — compare `horus --version` with `uv run horus --version`, then
  `--force --python 3.12` reinstall and restart; ctypes needs argtypes/restype (64-bit
  truncation); Windows GUI under `pythonw.exe` + reap the process tree; pin CI actions to
  tags that exist; probe the HTTP server, not the companion process.

## Structure contract (prototype)

- **This file** carries vision, backlog, shipped, rules. Keep it under ~250 lines: new
  shipped items are one line; done backlog items are deleted (git remembers); bugs get
  appended to the backlog as found.
- **`sessions/`** unchanged: one note per session (`horus session new`), operational
  facts welcome (gates verified, tokens to rotate, dead ends). Distilled notes →
  `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated` — the tooling reads them PRD-first
  (`resolve_focus`), so no shims are needed. **`next_action` / `next_prompt` /
  `execution_recommendation` each name an explicit model tier** for the next step
  (Haiku/Sonnet/Opus per the model-tier rule). If the user proposes starting a session
  on a heavier model than the work needs, pushing back — recommend the lower tier, or a
  delegated worker on the isolated account — is expected, not overstepping.
- **Closure:** update this file's frontmatter + backlog/shipped + session note +
  `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
