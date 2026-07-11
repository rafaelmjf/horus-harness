---
status: active
current_focus: "Empirical delegation-decision spine Slice 1 shipped (2026-07-11, PR #157, branch feat/capabilities-empirical-datums — CI green on head 0491401: freshness + pytest 3.12/3.13, 1109 passed). New horus/datums.py: fleet-global measured-datum store (~/.horus/datums.json, backfilled) + owner priors (~/.horus/capabilities.toml, hand-edited, seeds the gpt-5.6 caution) + exit classifier (completed/crashed/usage-death). `horus run` auto-writes a mechanical datum row at launch+completion (zero agent overhead, best-effort); `horus datum close <run-id> --outcome/--shape/--note` adds the agent-supplied qualitative half; `horus capabilities --models` renders a DATA-ONLY roll-up joining both layers. HARD BOUNDARY held: harness measures+displays, agent judges — advisory, never a router/policy/spend engine. Slice 1 STOPS at measure+display; the two consumer skills are a separate dispatch."
next_action: "Slice 2 of the delegation framework (SEPARATE dispatch, not started): the two consumer skills — in-project `horus-execution` subagents + multi-project cockpit dispatch — sharing ONE calibration+verification rubric that READS the Slice 1 data (datums.json + capabilities.toml via `horus capabilities --models`). Design the shared rubric first; keep the measure/display-vs-judge boundary. Meanwhile the pre-existing open threads remain: mobile-terminal-interaction-regression (.horus/backlog/, high), the parallel-safety multi-worker contention test (PR #148), accounts-refresh-button-invisible (medium, one-line CSS). [tier: Opus for the rubric design; Sonnet for the bug cards.]"
next_prompt: "Resume Horus. FIRST git fetch --all --prune and read .horus/PRD.md plus the newest .horus/sessions/ note. Slice 1 of the empirical delegation spine shipped (PR #157) — measured datums + owner priors + `horus capabilities --models` roll-up, all data-only. Slice 2 is the two consumer skills + shared calibration/verification rubric reading that data (Opus design). Alternatively pick an open thread: mobile-terminal-interaction-regression (.horus/backlog/, high), parallel-safety multi-worker contention test (PR #148), or accounts-refresh-button-invisible (one-line CSS)."
execution_recommendation: "plan-execution for Slice 2 (rubric spans two consumer skills across horus-harness + horus-agent, real ambiguity — design on Opus, then likely delegated implementation). continue-as-is for any of the open bug threads (single-focus, Sonnet)."
last_updated: 2026-07-11
horus_min_version: 0.0.26
---

# Horus — PRD

The one maintained continuity file: **PRD.md + sessions/** (prototype, 2026-07-03).
Tooling reads its frontmatter directly; the deleted shims and retired lanes remain in
`archive/` and git history.

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

**Card pilot (2026-07-10):** deferred items live one-per-file in `.horus/backlog/`;
"Now / next" stays the small human-curated order.

### Now / next candidates

- **★ [flagship] LaunchBackend seam — remaining slice blocked on hub.** See Shipped
  for what landed. Only remaining work is config-driven target/machine selection,
  gated on hub writing a `[[targets]]`-or-equivalent contract (not present as of hub
  HEAD `4a2b2ee` §9). Do NOT build an `OmnigentBackend` yet — blocking gates unmet
  (`research/omnigent-fit-2026-07-10.md`). [tier: Sonnet wiring once hub's contract lands.]
- **Mobile-web-app bundle (sequential, one card at a time — mostly share
  `horus/dashboard.py`, do not parallelize):** `usage-reset-inference`,
  `usage-refresh-button`, `pwa-installable`, and `responsive-mobile-pass`
  shipped (see Shipped). Remaining: `mobile-terminal-interaction-regression`
  (high — in-app terminal takes no input on hosted/mobile), open card in
  `.horus/backlog/`. [tier: Sonnet]
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
   owned-window defaults, hook execution — install-smoke CI covers install/CLI/`/health`.
5. **horus-hub follow-ups (harness side):** hub work in `rafaelmjf/horus-hub` (its PRD +
   execution.md). Parked: JSONL heartbeat events; `--worktree` auto-cleanup.
6. **[ops] Measure per-tool-call hook spawn cost:** up to three `horus` processes per
   shell call (close + guard-host + usage guard); only if material, build a single
   `horus pretool --hook` dispatcher (fabric suggestion 2026-07-08). [tier: Haiku
   measure / Sonnet dispatcher]
7. **Multi-developer continuity (design, evidence-gated):** PRD.md assumes one active
   workstream — two devs closing sessions collide on frontmatter. Direction:
   per-workstream focus (frontmatter keyed by branch/dev, or `.horus/focus/<name>.md`)
   aggregated by `resolve_focus`/dashboard/`resume`. Per the ladder rule, design now,
   build when a real second developer arrives. [tier: Opus design]

### Open / deferred — see `.horus/backlog/`

Everything formerly listed here is now one card per file in `.horus/backlog/` (priority
in each card's frontmatter). Notable: `scheduled-usage-aware-continuation`,
`project-machine-requirements`, and `deferred-*` for MVP3/MVP5 + continuity seams.

## Shipped

One line per capability; details in `archive/features.md`, git history, and the READMEs.
**Empirical delegation spine — Slice 1** (2026-07-11, PR #157): new `horus/datums.py` turns hand-written model-calibration prose into a measured loop, two strictly-separate layers under `~/.horus/`. MEASURED datums (`datums.json`, single-JSON-keyed-by-session-id like the registry, backfilled with the known datums — Sonnet 5 = 10 clean, Opus 4.8/Fable 5/gpt-5.6/gpt-5.5 ~1 each, Haiku 4.5 = 0) are written mechanically by `horus run` at launch+completion (model/effort/account/agent/worker/posture/wall-clock-runtime/exit ∈ completed|crashed|usage-death; token/PR/CI reserved-None; best-effort so measuring never breaks a run). OWNER priors (`capabilities.toml`, hand-edited, seeded once — tier tags + the real gpt-5.6 strength/token-hungry-caution/usage-ceiling-guard) shape HOW to use a model. `horus datum close <run-id> --outcome {clean|nudged|bounced|died} --shape --note` (prefix-matched) adds the agent-supplied qualitative half — the ONLY path that sets `outcome`. `horus capabilities --models` renders a DATA-ONLY roll-up joining both layers (tier + clean count + last-N outcomes + owner flags; `--stdout`→JSON). 20 new tests, suite green (1109). The two consumer skills + shared rubric are Slice 2 (separate dispatch).
**Projects-section resilience** (2026-07-11, PR #155): one registered project raising while rendering its card (concrete trigger: a registered path with no `.horus/` dir, via `_resume_html` → `routines.resume_prompt` → `resume_context` raising `FileNotFoundError`) used to 500 the entire dashboard projects section for every project. `horus/dashboard.py` gains `_project_column_safe` — the single join site feeding both `/projects-grid` and `render_index`'s non-defer path — which renders a compact `failed to load: <reason>` error card for just the bad project on any exception; `routines.resume_prompt` also now degrades to `""` for the concrete no-`.horus/`-dir case instead of raising. Verified: 4 new regression tests, full suite green (1089 passed), CI green, and a live probe against a real registry with one broken + one good project (HTTP 200, both render).
**Responsive mobile pass** (2026-07-11, PR #153): five phone-width CSS overflow bugs fixed in `horus/dashboard.py`'s inline `_STYLE` (media queries/flex-wrap/`minmax(0,1fr)`, no framework, desktop unchanged) — the fixed-height header row pushed the theme toggle off-screen on every page; five `auto-fill` card grids had a `minmax()` floor wider than any phone (a bare `1fr` override doesn't fix this, needs explicit `minmax(0,1fr)` per the grid spec); the launch form's Resume/Fresh-session buttons lacked `flex-wrap`; the Sessions page's 8-column live-sessions table had no horizontal-scroll rule (`.card table` now mirrors `.panel table`). Verified via Playwright + system chromium against an isolated dashboard instance seeded with this repo's real projects/sessions: no horizontal overflow at 320/375/768px on every page, nav/launch button/terminal reachable, desktop unchanged, full suite green (1085 passed). Incidental find, filed separately not fixed here: `accounts-refresh-button-invisible` (the PR #150 refresh button is `opacity:0` on every viewport, not just mobile).
**PWA installability** (2026-07-11, PR #151): `GET /manifest.json` (`application/manifest+json`; sumi-e `--bg`/`--seal` colors, standalone display, 192/512 icons resized from the existing `icon.ico` mascot) + `GET /sw.js` (`text/javascript`), wired into the shared page head; the service worker cache-first-precaches ONLY a fixed whitelist of static app-shell assets (icon PNGs + vendored xterm CSS/JS) — every HTML page and data/API route (`/accounts-*`, `/projects-grid`, `/health`, `/pty/*`, …) always hits the network, never cache, since the dashboard sits behind Cloudflare Access. Side-fix: `pyproject.toml` package-data was silently excluding `icon.ico`/`vendor/xterm/*` from the published wheel (verified via the installed 0.0.35 RECORD) — fixed, or the SW's `cache.addAll()` would 404 in production.
**Usage-refresh-button, cheap-cache-reread scope** (2026-07-11): dashboard accounts strip gains a "refresh (cached)" control (`GET /accounts-refresh`) that re-reads `usage_snapshot`'s on-disk cache via new `usage_snapshot.read_cache_only` (no live-fetch fallback) and reapplies `_reset_window_display`'s past-reset inference against wall-clock time — zero network call, no CLI turn; Codex was already disk-only and needed no change.
**Usage-reset-inference** (2026-07-11, PR #149): dashboard usage display (accounts strip/panel + Codex session-card fallback) reuses PR #145's expired-window rule on the display side — a cached window past its `resets_at` renders "window reset — capacity available" instead of the stale percent, never a fabricated 0%, no extra network/cache call (`horus/dashboard.py`'s `_reset_window_display`).
**LaunchBackend seam frozen, then made load-bearing** (2026-07-11): `horus/backend.py` fixes the minimal contract `launch(brief)->handle · status · stream · stop` with a behavior-preserving `LocalBackend` (native-Windows/other targets honestly refused, no fallback; Omnigent stays optional/undependend); `horus open` and the dashboard Control-tab OS-window launch (`POST /launch`) now route through `backend.LocalBackend().launch(...)` instead of calling `launch.launch_interactive` directly — same identity guard/registry row/terminal spawn. Config-driven target selection stays deferred pending hub's `[[targets]]`-or-equivalent contract (not yet written as of hub HEAD `4a2b2ee`); a TODO marks the plug-in point in `dashboard.py` rather than inventing one. Full suite green (1052 passed) + a live `horus open` probe (real registry row + spawned OS process).
**Omnigent LaunchBackend fit spike** (2026-07-10, PR #144): source-grounded matrix (`research/omnigent-fit-2026-07-10.md`) — optional backend fits Linux native + named managed containers, rejects native Windows, leaves same-host multi-subscription isolation Unknown pending a two-account E2E; Horus stays the memory plane.
**Honest dispatch receipts** (2026-07-10, PR #143): a non-clean `horus run` session (`failed`/`stale`) no longer collapses to a bare status — new `horus/delivery.py` derives pushed SHA / opened PR / continuity-closed post-hoc from the worker's own worktree/branch on disk (`integration.pr_for_branch` new, not scoped to `horus/`-prefixed branches), rendered as `<status>-but-delivered · pushed <sha> · PR #N · continuity closed` alongside the real status; `horus sessions` also now sorts running-first/recency and hides rows idle >24h behind a new `--all` flag (`registry.is_recent`). Every probe degrades to nothing on a gone branch or git/gh failure.
**Usage-preflight hardening** (2026-07-10, PR #141, released v0.0.35): `horus run`'s preflight now reads BOTH the 5h and weekly windows and gates on the more-constraining one (`UsageSnapshot` gains defaulted weekly fields + `worst()`, cache round-trips both); a `[50,80)` closing-window `Note:` surfaces percent+reset (visibility, not a runtime predictor); an unknown signal is surfaced (`capacity unknown …`) instead of proceeding as if healthy, with opt-in `--refuse-on-unknown` for critical launches — the PreToolUse guard's fail-open hot path is deliberately untouched.
**Reasoning-effort passthrough** (2026-07-10, PR #140, released v0.0.35): `horus run --effort {low,medium,high,xhigh,max}` reaches both adapters via `SpawnSpec.effort` — claude forwards `--effort` verbatim (documented enum, confirmed live); codex maps to `-c model_reasoning_effort=<value>` (server-validated).
**Fleet truth + source attribution** (2026-07-10, PR #142): `horus status`/`horus fleet` (one line per registered non-cockpit project) do a read-only TTL-cached `git fetch` (reusing the `fetchcheck` primitive) then flag a checkout on a merged-and-deleted branch (`⚠ upstream gone`, `vs <default>: +N/-M` via `for-each-ref`/`origin/HEAD`), name which continuity file backed the row (`continuity_source`, always the working-checkout copy), and hint when the local default branch is meaningfully behind origin — reporting-layer only, no auto-pull, no prose edits. Live-verified: caught `fabric-metadata-driven-medallion`'s actual gone branch.
**Fleet capability catalog prototype** (2026-07-10, draft PR #139): `horus capabilities` aggregates every registered project's Shipped ledger (+ harness's own 52-command argparse surface) into a deterministic queryable JSON index at `~/.horus/capabilities.json` — agent-first alternative to the `horus wiki` spike (#138).
**Refresh-artifacts honors workflow policy** (2026-07-10, PR #137): the dashboard's Refresh artifacts action now dispatches through `integration.integrate()` for an automatic commit policy — branch + PR (+ automerge) instead of dirtying a `branch-pr-automerge` repo's main — closing `bugs/refresh-artifacts-leaves-dirty-worktree.md` and the downstream `bugs/checkpoint-warning-after-artifact-refresh.md` symptom (both write-ups deleted, resolved).
**Codex worker posture guidance + adapter inference** (2026-07-10, v0.0.34): run help/adapter docs keep `auto-edit` safe while making `full-auto` mandatory for networked git/PR and local-server/browser verification; `horus run --worker codex|claude` selects the matching adapter when `--agent` is omitted (explicit flags stay authoritative).
**Hosted deploy runtime version gate** (2026-07-10, PR #131 + `horus-hub` #30): exhausted installs fail before restart; `/health.version` must exactly match the target; the hub receiver now waits for PyPI's JSON API to actually advance before deploying, fixing an observed race against this repo's own `publish.yml` upload (webhook E2E now confirmed clean, not just theorized).
**Backlog card parallel-safety gate** (2026-07-11, PR #148; pilot 2026-07-10): `.horus/backlog/` holds one dispatch-ready card per file (`rafaelmjf/horus-agent` is the first cross-project consumer); cards gain optional `parallel: safe|exclusive` + `surface: <globs>` frontmatter (back-compat) and new `horus/backlog.py` — `horus backlog list`/`claim <name> [--force]` warn-and-block a claim that overlaps an in-progress card's surface, or where either card is `exclusive`, or where overlap can't be verified (missing surface). Prerequisite gate before a multi-worker contention test on a shared backlog. Note: the claim→push→finish flow and any stale-claimed-card sweep remain a manual git/PRD convention, not (yet) enforced by `consolidate` — see Structure contract.
**Config/dashboard/checkpoint hardening** (v0.0.33/2026-07-10): config round-trip preserves unmanaged tables incl. the security-critical `[access]` gate; refresh-artifacts refuses dirty checkouts; live terminals surface dead SSE streams; `horus checkpoint --harvest` marker-gates idempotent commit-message harvesting from the Stop hook.
**Continuity core:** init/close/session/doctor/consolidate/distill/infer/reconcile; PRD+sessions v3; fetch-first freshness/merge gates; sessions archive/resume; brainstorm/orchestration and JSONL run-event/worktree/worker foundations.
**Hooks & projections:** cross-agent usage/closure and pre-merge hooks; upgrade/sync/skill-map surfaces; usage-limit survival kit; commit/push checkpoints; version-floor and shadow-install guards; stale-dashboard scan; `--exposed` boundary; cross-shell fetch-first block-v7 bundle.
**Dashboard:** read-mostly async multi-project UI; project/session/cache/PR/usage views; accounts/settings/self-update/startup visibility; reviewed sessions; mobile terminal; GitHub-owner and local-project add flows.
**GitHub bridge:** cached remote discovery, onboard/integrate policy with private-repo fallback, default-branch restoration, catalog dedup/tracking/ignore controls, and `horus start`.
**Execution & adapters:** Fake/Claude/Codex adapters, multi-account run/open/focus, workflow handoffs, worker marking, hub orchestration, run logs/tail/watch/status, and aware-UTC registry timestamps; in-app PTY cockpit retired.
**Companion & launch:** cross-platform Tk mascot, worker badges, owned dashboard windows, VS Code resume/fresh tasks, and same-version `/health` adoption.
**Distribution:** PyPI trusted publishing, floor/latest pytest + compileall, three-OS post-publish install smoke, Apache-2.0.

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
- **One fetch-first primitive, reused, not reinvented.** `fetchcheck.fetch_and_state`
  (TTL-cached, read-only `git fetch --all --prune`, never a pull) is the single fetch
  path for every reporting surface that needs fresh remote-tracking refs — the
  session-start hook and `status`/`fleet`'s gone-branch/staleness signals (2026-07-10)
  both call it rather than each shelling a fetch of their own.
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
  the suite *after* the bump (the stale-build guard test catches a skew). Verify
  publish→install E2E (PyPI JSON+simple index serve it, then a clean-venv install shows
  it) — a green `publish.yml` alone bit back on v0.0.34. Hosted-version verification is
  no longer a plain `/health` curl: the hosted dashboard now sits behind Cloudflare
  Access — confirm the flip via Access-authenticated access or deploy-hook logs (v0.0.35).
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
- **Model-calibration data measures; the agent judges (empirical spine, 2026-07-11).**
  `horus/datums.py` MEASURES and DISPLAYS — never a router/policy/spend engine (the
  `research/omnigent.md` drift trigger). Measured datums (`~/.horus/datums.json`,
  auto-captured by `horus run`) and hand-edited owner priors
  (`~/.horus/capabilities.toml`) stay separate layers. `outcome`
  (clean/nudged/bounced/died) is ALWAYS agent-supplied via `horus datum close`, never
  auto-scored; `horus capabilities --models` and every future consumer emit DATA ONLY —
  no model pick, no `--for` router, no auto-routed dispatch. Exit
  (completed/crashed/usage-death) is the mechanical axis, orthogonal to quality.
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
- **`backlog/` (card pilot 2026-07-10, claim gate 2026-07-11):** one card per item,
  `status`/`priority`/`tier`/`created` frontmatter plus optional `parallel:
  safe|exclusive` / `surface: <globs>`; claim via `horus backlog claim <name>`
  (warns, `--force` to override on overlap/exclusive); done = delete the card + a
  Shipped line here. No stale-`claimed` sweep exists (this bullet wrongly claimed
  one before 2026-07-11) — a real gap, not yet built.
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
- **Closure:** update frontmatter + backlog/shipped + session note; run `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
