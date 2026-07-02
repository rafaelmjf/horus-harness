---
status: active
last_updated: 2026-07-03
---

# Horus — PRD

The one maintained continuity file. Structure: **PRD.md + sessions/** (prototype,
2026-07-03). `project.md` and `roadmap.md` remain as thin frontmatter shims for the
current tooling (dashboard NEXT box, `horus resume`, merge freshness gate); their
content lives here. The retired lanes (`features.md`, `decisions.md`, `history.md`,
`execution.md`) are preserved verbatim in `archive/` and in git history.

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

1. **PRD structure as the product (v3 continuity structure).** Prototype is live in this
   repo; if it survives a few sessions, teach the tooling: templates + `horus init` scaffold
   PRD+sessions; `close --check` freshness reads PRD frontmatter (drop the shims);
   `consolidate` becomes a light "backlog hygiene" check (no lane-purity warnings);
   `infer`/skills rewritten for the new shape; dashboard renders PRD sections; migrate
   agentic-gym-coach + agentic-ttrpg via `upgrade-project`. Closure contract becomes:
   update PRD (focus/backlog/shipped) + session note + commit.
2. **[bug] `integrate()` leaves the clone on the `horus/chore-…` branch** after pushing —
   switch back to the default branch (seen live in agentic-gym-coach; default branch may
   be `master`, never hardcode `main`).
3. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance
   on the untracked fold (user misread "only public repos visible" when 3 private repos
   were on the ignore list).
4. **[ops] Windows machine:** one-time `uv tool install --force --python 3.12 horus-harness`
   + `horus upgrade-project --all`; eyeball the mascot failure dialog + Skills tab on a
   desktop session; confirm VS Code task keybindings work under Flatpak.
5. **macOS validation pass** (needs real hardware): mascot/Tk, terminal spawning,
   owned-window defaults, hook execution. Install-smoke CI already covers install/CLI/
   dashboard `/health` per release.

### Open, unscheduled

- **Execution-workflow tuning:** handoff template carries the pre-existing test-failure
  baseline; small phase-status vocabulary (planned/delegated/accepted/blocked) in the
  skill + template.
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
  turn can't blow past the limit between `UserPromptSubmit`/`Stop` checks.
- **Doctor compat (observe):** per project, report what each installed agent would load
  (instructions, skills, MCP, hooks). Skills half shipped as the Skill map.
- **Workflow-policy refinements:** project the branch→PR→auto-merge default into the
  managed block; per-project override in `.horus/`.
- **Companion signals:** usage warnings, stale continuity, uncommitted `.horus/`,
  per-project switching, configurable mascot background.
- **CI gate promotion:** continuity check advisory → required once proven; decide if
  `init` installs the merge gate by default.

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
`sessions/archive/`) · `horus resume` minimum-context handoff.

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
surfacing (v0.0.12).

**GitHub bridge:** remote catalog (`discover github`, cached snapshots, incremental
refresh) · onboard `github:owner/repo` (clone→init→integrate via workflow policy) ·
integrate() direct-merge fallback for free-plan private repos (v0.0.12) · catalog dedup +
Track-on-this-machine · ignore/unignore · `horus start github:…`.

**Execution & adapters:** adapter contract + Fake/Claude/Codex adapters (multi-account
via `CLAUDE_CONFIG_DIR`/`CODEX_HOME`) · `run`/`open`/`focus` · execution workflow
(`execution prompt`/`handoff`, delegation rubric volume×ambiguity×runtime) · in-app PTY
cockpit **retired 2026-06-30** (code dormant; launch/usage moved to Projects tab).

**Companion & launch:** Tk mascot (windowless on Windows, layered background on Linux) ·
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
- **Three disciplines, every session:** reproduce the gate yourself (including the
  *runtime* gate — drive the real surface once, mocked tests bless nonexistent flags);
  bound work to green committed-and-pushed checkpoints; safety in code, not review.
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
  distro pythons).
- **Dashboard contract:** read-mostly; every form POST is PRG; heavy/network panels load
  async, never in the page paint; a stale-build server never writes artifacts; empty
  nudge fragments return empty (no false "all clear").
- **Accounts:** login-driven setup into isolated dirs; TOFU identity adoption; the real
  email never lands in a commit; forward-slash every path written to TOML/JSON.
- **Git policy:** branch → PR → auto-merge (fallback: direct merge when no required
  checks); offboard keeps `.horus/` by default; `.vscode/` is a user surface (static,
  secret-free, create-only).
- **Delegation is volume × ambiguity × runtime** — delegate high-volume/low-ambiguity
  with a clear gate, then reproduce the gate; stay inline for exploratory/debugging;
  workflow tests require a real distinct worker.
- **Platform traps to remember:** ctypes needs argtypes/restype (64-bit truncation);
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
- **Shims:** `project.md` (current_focus) and `roadmap.md` (next_action/next_prompt/
  execution_recommendation) keep live frontmatter only, until the tooling reads PRD
  frontmatter directly.
- **Closure:** update shim frontmatter + this file's backlog/shipped + session note +
  `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
