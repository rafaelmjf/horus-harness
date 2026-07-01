---
status: active
current_focus: "Two-machine test legs 1–2 done (Linux machine 2): caught v0.0.5 dead-on-import under Python 3.11 (→ v0.0.6 + first-ever CI test matrix) and the committed hook files erroring on every Bash call ('python -m horus' is machine-local; → v0.0.7: portable 'horus' console-script hook commands + floor raised to >=3.12, user call). Both on PyPI; 537 tests green; machine 2 verified."
next_action: "USER continues the live two-machine flow validation from machine 2, now on v0.0.7: run the onboard/continue legs (same alias on both machines, per-machine owner config), exercise the dashboard/companion behaviors shipped 2026-07-01 (see features.md rows from that date), and fix whatever the test surfaces. Also run `horus upgrade-project --apply` in the sibling onboarded repos so their committed hook files pick up the portable commands; then pick the next roadmap item (overview-card transcript summaries, or MVP2.5 fetch-all)."
next_prompt: "Resume Horus. FIRST `git fetch --all --prune` and verify branch state. v0.0.7 is on PyPI carrying the two-machine test's first two findings: the 3.11 import crash (fixed + CI matrix now gates the floor) and the non-portable committed hook commands (now the 'horus' console script; floor raised to >=3.12). 537 tests green. NEXT: continue the live cross-machine onboard/continue test from the roadmap next_action; refresh sibling repos' hooks via `horus upgrade-project --apply`; fix what the test surfaces. The active execution.md documents the finished 2026-07-01 batch — replace it when the next substantial item starts."
execution_recommendation: "continue-as-is - the next step is a user-driven live test plus fixes for whatever it surfaces: interactive, exploratory, small-volume debugging where delegation buys nothing."
last_updated: 2026-07-02
---

# Roadmap

## Strategy - Omnigent Boundary

> Full evaluation + drift-triggers live in `research/omnigent.md` (the prior-art
> guardrail). Distilled rule in decisions.md "Omnigent Is An Interop Target".

- [ ] (Direction only, not scheduled) First interop seam = a `horus mcp` continuity server any MCP client can read (Omnigent the first consumer); then a thin `horus export omnigent` bundle; dashboard session read-back optional. Revisit only if/when actually adopting Omnigent.

## Context Cache Visibility

- [ ] Decide active behavior for cold/expired sessions: companion warning, launch-flow warning, native hook/statusline projection, or dashboard-only.

## UX hardening — fresh-machine first-touch (from the 2026-07-01/02 two-machine test)

> Every failure the live test surfaced happened silently or cryptically the moment a
> fresh machine first touched Horus (v0.0.5 dead-on-import; hook error spam; "app won't
> open" with no diagnostic; stale uv index on upgrade). Design lenses for all items:
> (1) **cross-platform** — everything must work on Windows, Linux, AND macOS (macOS
> entirely untested so far); (2) **cross-agent** — Claude and Codex (more later) must
> stay in sync: skills + hooks are *projections*, so any major change must reach every
> agent surface, and the UI should say when they've drifted. See history.md for the bumps.

- [ ] **Graceful hooks when the CLI is missing/broken** (top priority): committed hook
  files reach every machine and every collaborator, including ones without Horus — a
  missing `horus` must be a silent no-op, not per-Bash-call error spam. NB the guard
  must be per-OS (POSIX `command -v` vs Windows — Claude runs hook commands through the
  native shell), so this is exactly where the cross-platform lens bites. `horus doctor`
  / dashboard then report "hooks installed but CLI unavailable" as the visible signal.
- [ ] **Post-publish install smoke** (CI): after each PyPI publish, fresh
  ubuntu + windows + **macos** runners `uv tool install` from PyPI (retry for index
  propagation), then probe `horus --version` + dashboard `/health`. Doubles as the
  first-ever macOS coverage; "reproduce the gate" applied to releases.
- [ ] Dashboard `/self-update` button: run `uv tool upgrade --refresh` (stale uv index
  cache no-opped the upgrade twice during the live test). One-liner.
- [ ] **`horus doctor` machine-level checks**: console script on PATH, interpreter vs
  the `requires-python` floor, hook commands resolvable, Tk present (mascot), `gh`
  auth. The one command to run when "the app won't open".
- [ ] **Startup failure visibility**: dashboard/companion startup errors go to
  `~/.horus/logs/` and the companion surfaces "dashboard failed to start — run
  `horus doctor`" instead of nothing.
- [ ] **Bulk projection refresh**: `horus upgrade-project --all` (or a dashboard
  "refresh all stale projects" action) so a CLI upgrade propagates skills/hooks/blocks
  to every registered repo in one step, building on the existing staleness badge.
- [ ] **Projection-sync indicator in the UI**: per project, show whether each agent
  surface (Claude `.claude/` vs Codex `.agents/`+`.codex/`) carries the same
  generation of skills/hooks/managed block — "in sync" vs "Codex projection behind".
  This is the observable half of `horus doctor compat` (→ "Cross-tool interface sync"
  track below); do the read-only report + badge before any auto-sync.
- [ ] **macOS validation pass**: nothing has ever run on macOS — mascot (Tk
  transparency), terminal spawning in `launcher`, owned-window/tab defaults, hook
  execution. Fold findings back into the per-OS defaults like `resolve_open_mode`.

## Execution Planning Workflow

- [ ] Apply the two pilot tuning findings (deferred behind the GitHub-onboarding tracks): (1) supervisor brief / handoff template carries the known pre-existing test-failure baseline; (2) a small phase status vocabulary (`planned/delegated/accepted/blocked`) in the `horus-execution` skill + `execution.md` template. Small `continue-as-is` task; see decisions.md 2026-06-29 "Execution-Workflow Pilot".
- [ ] Later, consolidate the execution-workflow evals across Codex and Claude once both have been exercised on comparable real tasks. Do **not** do this first: useful comparison needs a little more instrumentation and a stable enough workflow contract. Capture whether each planner chose direct work, delegated work, or a model-separation test, plus the `delegation_basis`, review/rework, and rough token/time cost.

## Documentation Website

- [ ] Deferred until the product surface is somewhat more stable: add a lightweight documentation website for Horus concepts, setup, workflows, and native Claude/Codex integration. This is increasingly valuable as the project grows, but it adds maintenance overhead; prefer improving README/help text and stabilizing command surfaces first.

## Workflow policy + settings panel (Track C) - branch→PR→auto-merge default

> Decided 2026-06-29. Default integration policy for Horus-driven git actions across all
> tracked projects: feature branch → PR → auto-merge unless flagged for user review.
> Avoids "forgot to push, stuck local-only". This automates what was done by hand in the
> 2026-06-29 onboarding session.

- [ ] Deferred refinement: project the policy into the managed instruction block
  (AGENTS.md/CLAUDE.md) so the in-session agent adopts the same default for its own code
  work (Horus can only directly own its own commits — onboard + closure).
- [ ] Deferred refinement: per-project policy override stored in git-synced `.horus/`
  (e.g. "this repo always needs review"); start with the per-machine default only.

## MVP 2 - Session Continuity (file-first)

- [ ] **Clearer session handoff / branch pickup** — IMPROVEMENT (flagged 2026-06-25 after a handoff named a branch that
  existed only on `origin`; the pickup agent trusted stale local refs and misjudged the state). Encode a fetch-first +
  verify-branch step at session pickup (done for now via `next_prompt`); consider also recording `branch:` + push/merge
  state in the session summary and surfacing it in `horus close`/dashboard. Possibly a `horus resume` command or a managed
  instruction-block step. See history.md.
- [ ] **Mid-task usage interruption (Codex-style "check between every action")** — IMPROVEMENT. `UserPromptSubmit`/`Stop` only fire at task boundaries; a single long turn can still blow past the limit. Add a `PreToolUse` hook that checks usage before each tool call (with a short ~60s cached read to avoid hammering the OAuth endpoint) and blocks → diverts to closure mid-task. Gate carefully to avoid spamming.
- [~] SQLite session/event registry + session states (`closing`/`needs_closure`/`closed_stale`) — DEFERRED. Premature at solo scale (file parsing is instant) and presupposes the deferred execution layer. Revisit when scale hurts perf or Horus runs sessions itself.

## Structure v2 - `.horus/` lanes + distillation routines (prototyping in fabric)

> Designed against `fabric-metadata-driven-medallion` as a live fixture (user-steered).
> Drift from canonical templates is intentional until the structure locks, then packaged.
> See decisions 2026-06-25 "Structure v2 + distillation routines".

File-structure (NOT LLM-dependent — done 2026-06-25):

- [ ] Propagate the updated managed block to the sibling repos (cross-repo propagation still manual; see "Later").
- [ ] Run `horus upgrade-project --apply` in every onboarded repo after upgrading the CLI to ≥0.0.7 — their committed hook files still carry the non-portable `python -m horus` commands (they error on any machine that isn't the one that wrote them; see history.md).

Distillation routines — **agent-delegated prototype shipped 2026-06-25** (pre-pass + emitted prompt, like `close`; runs on any machine with an in-loop agent). Contract in `docs/routines.md`.

- [ ] Autonomous variant (Horus spawns the summarizer/consolidator itself) — deferred to MVP3 with the execution layer.
- [ ] Validate the prototypes by invoking them in a CLI-equipped session on a real project (fabric) and harmonizing the siblings to structure v2.

## Native app layer - cognitive routines as in-app skills/hooks

> The files-only `horus` CLI commands are the deterministic signal layer + the
> headless/fresh-session path. The context-aware LLM parts ship as native Claude
> Code/Codex **skills** that run inside the app, so they see the live context window
> (work/decisions not yet on disk), not just the files. Periodic checks use native
> app **hooks** instead of skills. This pulls the interactive LLM routines out of
> MVP3 — the native app provides the agent runtime + subscription auth + context.
> See decisions 2026-06-25 "Cognitive Routines Ship As Claude Skills" and
> "Native App Functionality Comes Before Horus-Owned Sessions".

Phase 1 — keystone skill + plumbing (done 2026-06-25):

- [ ] Triggering eval follow-up: `claude /login` was completed in the previous session;
  direct `claude -p` probing confirmed real skill triggering works, but the
  skill-creator `run_eval` proxy appeared incompatible with Claude Code 2.1.191 and
  the custom real-mechanism harness had not produced a final matrix before handoff.

Phase 2 — rest of the cognitive layer (done 2026-06-25):

Phase 3 — portability (started with direct Codex skill projection):

- [ ] Evaluate `rulesync` for broader sync/projection — folded into the dedicated
  "Cross-tool interface sync" milestone track below (the 3rd-target trigger).

## Native-app-first feature design

- [ ] Add this lens to future feature specs: "native Claude path", "native Codex path",
  "Horus-owned/session path if needed".

## Upgrade-project direction-awareness

> Found 2026-07-01 while planning the two-machine test; the managed-block half was
> hotfixed in v0.0.4 (`horus-block-version` marker + refusal to downgrade a newer
> block — CLIs ≤0.0.3 remain direction-blind, so on old installs: upgrade the CLI
> first, then refresh). → features.md "Project upgrade / projection refresh".

- [ ] Residual: native hook configs are still pure content comparisons — an old CLI
  reading a repo with newer-generation hooks would offer a downgrade "refresh".
  Version-mark or generation-stamp the hook entries the same way if hook payloads
  start changing between releases.

## Self-update follow-up

> Pill + Update button shipped 2026-07-01 (→ features.md "Dashboard self-update signal").

- [ ] Post-upgrade auto-respawn of the dashboard server (today the banner says
  "restart Horus" — no hot reload). Belongs with the MVP5 lifecycle-unification work,
  not a quick add: the respawn must mind the companion's owned-child reaping and the
  port-8765 reuse/health logic.

## Companion app / mascot - visible Horus presence (next)

Intent: make Horus feel active without prematurely owning agent sessions. The first
app slice should be a tiny always-on-top companion that acts as a doorway to the
dashboard and later becomes the place for continuity/status nudges.

- [ ] Low priority: add a configurable mascot background picker once the companion
  shell has a clean settings surface; the current foreground is generated by
  keying the source export's baked checkerboard preview, so a true-alpha source
  mascot would still make customization cleaner.
- [ ] Surface native hook events, usage threshold warnings, stale summaries,
  uncommitted continuity, and per-project switching.

## Cross-machine central view - lightweight GitHub bridge

> Goal: give the lightweight `uv` tool a central-view feeling for GitHub-backed
> projects before building the proper multi-machine app. GitHub carries durable
> `.horus/` project memory; local machines still own paths, accounts, running
> sessions, and launch state. See decisions 2026-06-28 "Cross-Computer View Starts
> As A Remote Catalog, Not A Runtime".

- [ ] Later proper-app track: machine snapshot aggregation for non-local paths,
  running sessions, account availability, dirty state, and non-git/Google Drive
  projects with explicit project ids.

## MVP 2.5 - Git-aware multi-project overview (next)

> Goal: a trustworthy overview of all projects from any machine. Decided
> 2026-06-25 (see decisions "Git Is The Cross-Machine Transport"): git already
> carries the durable lanes (project/roadmap/decisions/features/history), so the
> overview needs no server, no session hosting, no Tailscale. The gap is that the
> dashboard reads local clones with **no freshness signal** — so make it git-aware.
> Config stays per-machine (paths are local); sessions stay local and distill into
> the committed lanes. Deterministic signal layer only (no LLM), like `doctor`/`close`.

- [ ] "Fetch all" refresh action: `git fetch` across registered projects to update
  behind/ahead. Fetch does not touch the working tree, so the dashboard's
  read-only-on-files invariant holds. Pull (which mutates) is NOT auto-run.
- [ ] Fold staleness into the existing warning/verdict surface (reuse `close`'s
  uncommitted-`.horus/` check): "behind origin — pull to refresh" / "uncommitted
  continuity". Show the exact `git pull --ff-only` command rather than a button.
- [ ] Defer: a one-click pull endpoint (breaks read-only-files invariant — add only
  if showing the command proves too much friction).
- [ ] Optional ops, no code: document `tailscale serve` of the read-only dashboard so
  phone/laptop can glance at *that machine's* view over the tailnet.
- [ ] Optional, YAGNI for now: store each project's remote URL in the registry so the
  same project can be recognized across machines (only if cross-machine dedup is wanted).

## MVP 3 - Agent Execution (the core wedge; next major phase)

> No longer deferred: `claude` 2.1.191 is installed AND logged in on this machine, so
> the subprocess-driving layer is now end-to-end testable here (was the only blocker).
>
> Locked decisions (2026-06-25): build order = spawn + registry FIRST, then the live
> oversight app. First real adapter = Claude Code. Thin owned adapter against a shared
> contract; a fake adapter can validate orchestration anywhere. This phase also unlocks
> autonomous closure + agent-assisted infer.

- [~] **Oversight controls**: actions on a tracked session from the dashboard. The **POST surface
  shipped** (PR #11 — `/launch`, same-origin-guarded, loopback-only; → features.md), which was the
  blocker. Still open: terminate/resume of a *windowed* session from the UI (the in-app PTY
  cockpit path is retired). CLI `horus sessions --prune` covers cleanup today.
- [ ] Persist the registry in SQLite (re-justified once concurrency/scale hurts; JSON file shipped first).
- [ ] Restrict autonomous closure edits to `.horus/**`, `AGENTS.md`, `CLAUDE.md`.
- [ ] **LLM-based `horus infer`** (replaces the removed deterministic version): drive the official CLI to distill `.horus/` from the project's canonical docs — follow doc pointers (README → status/roadmap → CLAUDE.md → linked docs like docs/HISTORY.md), produce clean project + roadmap with planned/in-progress/done items, mark superseded source docs as stale, and prompt the user when intent is unclear.

## MVP 4 - Unified in-app terminal (the cockpit)

> **RETIRED 2026-06-30** (see decisions.md "Retire the Control Cockpit"): the Control tab
> + in-app PTY cockpit is removed from the UI — it overlaps the orchestration surface we
> cede to Omnigent, and it only ever tracked Horus-launched sessions. The code
> (`render_control`, `_terminal_panel`, `pty_host`, `/pty/*`) is left dormant pending
> deletion; `horus run`/`open` CLI remain. Account usage + start/resume moved to the
> Projects tab. The history below is kept for context.
>
> Originally shipped this milestone: the Control tab launches real sessions and hosts them
> as in-app terminals (the real agent TUI under a PTY, rendered with xterm.js). Decided
> 2026-06-26: keep the viewer in Horus (not a VS Code extension), local + persistent +
> re-attachable, cross-platform PTY. See features.md for the capabilities and
> decisions.md ("Unified in-app terminal", "Cross-platform PTY") for the why.

Deferred (noted as future direction, low value for now):

- [ ] **Standalone session-host daemon** — survive a Horus *restart* (today re-attach only
  spans tabs/reloads while the dashboard process runs).
- [ ] **Remote / cross-machine attach** — run the host per machine, attach over a tailnet with
  auth (Tailscale was already reserved for live state). Protocol kept transport-agnostic for this.
- [ ] Session-discovery follow-ups (core shipped 2026-07-01 → features.md "Read-only
  session discovery + Recent sessions panel"): surface a compact recent-sessions hint on
  the *overview* project cards too (detail page only today); optional process-scan layer
  (cwd→project, wants psutil) to tell live sessions from finished ones.
- [ ] Literal OS-level drag gestures / re-dock automation (pop-out covers the practical need).

## Cross-tool interface sync (Claude ↔ Codex ↔ Gemini CLI ↔ Copilot …)

> The differentiator is NOT a new converter — `rulesync` already projects rules/skills/
> commands/MCP across 20+ tools. Horus splits this into two layers and only *owns* the one
> that's inherently its own. See decisions 2026-06-25 "rulesync: stay direct at two tools;
> own the behavioral layer always" and the `codex-plan-review.md` compatibility section.
>
> - **Layer 1 — artifact projection** (instructions, `SKILL.md`, commands, MCP): commodity;
>   `rulesync` does it. Horus stays direct/zero-dep at two tools, adopts rulesync at the 3rd.
> - **Layer 2 — behavioral/semantic adapters** (hook control protocol per tool; usage-signal
>   *source* per tool; per-account config-dir env var): inherently Horus's; never portable.
>   This is where the value is and Horus owns it regardless.

Already shipped (Claude + Codex): dual-write `SKILL.md` to `.claude/skills/` + `.agents/skills/`;
`reconcile instructions` for the `AGENTS.md`↔`CLAUDE.md` managed block; per-tool usage→closure
hooks (Claude OAuth `/usage` + `decision:block`; Codex rollouts + `Stop`).

- [ ] **`horus doctor compat` (observe first)** — per project, report what *each* installed agent
  (claude/codex/gemini/copilot) would actually load: which instruction files, skills, MCP, hooks.
  Read-only; solves the real pain ("which instructions/skills are active here, for this agent?").
  The dashboard-facing half is the "Projection-sync indicator in the UI" item in the UX-hardening
  track above — same underlying comparison, badge form.
- [ ] **Canonical + projections, formalized** — `.horus/compat.toml` declares canonical surfaces
  (`AGENTS.md`, `.agents/skills/`) + per-target projection policy; generated `CLAUDE.md` /
  `.claude/skills/` are marked-generated with drift detection. Extends today's ad-hoc dual-write.
- [ ] **3rd/4th target via rulesync (trigger: Gemini CLI / Copilot)** — shell out to / document
  `rulesync` for Layer-1 projection (`GEMINI.md`, `.cursor/rules`, `.github/instructions/…`),
  never embed (it's npm/Node). Horus wraps it with provenance, diff-before-install, and trust UX.
- [ ] **Per-tool behavioral adapters (Layer 2)** — as each agent gets an execution adapter, add its
  usage-signal source + hook control protocol + config-dir env var (Claude `CLAUDE_CONFIG_DIR`,
  Codex `CODEX_HOME`, …). Pairs 1:1 with the adapter work in MVP3/4.
- [ ] **Skill-projection security/trust** — provenance, diff before install/update, explicit trust
  per project/account, warn on scripts/hooks/MCP/auto-approve, never silently install a
  personal-sourced skill into a work account (projecting into N agents multiplies blast radius).

## Closure ritual hardening (shipped 2026-06-26)

> Why: lanes drifted (stale `current_focus`, growing backlog) despite the ritual
> running several times. Fix keeps LLM-authors / Python-detects. See features.md
> ("Closure freshness gate", "Continuity PR check") + decisions.md.

- [ ] Promote the CI check from advisory to a required gate once proven (drop the
  `|| echo ::warning::` fallbacks).
- [ ] Decide whether `horus init` installs the merge gate by default (`--kind all`)
  or keeps it opt-in; same question for projecting it to Codex if a surface appears.

## MVP 5 - App cohesion / lifecycle (next, after the Codex adaptation)

> Why (flagged 2026-06-26): the app still feels like loosely-wired parts (mascot +
> dashboard server + in-app PTY sessions) rather than one application. Two concrete
> bites surfaced. The goal of this milestone is that Horus reads and behaves as a
> single app — ready for real alpha use, not just a dev harness.

- [ ] **STRUCTURAL fix still open: decouple the session-host lifecycle from a
  dashboard/code reload** — the guard above prevents the *agent* from triggering it,
  but a user restart / crash / code-reload still drops live PTYs. The deferred
  "standalone session-host daemon" (MVP 4) is the real fix (host PTYs in a process that
  outlives the dashboard). Relates to the dashboard-server-leak bug in the companion
  section (no single-instance + no reaping).
- [ ] **Unify the app lifecycle so the pieces act as one app** (flagged 2026-06-26):
  closing the mascot should close the whole app (mascot + dashboard server + hosted
  sessions, with a confirm if sessions are live); closing the dashboard window via its
  UI should terminate the backing process (not orphan it — see the 8765 leak); and the
  reverse — quitting should not leave a stray mascot or server. Today these are
  disconnected: the mascot, the dashboard server, and the PTY host have independent
  lifetimes. Define one ownership/teardown model. Prereq lens for design: the existing
  single-instance mutex (8764) and the dashboard-server-leak fix belong inside this.
  - **Concrete bidirectional bind for the dashboard window** (user note, 2026-06-26):
    the dashboard window today is the Edge `--app=` window opened by `companion.open_dashboard`,
    launched **fire-and-forget** (the `subprocess.Popen` handle is discarded). So (a) quitting
    the mascot leaves that Edge window as a **stale tab**, and (b) closing the Edge window does
    nothing to the mascot/server. Want both directions: quit mascot → close the window; close
    the window → quit mascot + stop server. Goal in the user's words: "feel like an app —
    no stale browser tabs left open." Enabling constraint: a bare `msedge --app=` hands off to
    the user's existing Edge (untrackable, and unsafe to kill — would close their browser), so
    the window must be **owned** (dedicated `--user-data-dir` → its own killable Edge instance
    whose liveness reflects the window) for either direction to work safely.
  - **pywebview was tried for this and REJECTED (2026-06-26)** — live-tested unstable
    (WinForms/WebView2 recursion crash) + slow (~4 s tab) on Win11; reverted to the Edge `--app`
    + Tk mascot shell. See decisions.md "pywebview Tried and Rejected" + history.md. The
    decision split the frontend into two tiers:
  - [ ] **Lightweight tier (SHIPS NOW, via uv): browser tab + Tk mascot** — fast, stable, zero
    heavy deps; refreshed mascot art; app-window mode remains opt-in. **Accepts the lifecycle
    drawbacks for now** (closing the dashboard tab/window doesn't quit the app; the browser owns
    taskbar identity). The bidirectional close↔quit bind is explicitly *deferred to the proper app*,
    not solved here.
  - [ ] **Proper-app tier (PLANNED, separate downloadable package): a real native desktop app**
    that owns the window lifecycle + taskbar icon + tray. **Stack not chosen** — eval PySide6
    (all-Python, heavy) vs Electron (Node, polished) vs Tauri (tiny, Rust+SPA); trade-offs in
    decisions.md. Shares the same Python server + web UI (the stable contract), so it's an
    additive host. This is where "close the window → close the app" and the 8765/single-instance
    fixes land. Also fold in: reliable per-pixel mascot/window transparency on Linux (Tk's
    `-transparentcolor` is Windows-friendly but unreliable under Linux compositors; PySide6/Qt is
    the cleanest Python-native candidate if transparency matters), load account usage async (cold
    `/control` is 750 ms of synchronous OAuth `/usage` calls — measured), and consider client-side
    tab switching.

## Later

- [ ] **One-time continuity-debt paydown (now tooled).** The drift backlog: `horus
  consolidate` reports ~39 roadmap↔features overlaps, ~44 done items without a
  `features.md` row, ~35 sessions to distill. Now a clean, supported job (skill v3's
  "backlog consolidation" mode + `horus close --check` to verify). Distill old sessions,
  move shipped capabilities into `features.md`, cross-reference each split, prune done
  roadmap items — so the freshly-hardened ritual starts from a clean baseline. Sizable;
  dedicated pass, not mid-feature.
- [ ] Optional Telegram bridge.
- [ ] Optional Tailscale-exposed dashboard.
- [ ] Optional VM/worker mode.
- [ ] Optional `rulesync` integration.
- [ ] Optional `horus reconcile instructions --ai`.
- [ ] Optional private session sync outside git.
- [ ] Propagate managed-block content updates across repos when Horus's canonical block changes (currently no mechanism; `reconcile` only syncs the two files within one repo).
