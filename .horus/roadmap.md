---
status: active
current_focus: "Two-PR refinement of the dashboard + continuity model, both merged to main. PR #51: sumi-e dashboard redesign, light-mode default + theme persistence + Settings control, async performance (project open ~6.5s→instant, index first paint 1.4s→1ms, git_state 235→114ms, mascot unblocked + dashboard pre-warm), and render-to-match (roadmap open-items only, history/decisions open-in-editor). PR (feat/horus-lane-discipline): baked the lane discipline into the horus-consolidate skill (v7) + templates + managed CLAUDE/AGENTS block (Claude+Codex), then reflowed this repo's lanes — decisions.md ~1318→~85 lines of concise topic-grouped current rules, history.md gained a Decision-rationale section, roadmap.md 748→349 lines (completed log dropped). 503 tests green."
next_action: "REVIEW (with the user) the autonomously-completed lane-discipline work now in main, taking the recommended path where a call was pending: (a) confirm the decisions.md topic taxonomy and that collapsing the 68 dated entries lost no current rule; (b) confirm the horus-consolidate v7 routing wording; (c) re-judge the 52 roadmap items carried forward by the mechanical trim — several are likely shipped-but-unticked (e.g. the post-Onboard launch CTA [A6], companion stale-dashboard reaping), so prune them into features.md. All discussed scope (dashboard redesign/perf/render + lane discipline + skills) is merged to main."
next_prompt: "Resume Horus. FIRST `git fetch --all --prune` and verify branch state from the remote. Both refinement PRs are MERGED to main: (#51) the sumi-e dashboard redesign + light-mode-default + async perf + lane render-to-match; and the continuity-model refinement (execution.md phases 2-4) — horus-consolidate skill v7 + templates + managed block now define decisions.md as concise topic-grouped current rules with rationale in history.md, and this repo's lanes were reflowed (decisions ~1318→~85 lines, history gained a Decision-rationale section, roadmap 748→349). All done autonomously taking the recommended path. NEXT is a review pass with the user (see next_action): confirm the decisions taxonomy lost no current rule, the v7 routing wording, and re-judge the 52 carried-forward roadmap open items (some are shipped-but-unticked) — pruning the done ones into features.md. The full pre-reflow decision log is in git. `uv run pytest -q` => 503 passed."
execution_recommendation: "continue-as-is - the phased build (execution.md phases 1-5) is done and merged; what remains is a single-agent review/prune pass with the user, not new multi-surface implementation."
last_updated: 2026-06-30
---

# Roadmap

## Strategy - Omnigent Boundary

> Full evaluation + drift-triggers live in `research/omnigent.md` (the prior-art
> guardrail). Distilled rule in decisions.md "Omnigent Is An Interop Target".

- [ ] (Direction only, not scheduled) First interop seam = a `horus mcp` continuity server any MCP client can read (Omnigent the first consumer); then a thin `horus export omnigent` bundle; dashboard session read-back optional. Revisit only if/when actually adopting Omnigent.

## Context Cache Visibility

- [ ] Decide active behavior for cold/expired sessions: companion warning, launch-flow warning, native hook/statusline projection, or dashboard-only.

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

## Self-update signal - dashboard update button

> Approved 2026-07-01. The artifact-staleness badge covers project-vs-installed-CLI;
> nothing covers installed-CLI-vs-latest-PyPI. Personal tool, so keep it passive +
> one click, no auto-update.

- [ ] Detect a newer `horus-harness` release (PyPI JSON API; cached + async so it never
  blocks a page or fails the dashboard offline) and show an "update available" pill in
  the top nav.
- [ ] Top-nav Update button: run `uv tool upgrade horus-harness`, then cleanly restart
  the dashboard server (a running server can't hot-swap its own code — needs a
  respawn, minding the companion's owned-child reaping and the port-8765 reuse logic)
  and afterwards point at `horus upgrade-project` for refreshing tracked repos'
  projections.

## Companion app / mascot - visible Horus presence (next)

Intent: make Horus feel active without prematurely owning agent sessions. The first
app slice should be a tiny always-on-top companion that acts as a doorway to the
dashboard and later becomes the place for continuity/status nudges.

- [ ] **Residual gap (found 2026-06-29): a stale/orphaned dashboard survives Quit and is
  reused forever.** The 2026-06-28 fix only reaps the dashboard child the *current* mascot
  owns. A dashboard process from an earlier launch (e.g. one orphaned before the fix, or by a
  crash) is not owned by a freshly-opened mascot — and because startup *reuses* any live
  server on 8765, the new mascot adopts the orphan instead of spawning its own, so it never
  owns a child to reap, and Quit leaves the orphan running. The orphan keeps serving its old
  in-memory build across quit/reopen cycles (observed live: PID from 06-26 still on 8765 after
  3 days + multiple quit/reopen; manually killed). Fix options: on startup, verify a reused
  server reports the current `__version__` (and replace it if stale); and/or on Quit, reap any
  `horus dashboard` on 8765 even if not the owned child (guard against killing a user's
  manually-started one). Relates to the MVP5 "decouple session-host lifecycle" item.
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

- [ ] **Ignore/Unignore without a page reload** (user request 2026-07-01): clicking
  Ignore on an untracked GitHub card currently PRGs the whole page; make it remove the
  card in place (small fetch POST + DOM removal, same-origin guard unchanged) so
  several repos can be ignored in one sitting.
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
- [ ] **Monitor sessions Horus did NOT start** (read-only) — discover foreign `claude`/`codex`
  sessions from the transcripts they already write (`~/.claude/projects/<slug>/<uuid>.jsonl`;
  Codex rollouts already read by `codex_usage`), surfacing project/last-activity/message-count.
  **PROMOTED 2026-06-30** as THE session-visibility path now that the Control cockpit is
  retired: this read-only transcript-discovery (no hosting) is what shows *all* sessions
  regardless of how they started — the thing the cockpit's Horus-only live view never could.
  Surface it on the Projects tab (per-project recent sessions). Deferred for now, but it's
  the chosen approach. (Drop the old "continue into a Horus-owned PTY" bridge — no cockpit.)
  Optional process-scan layer (cwd→project) wants psutil.
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

- [ ] **Fetch-first guard on `horus close --push`** (approved 2026-07-01): before
  committing/pushing lanes, `git fetch` and stop with "origin has newer `.horus/`
  commits — pull first" when the remote is ahead on lane paths. The mirror image of
  `horus resume`'s fetch-first pickup; protects the one-person-two-machines flow. No
  locking/merge machinery — git conflict resolution on markdown is the fallback.
- [ ] **Archive session summaries after distillation** (approved 2026-07-01): once a
  summary's durable content is folded into the lanes, move it to
  `.horus/sessions/archive/` instead of leaving it in the active list (56 undistilled
  today). Teach `horus consolidate` to count only non-archived summaries and the
  emitted distillation ritual to do the move.
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
