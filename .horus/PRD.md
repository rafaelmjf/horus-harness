---
status: active
current_focus: "v0.0.34 released and live: PRs #134-136 (`horus fleet`, `--worker` adapter inference, Codex full-auto guidance) are shipped and hosted `/health` confirms 0.0.34. The webhook E2E surfaced a real bug rather than just confirming success: the release-published webhook raced this repo's own publish.yml upload, so the first attempt silently deployed the stale version. Fixed and verified via a proper branch→PR→merge in `horus-hub` (receiver now waits for PyPI to actually advance) plus a webhook redelivery — no manual deploy-hosted.sh run."
next_action: "Opus inline freezes the LaunchBackend seam + LocalBackend before RemoteBackend/ContainerBackend delegation; Refresh-artifacts P1/P2 remains self-contained Sonnet work."
next_prompt: "Resume Horus. FIRST git fetch --all --prune and read .horus/PRD.md. v0.0.34 is released and hosted is confirmed live on it. Use Opus inline for the LaunchBackend + LocalBackend seam freeze (harness P0 of the multi-machine arc)."
execution_recommendation: "continue-as-is — the interface freeze stays Opus inline because its judgment defines every backend contract. plan-execution only after that seam is frozen, when RemoteBackend + ContainerBackend + hub provisioning become high-volume, low-ambiguity cross-repo work suitable for isolated workers."
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

**Card pilot (2026-07-10):** backlog items below "Now / next" live as **one card per
file in `.horus/backlog/`** — frontmatter `status: open|claimed|done` + `priority:
now|next|later|deferred` + `tier` + `created`; the body is a self-contained,
dispatch-ready brief. Add work = add a card (conflict-free); finish = delete the card
+ one Shipped line (git remembers); pick up a card = set `status: claimed`, commit and
push early. "Now / next" here stays the small human-curated order; new cards at
`priority: now` should also get a pointer line there. If two sessions racing this file
was the disease, cards are the treatment — log any friction in session notes (this
pilot is the evidence for/against making cards the scaffold default).

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
   execution.md). Parked: JSONL heartbeat events; `--worktree` auto-cleanup.
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

### Open / deferred — see `.horus/backlog/`

Everything formerly listed here is now one card per file in `.horus/backlog/` (priority
in each card's frontmatter). Notable: `scheduled-usage-aware-continuation`,
`project-machine-requirements`, and `deferred-*` for MVP3/MVP5 + continuity seams.

## Shipped

One line per capability; details in `archive/features.md`, git history, and the READMEs.
**Codex worker posture guidance** (2026-07-10, released v0.0.34): the run help and adapter docs keep `auto-edit` safe while making `full-auto` mandatory and explicit for networked git/PR and local-server/browser verification.
**Worker adapter inference** (2026-07-10): `horus run --worker codex|claude` selects the matching adapter when `--agent` is omitted, while explicit agent/posture flags remain authoritative.
**Fleet dispatch view** (2026-07-10): `horus fleet` prints one line per registered non-cockpit project with git freshness, latest session, and PRD-resolved focus/action/prompt.
**Hosted deploy runtime version gate** (2026-07-10, PR #131 + `horus-hub` #30): exhausted installs fail before restart; `/health.version` must exactly match the target; the hub receiver now waits for PyPI's JSON API to actually advance before deploying, fixing an observed race against this repo's own `publish.yml` upload (webhook E2E now confirmed clean, not just theorized).
**Card-per-file backlog pilot** (2026-07-10): `.horus/backlog/` holds dispatch-ready cards that can be claimed/finished without racing PRD.md; the first Codex claim→push→finish flow was frictionless; `rafaelmjf/horus-agent` is the first cross-project consumer.
**Config round-trip safety** (v0.0.33): `_write_config` preserves unmanaged top-level tables/keys, notably the security-critical `[access]` gate; `deploy-hosted.sh` also pins/retries while PyPI's simple index catches up.
**Dashboard robustness** (2026-07-10): refresh-artifacts P0 refuses dirty checkouts and reports exact paths/policy warnings; live terminals surface dead SSE streams and rejected input instead of failing silently.
**Checkpoint-based incremental consolidation** (2026-07-10): `horus checkpoint --harvest` marker-gates deterministic, idempotent commit-message harvesting into the latest session note and runs from the Stop hook.
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
- **`backlog/` (card pilot 2026-07-10):** one card per item, self-contained brief,
  status/priority/tier in frontmatter; done = delete the card + a Shipped line here;
  `consolidate` sweeps for stale `claimed` cards.
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
