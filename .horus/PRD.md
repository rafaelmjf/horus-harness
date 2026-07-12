---
status: active
current_focus: "Branch fix-consolidated-to-marker fixes the closure hook's self-referential dirty warning: upgrade-project untracks legacy generated markers, init coverage locks the ignore rule, and cleanliness checks exclude their own marker. Full suite: 1220 passed; live tracked-marker repro reports clean. Awaiting PR + required CI; do not merge."
next_action: "Open the consolidated-to-marker PR against main, observe required CI green on its exact head SHA, and stop without merging."
next_prompt: "Resume Horus. Fetch first, read PRD.md and the newest session note, then check the consolidated-to-marker PR. If required CI is green, leave it open for owner review; do not merge unless explicitly asked."
execution_recommendation: "continue-as-is — remaining work is only PR/CI observation; delegation adds no useful context or cost benefit."
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
- **Mobile-web-app bundle:** shipped (see Shipped). `mobile-terminal-ux-hardening` (sizing+lifecycle+controls) implemented, PR #171 open — not merged/shipped pending overseer CDP-gate reproduction + owner on-device verify. Symptom 2 (`mobile-terminal-interaction-regression`, folded-in but tracked) is a separate exposed-mode/POST-path investigation, untouched. [tier: Sonnet]
1. **[ops] Orphan reap after failed runs:** dead workers leave children holding
   ports (ghost probe server on 8899 corrupted a supervisor probe, 2026-07-04).
   On a `failed` RESULT — or `horus reap <session-id>` — kill the session's
   remaining process tree (registry has the pid); at minimum surface "pid still
   has children" in `horus tail`/dashboard.
2. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance
   on the untracked fold (user misread "only public repos visible" when 3 private repos
   were on the ignore list).
3. **[ops] Machine validation leftovers (needs real hardware):** Windows — mascot
   failure dialog + Skills tab; Linux — VS Code task keybindings under Flatpak;
   macOS — mascot/Tk, terminal spawning, owned-window defaults, hook execution.
   install-smoke CI covers install/CLI/`/health` on all three already.
4. **horus-hub follow-ups (harness side):** hub work in `rafaelmjf/horus-hub` (its PRD +
   execution.md). Parked: JSONL heartbeat events; `--worktree` auto-cleanup.
5. **[ops] Measure per-tool-call hook spawn cost:** up to three `horus` processes per
   shell call (close + guard-host + usage guard); only if material, build a single
   `horus pretool --hook` dispatcher (fabric suggestion 2026-07-08). [tier: Haiku
   measure / Sonnet dispatcher]
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
**Concise CLI matrix output** (2026-07-12, PR #169): `capabilities --models`/`--matrix` default table drops `LAST` (per-run outcomes) and shows a short `capability_summary`-or-word-safe-truncated capability column instead of a mid-word-truncated one; `--verbose`/`--full` restores LAST/RESEARCHED and the fuller capability slice; `--stdout` JSON unchanged (still complete, plus the new `capability_summary` field).
**Model-name normalization + datum migration** (2026-07-12, PR #168): real rename (not alias/mirror) — `horus run` canonicalizes captured models via `datums.canonical_model_name` (prefers the adapter's resolved concrete model, e.g. Claude Code's `system/init` event, over a small owner-maintained fallback map); `horus datum migrate-names` idempotently renames bare-alias rows already in `datums.json` in place; `capabilities --models`/`--matrix` render an aligned table (model/tier/datums/last/price/capability/researched) instead of the old vertical block, with strength/caution/guard in a Notes section. `--stdout` JSON shape unchanged.
**Price-for-capability model-roster priors** (2026-07-12, PR #167, code only): `capabilities.toml` owner-prior schema gains optional back-compatible `price_in`/`price_out`/`capability_note`/`researched_at`; `horus capabilities --models`/`--matrix` surface them plus a non-blocking staleness `WARNING` (stderr, exit 0) when the freshest `researched_at` is >14 days old or absent. Populating real price/capability data is a separate agent-run web-research pass, still open (`.horus/backlog/older-models-in-roster.md`).
**Vision / Current-Shape extraction** (2026-07-12, PR #163): the catalog's Shipped-derived capabilities answer "what can it do?" but captured nothing for "what IS it?" — a project's defining frame (agentic-ttrpg: "Claude Code as the runtime, no app to deploy") lived only in `## Vision`, invisible to the catalog. `capabilities.vision_lead` reduces `## Vision` to its markdown-stripped lead sentence (not the whole section) and wires it in as each project catalog's `vision` field (`null` when the section is absent); same best-effort six-lane fallback pattern as the Shipped extractor. 4 new tests; verified against the real agentic-ttrpg catalog.
**Per-project self-documenting capability record** (2026-07-11, PR #159): `horus capabilities --project <name>` (resolved by registered directory basename) — or the self-document default with no `--project` from inside a registered project's root (`capabilities.project_path_for_cwd`) — regenerates that ONE project's record from its live `.horus/` sources (same Shipped-ledger/six-lane-fallback/CLI-surface extraction as the v1 fleet catalog) and writes a provenance-stamped `<project>/.horus/capabilities.json` (`generated_at`/`schema_version`/`horus_version`), also printed to stdout for piping; gitignored. See Rules for the freshness-reconciliation invariant. v1 fleet-wide `horus capabilities`/`--models` unchanged. 13 new tests (30 total in `test_capabilities.py`), full suite 1127 passed.
**Empirical delegation-decision spine** (2026-07-11, PRs #157/#158): `horus/datums.py` — two strictly-separate `~/.horus/` layers, MEASURED datums (`datums.json`, auto-captured by `horus run`) and hand-edited OWNER priors (`capabilities.toml`); `horus datum close` adds the agent-supplied qualitative half (ONLY path that sets `outcome`); `horus capabilities --models` renders a DATA-ONLY roll-up. Three consumer skills in `horus/skills.py` — `delegation-rubric` (single source of truth: task shape → mode+tier via a data-driven tier-trust ladder, same tier-trust dials verification depth), `execution-decision` (in-project: inline vs subagent-plan), `dispatch-decision` (cockpit: inline-here vs dispatched-worker vs dispatched-plan + account routing) — both import the rubric by relative path. HARD BOUNDARY: advisory only, EMITS a recommendation, never auto-selects/routes. 25 new tests, suite green (1114).
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
  shipped items are one line; done backlog items are deleted (git remembers); bugs get
  appended to the backlog as found.
- **`backlog/` (card pilot 2026-07-10, claim gate 2026-07-11):** one card per item,
  `status`/`priority`/`tier`/`created` frontmatter plus optional `parallel: safe|exclusive` /
  `surface: <globs>`; claim via `horus backlog claim <name>` (warns, `--force` to override on
  overlap/exclusive); done = delete the card + a Shipped line here. No stale-`claimed` sweep
  exists — a real gap, not yet built.
- **`sessions/`** unchanged: one note per session (`horus session new`), operational
  facts welcome (gates verified, tokens to rotate, dead ends). Distilled notes →
  `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated` — the tooling reads them PRD-first (`resolve_focus`),
  so no shims are needed. **`next_action` / `next_prompt` / `execution_recommendation` each name
  an explicit model tier** (Haiku/Sonnet/Opus per the model-tier rule). If the user proposes a
  heavier model than the work needs, pushing back for the lower tier is expected, not overstepping.
- **Closure:** update frontmatter + backlog/shipped + session note; run `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
