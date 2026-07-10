---
status: active
current_focus: "SHIPPED to main this session (2026-07-10), pending a v0.0.32 release: (1) **checkpoint-based incremental consolidation** — `horus checkpoint --harvest` auto-runs in the Stop hook, folding commit messages into the session note (zero-LLM, marker-gated); (2) **Refresh-artifacts P0** — dashboard POST refuses a dirty checkout + reports exact paths (delegated to a GPT-5.5/Codex worker, supervisor-reviewed; its out-of-scope PRD rewrite discarded); (3) **mobile live-terminal visibility** — dead SSE stream + rejected input now surface a visible notice instead of failing silently (best-effort for the 'opens but can't see/control' report — could NOT reproduce headless; the visible error will make the root cause diagnosable once it auto-deploys to hosted). Prior arc: v0.0.31 --exposed boundary; hosted auto-deploys on release via ops/deploy-hook webhook."
next_action: "Cut **v0.0.32** (three-file bump + tag) — bundles checkpoint-harvest + Refresh-artifacts P0 + mobile-terminal visibility; the ops/deploy-hook webhook then auto-updates the hosted dashboard, where the owner can retry the mobile terminal and read the now-visible error (needed to pin that root cause — it was un-reproducible headless). Then: harness flagship P0 — freeze the **LaunchBackend seam + LocalBackend** (Opus inline; Option A per hub §9/§11) → delegate RemoteBackend/ContainerBackend. Also open: Refresh-artifacts P1/P2 (backlog), checkpoint gate provenance. [tier: Opus for the seam; Sonnet/GPT5.5 for backends + P1/P2.]"
next_prompt: "Resume Horus. FIRST git fetch --all --prune. Read .horus/PRD.md. State: main clean, everything reconciled (PR #129 merged; v0.0.31 released; hosted auto-deploys on release via the ops/deploy-hook webhook). LEADS: (a) freeze the LaunchBackend seam (P0, Opus inline) then delegate the backends; (b) fix the Refresh-artifacts dirty-worktree bugs (bugs/, self-contained); (c) build checkpoint-based incremental consolidation (backlog has the automatic harvest-hook design). horus-hub PRD item 2 + §11 hold the multi-machine decisions."
execution_recommendation: "continue-as-is for the LaunchBackend seam freeze (Opus inline — the interface is the contract every backend implements) and the bugs/checkpoint tooling (small, self-contained). plan-execution once the seam is frozen: RemoteBackend + ContainerBackend + hub worker/provisioning is high-volume, low-ambiguity, cross-repo — delegate to fresh sessions on the isolated accounts (GPT 5.5 / other Claude), one backend per worktree, --watch + review per owner preference."
last_updated: 2026-07-10
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

- **★ [flagship, important — not necessarily next] LaunchBackend seam + LocalBackend
  (harness P0 of the multi-machine arc).** Extract the session-launch chokepoint
  (`horus run` / adapters / `pty_host.start`) behind one interface —
  `launch(brief)→handle · status · stream · stop` — with a config-driven `LocalBackend`
  as the first impl (Option A in hub `docs/multi-machine-launch-targets-design.md` §9:
  harness owns local/ssh/container backends reading a `[[targets]]` table; hub owns the
  provisioning/probe/registry kit that writes it). **Freeze the interface first** — it's
  the contract `RemoteBackend` (tailnet worker) and `ContainerBackend` (hub-launched
  container) both implement, so once frozen those two backends parallelize as delegated
  work (GPT 5.5 → container, other Claude account → remote/worker; one worktree each,
  `--watch` + review). Pure refactor, no behavior change. Container launch = just the
  third backend, not a separate epic. [tier: Opus for the freeze; Sonnet/GPT5.5 impls.]
- **[bug] Refresh artifacts — P1/P2 remain (P0 shipped 2026-07-10).** P0 done: the dashboard
  POST now refuses a dirty checkout (mutation-path guard, names dirty+planned paths), reports
  exact changed paths, and warns on manual-commit policy (see Shipped). Still open, per
  `bugs/refresh-artifacts-leaves-dirty-worktree.md`: **P1** provenance receipt
  (`.horus/cache/last-artifact-refresh.json` — needs a `.horus/cache/` ignore rule first, since
  writing it would itself dirty the tree) + a checkpoint advisory that classifies generated vs
  authored dirty paths (`bugs/checkpoint-warning-after-artifact-refresh.md`); **P2** run the
  refresh through `[workflow]` (isolated branch → commit → push → PR → merge) for automatic
  policies. Self-contained; delegatable.
1. **[ops] Orphan reap after failed runs:** dead workers leave children holding
   ports (ghost probe server on 8899 corrupted a supervisor probe, 2026-07-04).
   On a `failed` RESULT — or `horus reap <session-id>` — kill the session's
   remaining process tree (registry has the pid); at minimum surface "pid still
   has children" in `horus tail`/dashboard.
2. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance
   on the untracked fold (user misread "only public repos visible" when 3 private repos
   were on the ignore list).
3. **[ops] Machine validation leftovers:** eyeball mascot failure dialog + Skills tab
   (Windows); confirm VS Code task keybindings under Flatpak (Linux). The reinstall +
   `upgrade-project --all` halves shipped 2026-07-09 with v0.0.29.
4. **macOS validation pass** (needs real hardware): mascot/Tk, terminal spawning,
   owned-window defaults, hook execution. Install-smoke CI covers install/CLI/`/health`.
5. **horus-hub follow-ups (harness side):** hub work in `rafaelmjf/horus-hub` (its PRD +
   execution.md). Parked: JSONL heartbeat events; `--worktree` auto-cleanup; `--worker`
   inferring agent from `--agent` (usage-error bounce 2026-07-04).
6. **[ops] Measure per-tool-call hook spawn cost:** up to three `horus` processes per
   shell call (close + guard-host + usage guard), reaching PowerShell calls too since
   the F1 matcher fix. Measure on a tool-heavy session; only if material, build a
   single `horus pretool --hook` dispatcher (fabric suggestion 2026-07-08). [tier:
   Haiku measure / Sonnet dispatcher]
7. **Multi-developer continuity (design, evidence-gated):** PRD.md assumes one active
   workstream — two devs closing sessions collide on frontmatter (`current_focus`/
   `next_action`), the merge hot-spot; body sections merge like code and sessions are
   already per-machine local. Direction: per-workstream focus (frontmatter keyed by
   branch/dev, or `.horus/focus/<name>.md`) aggregated by `resolve_focus`/dashboard/
   `resume`; fetch-first close guard already refuses stale closes. Per the ladder
   rule, design now, build when a real second developer arrives. [tier: Opus design]

### Open, unscheduled

- **Scheduled / usage-aware autonomous continuation** (proven hand-rolled 2026-07-05:
  systemd timer → `horus run` ran one pinned task, closed cleanly; preflight refused an
  exhausted-window spawn). Make first-class on the survival-kit substrate: `run
  --stop-at-usage <pct>`, `--at <time>` / `--after-usage-reset` (defer via `resets_at`),
  `--resume-plan` (cold session = `horus resume` + pinned-task → hold-merge → close),
  unattended posture, registry/dashboard record of run + PR. Local scheduling required;
  continuity must pin a *specific* task. Full learnings: 2026-07-05 note.
- **Project-declared machine requirements** (`doctor` + `resume` + dashboard): a project
  commits `.horus/requirements.md` (`kind: machine-requirements`, `tools:` name/probe/
  install/needed_for + `configs:`; prose for non-probeable deps). `doctor project` probes →
  warn findings; **`horus resume` prepends "⚠ this machine is missing: …" to the seed
  prompt**; dashboard card gets a readiness badge. First consumer: fabric (needs `fab`/
  `pbir`/PBI skills, declared there 2026-07-07).
- **Execution-workflow tuning:** phase-status vocabulary (planned/delegated/accepted/
  blocked) in skill + template; propagate the **model-tier suggestion** into the
  fresh-project template + execution skill + delegation rubric so the per-step tier
  convention reaches every project — optionally a first-class `model_recommendation`
  frontmatter field via `resolve_focus`/dashboard rather than `execution_recommendation` prose.
- **Skill map follow-ups** (gated on real Skills-tab use): third-party copy with
  provenance/diff/trust; invocation tracking; rulesync only at a 3rd tool.
- **Context-cache visibility:** how cold/expired sessions warn (companion/launch/hook/dashboard).
  **Hook generation stamps:** version-mark content-compared hook configs like the managed
  block if payloads change, else an old CLI offers a downgrade "refresh".
- **Git-aware overview (MVP2.5):** session-start half shipped (v0.0.29 `fetch-check`
  SessionStart hook); remaining: fold behind-origin / uncommitted-continuity staleness
  into the dashboard warning surface ("fetch all", never pull).
- **Doctor compat (observe):** per project, report what each agent would load (instructions/
  skills/MCP/hooks). **Workflow-policy:** block v7 carries the branch→PR default as
  instruction text (fabric field evidence: direct-to-main went unchallenged); remaining
  per the ladder rule: per-project `.horus/` override, then **CI gate promotion** only
  if the instruction rung observably fails again — continuity check advisory → required
  once proven; decide if `init` installs the merge gate by default.
- **Companion signals:** usage warnings, stale/uncommitted `.horus/`, per-project
  switching, configurable mascot background.

### Deferred (direction noted, not scheduled)

- **MVP3 agent execution:** UI terminate/resume; autonomous closure; LLM-rich `infer`;
  SQLite registry only when scale hurts. **MVP5 app cohesion:** one lifecycle
  (mascot ⇄ dashboard ⇄ server, owned/single-instance, post-upgrade respawn); native app
  tier (PySide6/Electron/Tauri, pywebview rejected); cross-machine machine snapshots.
- **`horus mcp` continuity server** (first Omnigent seam); docs website; session-host
  daemon; remote attach; Telegram bridge; Tailscale dashboard; `reconcile --ai`;
  cross-repo managed-block propagation; VS Code full auto-run.

## Shipped

One line per capability; details in `archive/features.md`, git history, and the READMEs.

**Dashboard robustness** (2026-07-10): Refresh-artifacts P0 — the POST refuses a dirty
checkout (mutation-path guard, lists dirty + planned paths + dry-run cmd), reports exact
changed paths, and warns/lists on manual-commit policy (`UpgradeAction.path` provenance);
never stashes/resets/commits. Plus: live terminals surface a dead SSE stream + rejected
input instead of failing silently (the "opens but can't see/control" symptom → visible,
diagnosable notice).

**Checkpoint-based incremental consolidation** (2026-07-10): `horus checkpoint --harvest`
appends commit messages since a local `consolidated-to` marker to the latest session note
(deterministic, zero-LLM, idempotent, trailer-stripped) — runs automatically inside the
existing Stop checkpoint hook, so continuity keeps pace per turn and the "work commits since
summary" nudge clears itself; close becomes light hygiene over a small delta instead of a
whole-log distillation. Commit-message quality = continuity granularity.

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
owns the compare; `upgrade-project` backfills/raises the stamp; `HORUS_IGNORE_VERSION_FLOOR=1` override ·
**shadow-install guard** (v0.0.28): `doctor machine` warns when >1 `horus` executable is resolvable on
PATH (`_all_on_path`, PATHEXT-aware, real-path deduped) — a stale `pip install` shadowing the uv shim ·
**stale running-dashboard scan** (v0.0.30): `doctor machine` probes localhost 8765–8775
(`_scan_running_dashboards` via `companion.dashboard_identity`, pid-deduped) and warns when a live
dashboard's build is older than the installed CLI — advises *restart*, never *kill* (may be a hosted
systemd backend) · **welcome overlay removed** (v0.0.30): the decorative first-run splash looped on
every launch (per-tab sessionStorage flag) — deleted, dashboard renders straight to content ·
**`--exposed` boundary** (on main, pending v0.0.31): the `[access]` gate is an explicit
`horus dashboard --exposed` launch flag (fail-closed without a block); local mode never reads
`[access]`, ending the machine-global-config 403 of local `horus app` ·
**v0.0.29 hooks bundle:** Claude shell guards match `Bash|PowerShell` (F1, both layers) with matcher
re-homing so fixes propagate to scaffolded repos · `fetch-check` SessionStart fetch-first signal
(TTL-cached, advisory) · block v7 (workflow + execution-mode planning discipline as instruction rungs).

**Dashboard:** read-mostly multi-project view, sumi-e design, async heavy panels ·
project detail: launch card, context-cache estimate, recent-sessions (read-only
transcript discovery), open-continuity-PR nudge, token-overhead report · accounts rail
with usage rings + login-driven account wizard · settings/workflow-policy panel ·
self-update pill + button (v0.0.9) · stale-build artifact-write guard (v0.0.9) ·
startup-failure visibility (dashboard.log + mascot error, v0.0.12) · Live-sessions
"Reviewed ✓" per-row dismiss + review-contract footer (v0.0.17) · **mobile-friendly
in-app terminal** (2026-07-08): touch full-screen, on-screen key strip, responsive
tap targets, non-zoom viewport (PR #124, authored on-device) · **catalog add-UI**
(v0.0.27): in-app forms to register a GitHub owner (`/github-add-owner`) + add a
local project (`/local-add`: register existing `.horus/` or scaffold from zero).

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
- **Controls climb a ladder: instruction → deterministic signal → hard gate.** New
  controls start as instruction text; promote a rung only on an *observed field
  failure* of the rung below (fabric 2026-07-08: fetch-first + branch→PR failed as
  instructions → became a SessionStart signal + block v7 policy line). Never build
  enforcement preemptively — this is the anti-over-engineering test for backlog items.
- **Continuity must beat re-derivation.** Every `.horus/` capability names what a
  fresh session gets that CLAUDE.md + git log alone couldn't, at less cost than
  re-deriving it. PRD.md is *state*, not behavior; behavioral text belongs in the
  managed block, and Rules stays project-specific invariants earned by failure —
  otherwise this file drifts into a second CLAUDE.md.
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
  command; Stop asks (close now vs push ahead); never strand uncommitted work. Emergency
  state-save keeps this: never denies the tool call; worker tree = full-tree commit to the
  disposable branch (+push, `-u origin` fallback); main checkout = `.horus/**`-only rescue
  ref via a temp `GIT_INDEX_FILE`, never touching the user's index/HEAD/worktree. Hook
  sentinels are machine-global under `/tmp` — probe session ids must be unique across
  supervisor/worker probes.
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
  nudge fragments return empty (no false "all clear"); no first-run splash/overlay
  (the welcome overlay looped and was removed — render straight to content).
- **Exposure is an explicit launch property, never ambient config.** The `[access]`
  Cloudflare gate arms ONLY under `horus dashboard --exposed`; local mode never reads
  `[access]`, so a machine-global block can't 403 a local `horus app` (v0.0.31). Fail
  closed: `--exposed` with no `[access]` block refuses to serve. A hosted backend must
  pass `--exposed` (its systemd unit does) — flipping this default without updating the
  unit would silently un-gate the public dashboard, so treat the harness flag + the
  deploy unit as one lockstep change. Persist a client-side seen-flag in `localStorage`,
  not `sessionStorage` (per-tab → resets on every new window Horus opens).
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
  frontier.** Token burn ≈ (tool-call turns) × (resident context), cache reads of which are
  ~80% of cost — keep the *expensive* tier's context small: push tool-heavy exploration/
  verification into subagents/workers returning distilled notes, not file dumps. **Haiku** —
  mechanical verifiable sweeps (never the judgment gate); **Sonnet** — most implementation;
  **Opus** — design, ambiguity, the verify/accept gate. Main-session model can't swap per
  call, so cheaper execution comes only via a worker on the **isolated** account (never the
  ambient one) — cheaper tier × separate account is the double win. Rationale: 2026-07-04 note.
- **Orchestration (proven 2026-07-04, contract in execution skill v8):** parallel features
  run orchestrator > supervisor > worker — worktree per worker; claude workers `full-auto`
  (default posture stalls headless); bounce = resume same session with the exact failure;
  after each merge watch main's push CI before arming the next. Orchestrator implements
  nothing, alone edits continuity. Commit continuity before cutting a worktree from HEAD;
  name any unreviewed-output branch in the handoff; probe briefs never hardcode port 8765;
  reap orphaned port-holders before probing after a worker death.
- **Platform traps:** `uv tool install horus-harness` without `--python 3.12` silently
  resolves an ancient version when uv's default python is below the floor; after a release
  the app/mascot can still be the old install — compare `horus --version` with `uv run
  horus --version`, `--force --python 3.12` reinstall + restart; a **stale `pip`-installed
  `horus` on PATH shadows the uv shim** (v0.0.28 `doctor machine` flags it); ctypes needs
  argtypes/restype; Windows GUI under `pythonw.exe` + reap the tree; pin CI actions to real
  tags; probe the HTTP server, not the companion.

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
