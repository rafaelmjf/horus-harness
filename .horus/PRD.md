---
status: active
current_focus: "Orchestration pilot batch running (execution.md): A brainstorm-dashboard on claude/work Opus, C badge-liveness on codex GPT-5.5 (parallel, separate worktrees), B hub-design doc queued behind C. This session orchestrates on deterministic signals only (required CI, RESULT events, handoff gate commands, Rafa's eyeball for UI). Signal-based acceptance shipped v0.0.22."
next_action: "Observe the wave-1 workers (A + C), accept on signals per execution.md's orchestrator contract, spawn B-hub-design on codex when C's PR is up, then distill the pilot verdict (keep/adjust/drop the orchestrator tier) into PRD."
next_prompt: "Resume Horus. FIRST git fetch --all --prune and verify the current branch against origin. Read .horus/PRD.md and .horus/execution.md (orchestration pilot, active). Check worker state: registry/badge, feat/brainstorm-dashboard and feat/session-liveness branches, open PRs and their required checks, handoff notes in the worktrees' .horus/temp/. Accept on signals only; B-hub-design starts on codex when C's PR is up."
execution_recommendation: "plan-execution — the orchestration pilot batch is active in execution.md; the orchestrator session coordinates and accepts, it does not implement."
last_updated: 2026-07-04
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

**Continuity value finding (2026-07-03, transcript analysis):** the proven spine is the
resume frontmatter + session notes + fetch-first protocol (cold pickup in ~5 tool calls,
cross-account). The six-lane taxonomy + iterate-to-zero consolidation was the overhead
(20–30 tool calls per closure; 40 unresolved overlap warnings on this very repo). Hence
this PRD structure.

## Backlog

Prioritized open work. Features and bugs in one list; jump order is allowed — this list
is a menu, not a contract. Mark bugs **[bug]**, ops chores **[ops]**.

### Now / next candidates

1. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance
   on the untracked fold (user misread "only public repos visible" when 3 private repos
   were on the ignore list).
2. **[ops] Windows machine:** one-time `uv tool install --force --python 3.12 horus-harness`
   + `horus upgrade-project --all`; eyeball the mascot failure dialog + Skills tab on a
   desktop session; confirm VS Code task keybindings work under Flatpak.
3. **macOS validation pass** (needs real hardware): mascot/Tk, terminal spawning,
   owned-window defaults, hook execution. Install-smoke CI already covers install/CLI/
   dashboard `/health` per release.
4. **Orchestration pilot batch (active, see execution.md):** three parallel features
   run as orchestrator > supervisor > worker — **A** dashboard Ideas/Brainstorm card
   (scoped-context session that drafts an implementation plan; claude/work Opus),
   **B** self-hostable hub design doc (central agent-launch place à la the gym app,
   not in the uv package; codex), **C** trustworthy session badges (liveness-verified
   registry counts, stale demotion, "as of" freshness in badge + dashboard; codex).

### Open, unscheduled

- **Execution-workflow tuning:** small phase-status vocabulary
  (planned/delegated/accepted/blocked) in the skill + template (the gate-command +
  failure-baseline handoff fields shipped in v0.0.22).
- **Skill map follow-ups** (gated on real use of the new Skills tab): Claude↔Codex
  third-party skill copy with provenance/diff/trust; invocation tracking via transcript
  scan; adopt rulesync only at a 3rd tool (Gemini/Copilot).
- **Context-cache visibility, active behavior:** decide how cold/expired sessions warn
  (companion, launch flow, hook, or dashboard-only).
- **Hook generation stamps:** hook configs are content-compared — an old CLI would offer
  a downgrade "refresh"; version-mark them like the managed block if payloads change.
- **Git-aware overview (MVP2.5):** "fetch all" refresh (fetch only, never pull);
  behind-origin / uncommitted-continuity staleness folded into the warning surface.
- **Mid-task usage interruption:** `PreToolUse` usage check (~60s cache) so a single long
  turn can't blow past the limit between `UserPromptSubmit`/`Stop` checks; plus an
  **emergency state-save at ≥97–98%** — hook-side and deterministic (zero model tokens):
  commit `.horus/**` + push to a rescue ref with a stub note, never product code, never
  a forced model closure (evidence: hub-probe closure orphaned at the limit 2026-07-03 —
  the 90% advisory fired and asked, but a long turn sailed past it).
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
`distill-history` / `infer` (deterministic pre-pass + agent ritual; bundled as
Claude+Codex skills) · `reconcile instructions` · closure freshness gate (`close --check`)
+ CI continuity check + local pre-merge hook · sessions archive (distilled → local
`sessions/archive/`) · `horus resume` minimum-context handoff · **v3 PRD+sessions
structure** (v0.0.21): PRD-first frontmatter/readers, fresh-project templates,
v3 consolidate/infer/skills, dashboard PRD rendering, opt-in six-lane migration engine,
and live migrations for gym-coach + ttrpg with archived lanes preserved verbatim ·
**signal-based acceptance** (v0.0.22): required pytest checks on main + live-proven
auto-merge, block v4, execution skill v7 (gate-command/baseline handoffs,
structure-aware suggestions), v3 routine trailers.

**Hooks & projections:** usage→closure hooks for Claude (OAuth `/usage`) + Codex
(rollouts), advisory + ask-never-force · pre-merge gates both agents · hooks guarded to
silent no-op on horus-less machines (v0.0.11) · projected artifacts committed as
continuity (v0.0.11) · `upgrade-project` (direction-aware managed block; `--all`
registry-wide) · projection-sync badge (per-surface vs installed CLI) · Skill map:
`horus skill map` + dashboard Skills tab, read-only presence across scopes (v0.0.13).

**Dashboard:** read-mostly multi-project view, sumi-e design, async heavy panels ·
project detail: launch card, context-cache estimate, recent-sessions (read-only
transcript discovery), open-continuity-PR nudge, token-overhead report · accounts rail
with usage rings + login-driven account wizard · settings/workflow-policy panel ·
self-update pill + button (env-migrating, verify-on-land, v0.0.9) · stale-build
artifact-write guard (v0.0.9) · startup-failure visibility: dashboard.log + mascot error
surfacing (v0.0.12) · Live-sessions "Reviewed ✓" per-row dismiss + review-contract
footer — the actionable side of the badge's awaiting-review (v0.0.17).

**GitHub bridge:** remote catalog (`discover github`, cached snapshots, incremental
refresh) · onboard `github:owner/repo` (clone→init→integrate via workflow policy) ·
integrate() direct-merge fallback for free-plan private repos (v0.0.12) · integrate()
returns the clone to the default branch once the branch is pushed (v0.0.14) · catalog
dedup + Track-on-this-machine · ignore/unignore · `horus start github:…`.

**Execution & adapters:** adapter contract + Fake/Claude/Codex adapters (multi-account
via `CLAUDE_CONFIG_DIR`/`CODEX_HOME`) · `run`/`open`/`focus` · execution workflow
(`execution prompt`/`handoff`, delegation rubric volume×ambiguity×runtime) · cross-agent
worker marking: per-phase `worker_agent` (native/claude/codex) in template + skill v5,
spawned via `horus run --agent codex`, proven live 2026-07-03 · hub-orchestrated
cross-project delegation proven (ttrpg Phase 2 shipped from a horus-harness hub
session, 2026-07-03) · per-run logs (`~/.horus/logs/runs/`) + `horus tail
<session-id>` + `run --watch` watcher terminal, built by a delegated claude/work
worker via branch+PR (v0.0.18) · run status decided by the terminal RESULT event —
transient tool failures no longer mark a completed run `failed`/rc=0 · registry
timestamps aware-UTC (legacy naive rows normalized on read) · in-app PTY
cockpit **retired 2026-06-30** (code dormant; launch/usage moved to Projects tab).

**Companion & launch:** Tk mascot (windowless on Windows, layered background on Linux) ·
worker badge on the mascot: per-agent running / awaiting-review / failed counts from the
session registry, click→dashboard, Dismiss Finished Workers menu (v0.0.16) ·
owned dashboard window where raise is reliable · VS Code launch destination +
`vscode-task` resume/fresh tasks · same-version `/health` adoption guard.

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
- **Three OS targets** (Windows/Linux/macOS); projections move together across agent
  surfaces (Claude + Codex), drift user-visible; sync compares each surface to the
  installed CLI, never surfaces to each other.
- **Every release:** cut promptly after meaningful merges; install smoke on all three
  OSes; tests on the `requires-python` floor (uv provisions it — floor tracks uv, not
  distro pythons). The bump is **three files together** — `pyproject.toml` +
  `horus/__init__.py` + `uv.lock` — each missed once (0.0.15, 0.0.19-broken); rerun
  the suite *after* the bump (the stale-build guard test catches a skew).
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
- **Platform traps to remember:** `uv tool install horus-harness` without
  `--python 3.12` silently resolves an ancient version when uv's default python is
  below the floor (hit on Linux 2026-07-03, not just Windows);
  after a release, the app/mascot can still be the old `uv tool` install even when
  the repo is current — compare `horus --version` with `uv run horus --version`, then
  `uv tool install --force --python 3.12 horus-harness` and restart the app;
  ctypes needs argtypes/restype (64-bit truncation);
  Windows GUI under `pythonw.exe` + reap the process tree; pin CI actions to tags that
  exist; probe the HTTP server, not the companion process; grep the binary/watch the
  network before concluding "no endpoint".

## Structure contract (prototype)

- **This file** carries vision, backlog, shipped, rules. Keep it under ~250 lines: new
  shipped items are one line; done backlog items are deleted (git remembers); bugs get
  appended to the backlog as found.
- **`sessions/`** unchanged: one note per session (`horus session new`), operational
  facts welcome (gates verified, tokens to rotate, dead ends). Distilled notes →
  `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated` — the tooling reads them PRD-first
  (`resolve_focus`), so no shims are needed.
- **Closure:** update this file's frontmatter + backlog/shipped + session note +
  `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
