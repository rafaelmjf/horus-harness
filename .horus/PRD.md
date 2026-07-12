---
status: active
current_focus: "Continuity closure + landing PR #177 (research-openwiki-comparison): OpenWiki-vs-self-documenting-catalog research delivered `research/openwiki-comparison-2026-07.md`; overseer+owner endorsed its skip-but-watch recommendation, card stamped shipped. No PR in flight after this merges."
next_action: "No PR in flight. Pick up Backlog 'Now / next candidates': mobile-terminal symptom 2 (exposed-mode/POST-path input regression) is the most concrete open thread; ops item 1 (orphan reap) is the smallest. [tier: Sonnet]"
next_prompt: "Resume Horus. Fetch first, read PRD.md and the newest session notes. No PR is in flight. Choose the next Backlog item — mobile-terminal symptom 2 (exposed-mode input regression) or ops item 1 (orphan reap after failed runs) — and start there."
execution_recommendation: "continue-as-is — next candidates are exploratory investigation (symptom-2 root cause unknown) or a small ops fix; neither is high-volume/low-ambiguity enough to justify a phased plan."
last_updated: 2026-07-12
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
- **Mobile-web-app bundle:** shipped (see Shipped). `mobile-terminal-ux-hardening` (sizing+lifecycle+controls) merged (PR #171). Symptom 2 (`mobile-terminal-interaction-regression`, folded-in but tracked) is a separate exposed-mode/POST-path investigation, untouched. [tier: Sonnet]
1. **[ops] Orphan reap after failed runs:** dead workers leave children holding
   ports (ghost probe server on 8899 corrupted a supervisor probe, 2026-07-04).
   On a `failed` RESULT — or `horus reap <session-id>` — kill the session's
   remaining process tree (registry has the pid); at minimum surface "pid still
   has children" in `horus tail`/dashboard.
2. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance on the untracked fold (user misread "only public repos visible" when 3 private repos were on the ignore list).
3. **[ops] Machine validation leftovers (needs real hardware):** Windows — mascot failure dialog + Skills tab; Linux — VS Code task keybindings under Flatpak; macOS — mascot/Tk, terminal spawning, owned-window defaults, hook execution. install-smoke CI covers install/CLI/`/health` on all three already.
4. **horus-hub follow-ups (harness side):** hub work in `rafaelmjf/horus-hub` (its PRD + execution.md). Parked: JSONL heartbeat events; `--worktree` auto-cleanup.
5. **[ops] Measure per-tool-call hook spawn cost:** up to three `horus` processes per shell call (close + guard-host + usage guard); only if material, build a single `horus pretool --hook` dispatcher (fabric suggestion 2026-07-08). [tier: Haiku measure / Sonnet dispatcher]
6. **Multi-developer continuity (design, evidence-gated):** PRD.md assumes one active
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
**OpenWiki fit research → skip-but-watch** (2026-07-12, PR #177): compared OpenWiki against the Horus capability catalog + PRD continuity (`research/openwiki-comparison-2026-07.md`); overseer+owner endorsed skip-but-watch — no dependency, no competing doc engine now — revisit only if OpenWiki reaches a stable 1.x code mode with evidence across 30+ merged changes in a private polyglot repo, via an opt-in measured pilot (`.horus/backlog/openwiki-vs-self-documenting-research.md`).
**`dashboard --reload`** (2026-07-12, PR #175): restarts a running Horus backend in place from currently-installed code via `/health` discovery + terminate + relaunch on the same host/port (exposed backends restart with `--exposed`); `horus app` polls and respawns its own dashboard child after a crash, never adopting one it didn't spawn.
**Consolidated-to marker stops self-dirtying closure** (2026-07-12, PR #174): `init`/`upgrade-project` scaffold the ignore rule for the generated `.horus/.consolidated-to` marker, `upgrade-project --apply` untracks legacy tracked copies while preserving local state, and closure cleanliness checks exclude the marker so it can never itself fail `working tree clean`.
**Fix Codex usage-limit account scope** (2026-07-12, PR #173): `horus usage check` sources 5h/weekly Codex limits from the newest account-wide rollout (not project-scoped) and flags an expired reset window as stale rather than current capacity.
**Mobile/desktop terminal sizing + lifecycle + controls hardening** (2026-07-12, PR #171): `.xterm-host` fills its region via `ResizeObserver` + layout-settled initial fit (no stale 80×24 default); live `matchMedia` re-evaluation instead of load-once mobile/desktop latch; tabs reachable in fullscreen; larger tap targets; confirm-guard on closing a live session. Symptom 2 (exposed-mode/POST-path no-input regression) is untouched, tracked separately in Backlog.
**Backlog card ship-lifecycle provenance** (2026-07-12, PR #172): `horus backlog ship <slug> --pr N --sha SHA` stamps `status: shipped` + PR/SHA in place; `backlog list`/`fleet --backlog` hide shipped cards by default (`--all`/`--shipped` opt in); `close --check` warns when a card carries shipped provenance but is still `open`.
**Capabilities table rendering + model-name normalization** (2026-07-12, PRs #167/#168/#169): `capabilities --models`/`--matrix` render an aligned model/tier/datums/last/price/capability/researched table (concise default drops LAST/RESEARCHED, `--verbose`/`--full` restores them); `horus run` canonicalizes captured model names via `datums.canonical_model_name` (adapter-resolved model preferred over a small fallback alias map), `horus datum migrate-names` migrates existing rows in place; `capabilities.toml` owner priors gained optional `price_in`/`price_out`/`capability_note`/`researched_at` plus a >14-day staleness `WARNING`. Real price/capability data for older models is still open (`.horus/backlog/older-models-in-roster.md`). `--stdout` JSON shape unchanged throughout.
**Per-project capability record + Vision extraction** (2026-07-11/12, PRs #159/#163): `horus capabilities --project <name>` (or the self-document default from inside a registered project's root) regenerates that ONE project's record from its live `.horus/` sources and writes a provenance-stamped, gitignored `<project>/.horus/capabilities.json`; `capabilities.vision_lead` adds each project's markdown-stripped `## Vision` lead sentence as the catalog's `vision` field (`null` when absent), answering "what IS it?" alongside the Shipped-derived "what can it do?". v1 fleet-wide `horus capabilities`/`--models` unchanged; see Rules for the freshness-reconciliation invariant.
**Empirical delegation-decision spine** (2026-07-11, PRs #157/#158): `horus/datums.py` MEASURED datums + hand-edited OWNER priors, `horus datum close`, `horus capabilities --models` data-only roll-up; three consumer skills — `delegation-rubric`, `execution-decision`, `dispatch-decision` — share the rubric by relative import (see Rules for the advisory-only boundary).
**Mobile-web-app bundle + dashboard resilience** (2026-07-11, PRs #149/#151/#153/#155): `usage-reset-inference`, `pwa-installable` (`/manifest.json` + `/sw.js`, cache-first ONLY for a fixed static app-shell whitelist), `responsive-mobile-pass`; `_project_column_safe` renders a per-project `failed to load` error card instead of 500ing the whole projects section on one bad registry entry — full detail in git history; `mobile-terminal-interaction-regression` remains open (Backlog).
**LaunchBackend seam** (2026-07-10/11, PRs #144/#147): `horus/backend.py`'s minimal contract (`launch(brief)->handle · status · stream · stop`) backs a behavior-preserving `LocalBackend`; `horus open` + the dashboard's OS-window launch route through it. Omnigent evaluated as an optional backend (fits Linux native + managed containers, rejects native Windows, same-host multi-subscription isolation left Unknown) and stays undepended-on. Config-driven target selection stays deferred pending hub's `[[targets]]`-or-equivalent contract.
**Ops & fleet-reporting hardening** (2026-07-10, PRs #131/#137/#139/#140/#141/#142/#143/#148, v0.0.33-35): honest dispatch receipts (`horus/delivery.py` derives pushed-SHA/PR/continuity-closed post-hoc for a non-clean `horus run`); usage-preflight reads both 5h+weekly windows; `horus run --effort` passthrough to both adapters; `status`/`fleet` fetch-first gone-branch/staleness attribution; the v1 fleet capability catalog prototype (superseded by the per-project mode above); refresh-artifacts honors workflow policy; Codex worker posture + adapter inference; hosted-deploy version gate; `.horus/backlog/` card parallel-safety claim gate; config/dashboard/checkpoint round-trip hardening.
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
- **Capability catalogs stay idempotent EXCEPT the per-project stamp, by design
  (2026-07-11).** The fleet-wide catalog has no timestamps (pure function of
  sources, unchanged run = no write). `horus capabilities --project <name>`
  (or the self-document default) deliberately relaxes this ONE way: its
  `generated_at` stamp refreshes every run — the file is a regenerate-on-read
  publishing artifact, never a cache read back — while the `project` payload
  underneath stays just as idempotent. Don't "fix" the stamp, and don't let
  the relaxation creep into the fleet-wide catalog.
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
- **Platform traps:** `uv tool install horus-harness` without `--python 3.12` silently resolves
  an ancient version below the floor — compare `horus --version` with `uv run horus --version`,
  `--force --python 3.12` reinstall + restart. A **stale `pip`-installed `horus` on PATH shadows
  the uv shim** (v0.0.28 `doctor machine` flags it). Also: ctypes needs argtypes/restype;
  Windows GUI under `pythonw.exe` + reap the tree; pin CI actions to real tags; probe the HTTP
  server, not the companion.

## Structure contract (prototype)

- **This file** carries vision, backlog, shipped, rules. Keep it under ~250 lines: new
  shipped items are one line; card-backed work stays in `backlog/` as `status: shipped`
  with PR/SHA provenance; bugs get appended to the backlog as found.
- **`backlog/` (card pilot 2026-07-10, claim gate 2026-07-11):** one card per item,
  `status`/`priority`/`tier`/`created` frontmatter plus optional `parallel: safe|exclusive` /
  `surface: <globs>`; claim via `horus backlog claim <name>` (warns, `--force` to override on
  overlap/exclusive); after merge, `horus backlog ship <name> --pr N --sha SHA` flips the card
  in place and records provenance. `close --check` warns on lingering-done or shipped-but-open
  cards. No stale-`claimed` sweep exists — a real gap, not yet built.
- **`sessions/`** unchanged: one note per session (`horus session new`), operational
  facts welcome (gates verified, tokens to rotate, dead ends). Distilled notes →
  `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated` — the tooling reads them PRD-first (`resolve_focus`),
  so no shims are needed. **`next_action` / `next_prompt` / `execution_recommendation` each name
  an explicit model tier** (Haiku/Sonnet/Opus per the model-tier rule). If the user proposes a
  heavier model than the work needs, pushing back for the lower tier is expected, not overstepping.
- **Closure:** update frontmatter + backlog/shipped + session note; run `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
