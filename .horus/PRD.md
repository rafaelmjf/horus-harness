---
status: active
current_focus: "The approved personal-Claude parallel trial delivered product-audit PR #258 and terminal-TUI remote start PR #257 in one attempt each; exact CI plus direct audit/TUI probes passed, while overlapping ambient-account readings stayed honestly confounded. The first detached campaign also exposed that successful merged workers are persisted as crashed/stale/blocked with null runtime."
next_action: "Fix the reproduced detached completion-receipt defect under `deferred-supervision-completion-receipt`: terminal one-shot workers with pushed PR evidence must retain a truthful terminal state and runtime instead of `crashed` / `stale` / `blocked` / null. Keep the richer supervision taxonomy deferred."
next_prompt: "Fetch clean main after the parallel-worker closure, read PRD.md and `deferred-supervision-completion-receipt`, then claim it. Reproduce against datums `ed7a7f2b` and `bf63cc20`, trace executor reconciliation into registry/delivery/datum projection, fix only terminal-state/runtime/delivery truth, and gate with targeted tests plus one cheap isolated detached probe."
execution_recommendation: "continue-as-is — the next unit is a narrow reproduced lifecycle defect whose exact persisted rows are already in supervisor context; another dispatch would pay the full brief/review/merge tax and use the broken surface to test itself, with no offsetting context, parallelism, or lower-tier dividend."
last_updated: 2026-07-16
last_product_audit: 0.0.57 2026-07-16
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

**Continuity value finding (updated 2026-07-15):** the proven spine is resume
frontmatter + pushed git/PR state + fetch-first; local recovery notes are an optional
fallback when that durable state cannot resume incomplete work. The six-lane taxonomy
and mandatory per-session prose were overhead.

## Backlog

Prioritized open work. Features and bugs in one list; jump order is allowed — this list
is a menu, not a contract. Mark bugs **[bug]**, ops chores **[ops]**.

### Open / deferred — see `.horus/backlog/`

Eight active cards: high — detached completion-receipt correctness; medium — campaign launch UI, project workflow overrides, scoped machine requirements, and remote-only TUI start; low/deferred — Codex usage-window semantics, init-CI, and heartbeat stall detection.

## Shipped

**Release-stamped product audit** (2026-07-16, PR #258): `close`/`consolidate` emit a non-blocking advisory after five releases or 30 days, while the bundled evidence-first skill permits only demote/defer/retire/no-change verdicts and updates the PRD stamp without adding telemetry or features.
**Explicit worker dispatch consent + actual-cost accounting** (2026-07-16, PR #256): shared Claude/Codex instructions and decision/execution skills require owner approval for an exact worker envelope with reapproval on fallback; completion captures one end reading and `horus datum report` renders model/account/effort/runtime/attempt/outcome plus observed or honestly confounded start/end usage without estimation or polling.
**Attachable detached workers + delivery completion evidence** (2026-07-16, PR #255): foreground/detached one-shot workers share a stable-ID caller-death-safe tmux executor; explicit delivery intent/evidence persists `delivery-ready|blocked|no-op|failed|unknown` across reconciliation, registry, JSONL, datums, and sessions JSON; additive registry readers preserve unknown future fields.
**Bulk-migration inventory reconciliation** (2026-07-16, PR #254): `horus verify-inventory` reconciles source/produced trees by count+size both directions (0 clean / 1 discrepancy / 2 error), treats an empty walk of an expected-non-empty tree as a retryable error, handles non-ASCII names, and the horus-execution skill requires the reconcile before accepting bulk-copy phases; delivered by a dispatched sonnet worker gated by the account-scoped usage check.
**Account-scoped usage check** (2026-07-16, PR #253): `horus usage check --account <alias>` reads the isolated CLAUDE_CONFIG_DIR/CODEX_HOME mapping without touching the ambient login, names source/freshness/windows, fails unknown aliases instead of falling back, and warns on overseer==worker account collisions (advisory).
**Optional recovery notes and honest onboarding** (2026-07-15, PR #247, v0.0.57): fresh init keeps a blank tracked backlog and does not pressure immediate inference; generated instructions are not treated as project truth; doctor/close never require or auto-create local notes; v3 infer and Claude/Codex attribution are honest; onboarding preflights and safely inherits repository-local Git identity; hosted/local installs and the selected Horus/Fabric projections were verified.
**Need-first dispatch routing** (2026-07-15, PR #244, v0.0.56): managed instructions and bundled consolidation/execution/decision skills prove a concrete context, parallelism, or price dividend before model selection; cross-project scope, multiple phases, and calibration alone never force dispatch, live owner evidence may qualify incomplete usage telemetry, and durable guidance carries no pinned model names.
**Fleet Projection Sync cockpit** (2026-07-15, PR #240): TUI Home shows stale/unknown project counts, a dedicated screen renders each Claude/Codex surface against the canonical projection check, and the optional `horus-agent` curator launch carries a bounded fetch/isolated-worktree/branch→PR prompt without automatic writes.
**Truthful datum quality denominator** (2026-07-15, PR #241): `void` closes aborted/untested runs, `died` and `void` remain separately visible, and only clean/nudged/bounced contribute to quality rates and recent quality outcomes; delegation rubric v4 consumes the corrected fields.
**Boundary-based continuity granularity** (2026-07-15, PRs #238/#239): handoff boundaries are the default while delivery/manual remain selectable in TUI Defaults; git history provides portable pending-delivery receipts, strict project overrides still bind CI, per-turn Stop hooks no longer dirty session notes, dispatch pins/surfaces its base and pending state, resume/TUI warn until one campaign checkpoint consolidates PRD/cards/session context, and successful v3 acting-close output stays concise instead of replaying the retired six-lane ritual.
**Project-declared machine readiness** (2026-07-14, PR #237): optional `.horus/requirements.md` tool/config probes are checked without command execution and rendered through one canonical result in doctor, resume prompts, dashboard badges/details, and TUI project views; the existing fabric declaration is the live first consumer.
**Unambiguous acting-close verdict** (2026-07-14, PR #236): `close --commit [--push]` performs its checkpoint before rendering status, so successful output contains only recomputed clean findings while residual edits, failed pushes, and no-op failures still report their final actionable state.
**Required server-side continuity freshness** (2026-07-14, PR #233): `close --check --base-ref` fails source/product PRs without canonical PRD/lane updates; GitHub's `freshness` job is non-advisory and required, while the local merge hook tokenizes command positions so quoted prompts never trigger it. Live queued-auto-merge probe PR #234 remained blocked and was closed unmerged.
**Remote-authoritative fleet curator** (2026-07-14): a path-free shared manifest drives `horus fleet --review` (fetched remote PRD/cards/capabilities kept separate from local state, with GitHub fallback and continuity lag), an optional TUI Fleet Review/curator launch, and a bundled owner-gated curation skill.
**TUI canonical project focus + claimed-card state** (2026-07-14, PR #229): the project screen renders PRD-first current focus and next action before launch choices, and backlog rows visibly distinguish claimed cards while reusing canonical focus/card primitives.
**Self-reference-free closure + residual-dirty guard** (2026-07-14, PR #228): close harvests work before staging, seals its own SHA only in the local marker, names residual continuity edits and skips push, then recomputes the complete closure verdict.
**Visible web + manual TUI account usage refresh** (2026-07-14, PR #227): the web cache-refresh label is always visible and properly sized; TUI `u` re-reads cache-only usage and account mappings in-frame with a compact visible shortcut and no live provider call.
**Canonical GPT-5.6 roster + lifecycle provenance** (2026-07-14, PR #226): generic aliases fold into Sol, canonical Sol/Terra/Luna priors join measured datums with sourced prices, and optional availability/retirement markers remain display-only.
**TUI capabilities screen** (2026-07-14, PR #225): project-open regenerates the canonical capability record once, renders its vision plus a scrollable shipped list with related commands, and reports generated age + commits since.
**Archive-on-ship backlog lifecycle** (2026-07-14, PR #223): shipping stamps PR/SHA then moves the complete card to `backlog/archive/`; active local/fleet views exclude terminal cards and the archive; 13 shipped + 2 owner-retired cruft cards archived without content loss.
**One-verb resume preflight** (2026-07-14, PR #222): `horus resume --preflight [--fleet]` composes fetched git state, explicit dual-target usage freshness, version floors, PRD handoffs, open datums, projected sessions/collisions, and hygiene into one lean read-only digest; `--no-fetch` and JSON `--stdout` supported.
**Tier-0 supervision verbs** (2026-07-14, PR #221): `horus merge-watch <sha|pr>` polls required checks on the exact pinned sha to green/red, one line per state change; `horus reinstall <path> --verify <marker>` does the cache-clean + force-reinstall + installed-surface marker grep in one act; `datum close --card` now resolves against the primary git checkout (not a `--worktree` path) with an optional `--remove-worktree` merged-only cleanup.
**Datum supervisor-cost envelope + one-act acceptance** (2026-07-14, PR #218): `usage_launch`/`usage_close` readings + agent-supplied cost flags on `datum close`; `--card` stamps delivery and warns on stale continuity; `--models` cost glance; delegation-rubric dispatch-dividend v3.
**Backlog card reviews + friendly TUI edit/review handoff** (2026-07-14, PRs #217/#219): append-only Reviews + `backlog review`; `e`/`r` open the configured editor, prefer nano over vi when unset, explain save/return, ignore swap files, then offer fetch-first commit+push.
**Scoped tmux mouse mode + TUI launch-defaults screen** (2026-07-13, PR #215): session-scoped mouse fixes wheel-scroll recall; `d`-key Defaults screen persists launch posture. v0.0.52 attach gate PASS (owner-verified): web-launched session attached from Termius/`horus tui`, detach/reattach clean.
**Guarded tmux orphan-reaper** (2026-07-13, PR #214): `reap_orphans()` kills only on positive confirmation (matching registry + terminal status + idle grace).
**Unified terminal project cockpit** (PRs #195–#213, v0.0.46–0.0.52): responsive phone/desktop TUI with KPIs, scrolling, unified Resume/Fresh, backlog-card resume, live-session controls; managed tmux attachment across viewers; graceful fallbacks.
**Ops & UX hardening batch** (2026-07-12, PRs #171–#177): `dashboard --reload` + `horus app` child respawn; consolidated-to gitignore marker (no self-dirtying closure); Codex usage account-wide scope fix; mobile terminal sizing/lifecycle/controls hardening; backlog `ship` PR/SHA provenance + `close --check` shipped-but-open warning; OpenWiki skip-but-watch verdict.
**Terminal multi-viewer/mobile stack + verified Claude phone route** (PRs #178–#191, v0.0.36–0.0.45): phone-width spawn, retained exits, SSE reset markers; native iOS Tailscale SSH → tmux path verified reliable.
**Windows CLI un-broken** (2026-07-13, PR #181): lazy import of Unix-only `fcntl`; install-smoke green all three OS.
**Capabilities catalog + empirical delegation spine** (2026-07-11/12, PRs #157–#159/#163/#167–#169): MEASURED datums + owner priors + three consumer skills (data-only, no auto-routing); per-project `capabilities.json` regenerate-on-read artifact + Vision lead in catalog; `--models`/`--matrix` aligned tables with canonicalized model names + staleness WARNING.
**Mobile-web-app bundle + dashboard resilience** (2026-07-11, PRs #149/#151/#153/#155): PWA-installable, per-project error card isolation.
**LaunchBackend seam + fleet-reporting hardening** (2026-07-10/11, PRs #131–#148, v0.0.33–0.0.35): minimal LaunchBackend contract + LocalBackend (Omnigent optional, undepended-on, config target selection deferred); honest dispatch receipts; both-window usage preflight; fetch-first staleness signals.
**Continuity core + hooks/projections:** init/close/session/doctor/consolidate/distill/infer/reconcile; PRD+sessions v3; cross-agent usage/closure hooks; upgrade/sync, version-floor, and fetch-first gates; worker foundations.
**Dashboard:** async multi-project UI; project/session/PR/usage views; mobile terminal; GitHub and local-project add flows.
**GitHub bridge:** cached discovery; onboard/integrate policy; private-repo fallback; dedup/tracking/ignore; `horus start`.
**Execution & adapters:** Fake/Claude/Codex adapters; multi-account launch; workflow handoffs; worker marking; hub orchestration.
**Companion & launch:** Tk mascot; worker badges; owned windows; VS Code tasks; same-version `/health` adoption.
**Distribution (current v0.0.55):** PyPI trusted publishing; three-OS install smoke; hosted pinned-install deployment; Apache-2.0.

## Rules (load-bearing)

The invariants that constrain new work. Full rationale: `archive/decisions.md` + `archive/history.md`.

- **Repo-local `.horus/` is the source of truth** — committed, vendor-neutral, works without Horus installed. Horus is a helper, never a required runtime.
- **Controls climb a ladder: instruction → deterministic signal → hard gate.** Start with instructions; promote only after an observed field failure (fetch-first + branch→PR instructions failed, so SessionStart signal + block v7 followed). Never enforce preemptively.
- **Server-side continuity is granularity-aware.** The required PR check always verifies field validity + git checkpoint state; `delivery` additionally requires canonical PRD/card hygiene in every PR, while default `handoff` and `manual` accept product commits as durable receipts until the next visible boundary checkpoint. Local PreToolUse parsing is fast feedback only and must match `gh pr merge` at shell command position, never inside quoted prompt prose.
- **Continuity must beat re-derivation.** Every capability must give a fresh session something CLAUDE.md + git log cannot, at lower cost. PRD.md is state, not behavior; behavioral text belongs in the managed block, and Rules holds only project-specific invariants earned by failure.
- **Continuity checkpoints at context boundaries; delivery safety never relaxes.** Default `handoff` batches canonical PRD/card/session prose until agent/account/machine change, dispatch, pause, release, or end; `delivery` closes every PR and `manual` keeps warnings until explicit close. Branches, commits, pushed refs, PRs, deterministic gates, dispatch base/receipts, and commit/push checkpoints apply in every mode. Pending delivery truth derives from product commits after the latest canonical-continuity commit, so it survives machines and squash merges.
- **Closure reaches the remote, fetch-first and self-reference-free** — at the configured boundary run `close --commit --push`; refuse newer remote continuity, seal the closing SHA without appending it into its own note, and refuse to push residual dirty continuity. Start each session with `git fetch --all --prune` before trusting local refs or prose.
- **Acting closure reports the final state only.** `close --commit [--push]` keeps pre-action dirtiness internal, renders the recomputed complete findings after its mutation, and still fails visibly on residual edits or an unpushed checkpoint.
- **Committed machine probes are data, never commands.** `.horus/requirements.md` tool probes are executable-name lookups and config probes are path-existence checks; doctor, resume, dashboard, and TUI render the same shared result, while non-probeable access stays prose.
- **One fetch-first primitive, reused.** `fetchcheck.fetch_and_state` (TTL-cached, read-only fetch, never pull) serves SessionStart and `status`/`fleet` gone-branch/staleness signals; no consumer reinvents it.
- **Fleet review names its truth layers.** Manifests contain repository identity/lifecycle only; fetched `origin/<default>` PRD/cards are REMOTE SHIPPED TRUTH, checkout/session/dirty state is LOCAL WORKING STATE, and neither is blended or pulled. GitHub fallback is read-only; unavailable/unstructured data is labelled, never guessed.
- **Resume preflight only projects deterministic data.** Its sole sanctioned side effect is the explicit fetch refresh; session liveness is projected without registry reconciliation, usage snapshots carry unmistakable freshness tags, and no output recommends or selects a model/account.
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
- **Three OS targets** (Windows/Linux/macOS); Claude/Codex projections move together and each compares with the CLI, never with its peer. Before release, project from prospective source (`uv run horus`) or repeat after install—the previous installed version can falsely look current. Fleet Projection Sync is read-only; curator launch never mass-writes targets.
- **Every release:** bump `pyproject.toml` + `horus/__init__.py` + `uv.lock`, rerun tests, publish promptly, and prove PyPI JSON/simple-index plus a fresh install on all three OSes. The final release action is `scripts/deploy-hosted.sh`: exact refreshed install, service restart, `/health` version match, and `/` still 403 behind Access. A green publish job alone is insufficient.
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
- **Terminal TUI stays thin and navigable:** render canonical CLI-callable continuity/card
  primitives, never a second parser/state path; swipe/wheel/arrows scroll the highlighted
  viewport, and leave the alternate screen before blocking commands. External editors honor
  VISUAL/EDITOR; prefer a modeless fallback and explain how to return — vi made typing look
  broken. Preserve conventional SSH mouse/arrow mapping; inversion is opt-in. Account aliases
  are display labels while ambient launches pass `None` to the native agent adapter.
- **Terminal persistence is prospective and capability-based:** TUI and web-app session requests use a unique Horus-managed tmux session when tmux is available on Linux/macOS/WSL and the caller is outside tmux; browser xterm and web-requested native windows attach as viewers, while native Windows, no-tmux hosts, and nested shells keep their direct host. A live registry row is attachable only with a Horus tmux `target_ref`; otherwise label it `original terminal only` and never offer a fake attach/close action. If a requested viewer cannot attach, reap the new tmux session. Keep scripted `horus open --target` behavior explicit and stable.
- **Git policy:** branch → PR → auto-merge; this repo's main requires pytest checks
  (admins exempt so continuity pushes land directly; fallback direct merge only on
  repos without required checks); offboard keeps `.horus/` by default; `.vscode/` is
  a user surface (static, secret-free, create-only).
- **Delegation is need-first, model-second.** Define the bounded unit and name a
  concrete context, parallelism, or price dividend that exceeds the fixed supervisor
  tax before selecting a worker. Cross-project scope, multiple phases, and calibration
  goals alone do not justify delegation; integrated campaigns may be cheaper inline.
  Owner-directed dispatch may instead spend expiring account capacity or protect the
  supervisor context, but every launch first names the exact agent, concrete model,
  effort, account, current usage/reset evidence, bounded task, attempt allowance, and
  gate and obtains approval; any fallback changes that envelope and asks again. Worker
  completion captures one end reading; show a percentage-point delta only for fresh
  same-window isolated readings without tracked overlap, otherwise retain the actual
  start/end evidence with an unknown/confounded label. Never estimate task usage,
  auto-route, continuously poll, or spend another model call on accounting. Workflow
  tests still require a real distinct worker. Codex
  auto-edit workers get a read-only `.git` and no socket bind: the
  supervisor owns commit, push, and every runtime gate — write briefs accordingly.
- **Self-documentation has two truth layers, never curated (2026-07-16).** "What exists
  now" is answered only by code-derived surfaces (`horus --help` / the argparse walk);
  `backlog/archive/` cards are the append-only historical index ("was this built, where
  did it live") — dated, SHA-pinned, verified against code before trusting. No
  supersede/tombstone metadata on archived cards, ever: curation decays, byproducts of
  the ship ritual don't. The capabilities project record is a display/fleet projection
  artifact, not an agent entry point.
- **Capability catalogs stay idempotent EXCEPT the per-project stamp, by design
  (2026-07-11).** The fleet-wide catalog has no timestamps (pure function of
  sources, unchanged run = no write). `horus capabilities --project <name>`
  (or the self-document default) deliberately relaxes this ONE way: its
  `generated_at` stamp refreshes every run — the file is a regenerate-on-read
  publishing artifact, never a cache read back — while the `project` payload
  underneath stays just as idempotent. Don't "fix" the stamp, and don't let
  the relaxation creep into the fleet-wide catalog. The TUI calls
  `generate_project` once on project-open and renders that returned payload;
  it never reads the generated file as a cache or maintains a parallel parser.
- **Model calibration measures; the agent judges.** Measured datums and hand-edited owner priors stay separate; `horus/datums.py` is never a router/policy/spend engine. Outcomes are agent-supplied: clean/nudged/bounced form quality, died/void are separate operational counts, and exit is an orthogonal mechanical axis. Every consumer emits data only—no pick, `--for`, or auto-dispatch—and aliases normalize before joins.
- **Orchestration (proven 2026-07-04, contract in execution skill v8):** parallel features
  run orchestrator > supervisor > worker — worktree per worker; claude workers `full-auto`
  (default posture stalls headless); bounce = resume same session with the exact failure;
  after each merge watch main's push CI before arming the next. Orchestrator implements
  nothing, alone edits continuity. Commit continuity before cutting a worktree from HEAD;
  name any unreviewed-output branch in the handoff; probe briefs never hardcode port 8765;
  manually reap exact-handle orphaned port-holders before probing after a worker death;
  automatic cross-platform reaping stays retired unless incidents make manual recovery burdensome (closed design PR #231).
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
  were already-abandoned), but never again: any tmux-touching test or probe MUST unset
  inherited `TMUX` and route every client/cleanup call through `tmux -S <explicit-path>`;
  a private HOME/TMUX_TMPDIR does not override an inherited server target. Never issue
  bare `kill-server`. (`-L` takes a bare name, not a path, and can silently mis-resolve.)
- **Machine-local registries are additive and forward-readable.** Readers ignore fields
  they do not understand and known-field updates preserve them; source-version probes
  isolate HOME/registry so an installed older CLI is not fed a future row schema.
- **Platform traps:** `uv tool install horus-harness` without `--python 3.12` silently resolves
  an ancient version below the floor — compare `horus --version` with `uv run horus --version`,
  `--force --python 3.12` reinstall + restart. A **stale `pip`-installed `horus` on PATH shadows
  the uv shim** (v0.0.28 `doctor machine` flags it). Also: ctypes needs argtypes/restype;
  Windows GUI under `pythonw.exe` + reap the tree; pin CI actions to real tags; probe the HTTP
  server, not the companion.

## Structure contract (prototype)

- **This file** carries vision, backlog, shipped, rules. Keep it under ~250 lines: shipped items are one line; shipped cards move to `backlog/archive/` with status + PR/SHA intact; bugs get cards as found.
- **`backlog/` (card pilot 2026-07-10, claim gate 2026-07-11):** one card per item with `status`/`priority`/`tier`/`created` plus optional `parallel`/`surface`; claim via `horus backlog claim` (warnings need `--force`). After merge, `horus backlog ship <name> --pr N --sha SHA` records provenance and moves the card to `backlog/archive/`; active local/fleet views exclude terminal cards and the archive. `close --check` warns on lingering-done or shipped-but-open cards. No stale-`claimed` sweep exists.
- **`sessions/`** unchanged: one note per session (`horus session new`); distilled notes → `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated` — the tooling reads them PRD-first (`resolve_focus`),
  so no shims are needed. Describe the next unit and execution posture without pinning a
  model name; choose the model from live calibration only after delegation earns its cost.
- **Closure:** at the configured boundary, update frontmatter + backlog/shipped + one campaign session note; run `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
