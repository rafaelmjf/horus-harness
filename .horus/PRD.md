---
status: active
current_focus: "PR #217 (backlog card reviews: append-only `## Reviews` convention + `horus backlog review` + TUI e/r edit keys with offered fetch-first commit+push; also gitignores backlog/.claim.lock) open with CI green, awaiting owner live verification + merge. Release cut still pending and should include it."
next_action: "Owner verifies PR #217 live (edit + review a card from `horus tui`, confirm commit+push lands) and merges; then cut the release: three-file version bump + install-smoke CI on all three OS + hosted deploy. [Haiku mechanical once #217 lands]"
next_prompt: "Resume Horus. Fetch first. If PR #217 is merged, ship-stamp is not needed (no card backs it) — proceed to the release cut: three-files-together bump, verify publish→install E2E, then run deploy-hosted.sh. Do not merge PRs yourself."
execution_recommendation: "continue-as-is — remaining steps are owner verification and a mechanical release cut, no ambiguity."
last_updated: 2026-07-14
horus_min_version: 0.0.26
---

# Horus — PRD

The one maintained continuity file: **PRD.md + sessions/** (prototype, 2026-07-03). Tooling reads its frontmatter directly; retired lanes remain in `archive/` and git history.

## Vision

Horus is a lightweight, project-centric **continuity layer** for official coding-agent CLIs (Claude Code, Codex, more later). The durable value is the memory plane, not orchestration:

- repo-local `.horus/` files that any native agent session can use without Horus running;
- a read-mostly dashboard: projects, current focus, next step, sessions, accounts/usage;
- a closure ritual so work never disappears into a stale conversation;
- visibility into which agent/account/environment touched a project.

Model concretely: `project + agent + account + environment + session` — no abstract identity profiles. Native-app-first: design capabilities on Claude/Codex's own surfaces before a Horus-owned session layer. Execution planes own orchestration (see `research/omnigent.md`); Horus stays the memory plane and interops via `.horus/`.

**Out of scope:** multi-user SaaS, agent marketplace, distributed worker control plane,
identity abstraction, memory beyond repo-local continuity.

**Continuity value finding (2026-07-03):** the proven spine is resume frontmatter +
session notes + fetch-first; the six-lane taxonomy was the overhead — hence this PRD.

## Backlog

Prioritized open work. Features and bugs in one list; jump order is allowed — this list
is a menu, not a contract. Mark bugs **[bug]**, ops chores **[ops]**.

### Now / next candidates

- **★ [flagship] LaunchBackend seam — remaining slice blocked on hub.** Only config-driven target/machine selection remains, gated on hub writing a `[[targets]]`-equivalent contract (absent at hub HEAD `4a2b2ee` §9). Do NOT build `OmnigentBackend` yet (`research/omnigent-fit-2026-07-10.md`). [tier: scoped implementation once contract lands]
1. **[ops] Orphan reap after failed runs (process-tree, distinct from the tmux reaper below):** dead workers leave children holding ports (ghost probe server on 8899 corrupted a supervisor probe, 2026-07-04; 2026-07-12: a setsid-detached dashboard orphan served the hosted app for 7h — systemd showed dead, deploys no-opped "already running"; deploy-hosted.sh's version check caught it). On a `failed` RESULT, kill the session's remaining process tree (registry has the pid); at minimum surface "pid still has children" in `horus tail`/dashboard. Cross-platform process-tree walking, not tmux-specific — needs its own execution decision.
2. **Catalog niceties:** badge private repos in the GitHub catalog; "N ignored" affordance on the untracked fold (user misread "only public repos visible" when 3 private repos were on the ignore list).
3. **[ops] Machine validation leftovers (needs real hardware):** Windows — mascot failure dialog + Skills tab; Linux — VS Code task keybindings under Flatpak; macOS — mascot/Tk, terminal spawning, owned-window defaults, hook execution. install-smoke CI covers install/CLI/`/health` on all three already.
4. **horus-hub follow-ups (harness side):** hub work in `rafaelmjf/horus-hub` (its PRD + execution.md). Parked: JSONL heartbeat events; `--worktree` auto-cleanup.
5. **[ops] Measure per-tool-call hook spawn cost:** up to three `horus` processes per shell call (close + guard-host + usage guard); only if material, build a single `horus pretool --hook` dispatcher (fabric suggestion 2026-07-08). [tier: Haiku measure / Sonnet dispatcher]
6. **Multi-developer continuity (design, evidence-gated):** PRD.md assumes one active workstream, so two closers collide on frontmatter. Direction: per-workstream focus keyed by branch/dev, aggregated by `resolve_focus`/dashboard/`resume`; build when a real second developer arrives. [tier: Opus design]

### Open / deferred — see `.horus/backlog/`

Everything formerly listed here is one card per file in `.horus/backlog/`. Notable: `scheduled-usage-aware-continuation`, `project-machine-requirements`, and `deferred-*` for MVP3/MVP5 + continuity seams.

## Shipped

One line per capability; details in `archive/features.md`, git history, and the READMEs.
**Scoped tmux mouse mode + TUI launch-defaults screen** (2026-07-13, PR #215): session-scoped mouse fixes wheel-scroll recall; `d`-key Defaults screen persists launch posture. v0.0.52 attach gate PASS (owner-verified): web-launched session attached from Termius/`horus tui`, detach/reattach clean.
**Guarded tmux orphan-reaper** (2026-07-13, PR #214): `reap_orphans()` kills only on positive confirmation (matching registry + terminal status + idle grace).
**Unified terminal project cockpit** (PRs #195–#213, v0.0.46–0.0.52): responsive phone/desktop TUI with KPIs, scrolling, unified Resume/Fresh, backlog-card resume, live-session controls; managed tmux attachment across viewers; graceful fallbacks.
**Ops & UX hardening batch** (2026-07-12, PRs #171–#177): `dashboard --reload` + `horus app` child respawn; consolidated-to gitignore marker (no self-dirtying closure); Codex usage account-wide scope fix; mobile terminal sizing/lifecycle/controls hardening; backlog `ship` PR/SHA provenance + `close --check` shipped-but-open warning; OpenWiki skip-but-watch verdict.
**Terminal multi-viewer/mobile stack + verified Claude phone route** (PRs #178–#191, v0.0.36–0.0.45): phone-width spawn, retained exits, SSE reset markers; native iOS Tailscale SSH → tmux path verified reliable.
**Windows CLI un-broken** (2026-07-13, PR #181): lazy import of Unix-only `fcntl`; install-smoke green all three OS.
**Capabilities table rendering + model-name normalization** (2026-07-12, PRs #167–#169): `--models`/`--matrix` render aligned tables; canonicalized model names; owner-prior price/capability/note fields; staleness WARNING.
**Per-project capability record + Vision extraction** (2026-07-11/12, PRs #159/#163): per-project `capabilities.json` regenerate-on-read artifact; Vision lead in catalog; fleet-wide catalog unchanged.
**Empirical delegation-decision spine** (2026-07-11, PRs #157/#158): MEASURED datums + owner priors + three consumer skills; data-only roll-up, no auto-routing.
**Mobile-web-app bundle + dashboard resilience** (2026-07-11, PRs #149/#151/#153/#155): PWA-installable, per-project error card isolation.
**LaunchBackend seam** (2026-07-10/11, PRs #144/#147): minimal contract; LocalBackend; Omnigent optional, undepended-on; config target selection deferred.
**Ops & fleet-reporting hardening** (2026-07-10, PRs #131–#148, v0.0.33–0.0.35): honest dispatch receipts; both-window usage preflight; fetch-first staleness signals.
**Continuity core:** init/close/session/doctor/consolidate/distill/infer/reconcile; PRD+sessions v3; fetch-first gates; worker foundations.
**Hooks & projections:** cross-agent usage/closure hooks; upgrade/sync surfaces; version-floor guard; `--exposed` boundary.
**Dashboard:** async multi-project UI; project/session/PR/usage views; mobile terminal; GitHub and local-project add flows.
**GitHub bridge:** cached discovery; onboard/integrate policy; private-repo fallback; dedup/tracking/ignore; `horus start`.
**Execution & adapters:** Fake/Claude/Codex adapters; multi-account launch; workflow handoffs; worker marking; hub orchestration.
**Companion & launch:** Tk mascot; worker badges; owned windows; VS Code tasks; same-version `/health` adoption.
**Distribution:** PyPI trusted publishing; three-OS install smoke; Apache-2.0.

## Rules (load-bearing)

The invariants that constrain new work. Full rationale: `archive/decisions.md` + `archive/history.md`.

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
  email never lands in a commit; forward-slash every path written to TOML/JSON. A
  `CLAUDE_CONFIG_DIR` isolates renderer preferences too — compare account settings when
  UI behavior differs, and change the explicit preference rather than cloning ambient config.
- **Agent terminals on phones:** keep the browser terminal functional, but use native
  iOS Termius SSH over the private Tailscale network into `horus tui` as the reliable
  Claude/Codex control path; managed tmux makes app- and TUI-launched sessions attachable
  from either surface. `claude-work-phone` selects the isolated work account. Treat Claude
  in the 39-column browser/xterm viewer as best-effort; do not resume narrow-grid patching
  without new upstream renderer evidence.
- **Mobile entry stays deliberately simple:** Termius → connect → `horus tui`. No
  shortcut/forced-command machinery; revisit only if Termius adds a free one-tap
  saved-host/startup action or real usage changes the tradeoff.
- **Terminal-app navigation stays inside the UI:** on a real TTY, swipe/wheel/arrows
  scroll the highlighted internal viewport and raw escape bytes never reach a line
  prompt; leave the alternate screen before blocking agent launch/attach commands.
  Preserve conventional mouse/arrow mapping on SSH because Termius already translates
  touch gestures; inversion is explicit opt-in only. Account aliases are display labels
  while ambient launches continue to pass `None` to the native agent adapter.
- **Terminal persistence is prospective and capability-based:** TUI and web-app session requests use a unique Horus-managed tmux session when tmux is available on Linux/macOS/WSL and the caller is outside tmux; browser xterm and web-requested native windows attach as viewers, while native Windows, no-tmux hosts, and nested shells keep their direct host. A live registry row is attachable only with a Horus tmux `target_ref`; otherwise label it `original terminal only` and never offer a fake attach/close action. If a requested viewer cannot attach, reap the new tmux session. Keep scripted `horus open --target` behavior explicit and stable.
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
- **Orphan reaping only ever acts on positive confirmation (2026-07-13).**
  `reap_orphans()` kills a Horus tmux session only when the registry has a *matching*
  record that is already terminal or whose tracked pid is dead, AND it's unattached,
  AND idle past a grace window. A tmux session with **no matching registry record is
  never touched**, however idle/unattached — absence of a record is not evidence of
  anything (a stale, foreign, or rebuilt registry looks identical), and reaping on
  absence is exactly how a live session gets killed. Extend this pattern to any future
  reaper before relaxing it.
- **tmux is one server per machine, never `$HOME`-namespaced — isolate it with a
  private socket in every test/probe that touches real tmux (2026-07-13 incident).**
  A live probe pointed a fake `$HOME` at tmux to sandbox the *registry*, but tmux itself
  is a single shared server regardless of `$HOME`; `reap_orphans()` correctly (per its
  own contract) killed two real pre-existing sessions on the machine because they had
  no record in the probe's fake registry. No real loss this time (owner confirmed both
  were already-abandoned), but never again: any tmux-touching test or probe MUST use
  `tmux -S <explicit-path>` (not `-L <path>` — `-L` takes a bare *name* in the standard
  socket dir, not a path, and silently mis-resolves/errors if given one).
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
