---
status: active
current_focus: "pathfinder FACTORED into step skills (2026-07-17, PR #288, merge SHA 9e749e4, main CI green). The second dogfood ran the flow on this repo (intent=deepen-own-use, reused the same-day market receipt at zero spend) and produced a full branch-tree read-out — receipt .horus/research/2026-07-17-pathfinder-branch-tree.md — but deliberately NO cards: the owner chose to rebuild the skills first from the run's nine calibration findings (read-out BEFORE any diff gate; narrative depth over bullets; a plain numbered roadmap; fixed template with a no-repetition rule; claims name their comparison baseline; re-justify the EXISTING backlog with explicit push-back, inherit nothing; the deliverable is a branch TREE incl. 1-2 speculative branches, never one merged roadmap; every proposed item ships as a fully populated self-sufficient card draft; market evidence inside each branch). Result: new `roadmap-branches` skill v1 (the divergence tree) + `scope-cards` skill v1 (self-sufficient card drafts + Vision diff + existing-card edits, per-item owner gate), `pathfinder` v2 rewritten as a genuinely thin sequencer (Step 0 intent gate → pinned brief → market-scan → roadmap-branches → scope-cards; receipts are the step interfaces; optional owner-pre-authorized straight-through mode that still never writes unapproved), market-scan v3 linkage. All projections installed for claude+codex; suite green (1645). Post-boundary: merged the parallel scheduled session's PR #287 (TUI backlog field picker, merge SHA 85d0eeb) and re-closed so this frontmatter stays canonical; the reconciliation gap that made that manual got a card (parallel-session-continuity-reconciliation)."
next_action: "CONVERGENCE TEST: run pathfinder e2e in a FRESH session with the factored skills, WITHOUT reading the held-out receipt .horus/research/2026-07-17-pathfinder-branch-tree.md — if the process is well-specified, an independent run (any session/model) should converge to similar branches and findings. Compare against the held-out receipt only AFTER the run and report convergence/divergence. Then decide whether to apply a chosen branch via scope-cards. For reference (post-run only), the held-out tree proposed: A agent-neutrality primary (cross-agent-resume-parity, native-memory-interop), B PO-loop proof, C rescoped to external-priors-calibration (owner push-back: rely on external benchmarks over own-datum plumbing), X1 fleet-knowledge-plane as the strongest speculative branch."
next_prompt: "Fetch clean main. PR #288 shipped the factored pathfinder flow (roadmap-branches + scope-cards + thin pathfinder v2). Run the `pathfinder` skill e2e on THIS repo as a convergence test: intent=deepen-own-use; do NOT read .horus/research/2026-07-17-pathfinder-branch-tree.md (held out for post-run comparison); reuse or refresh market evidence per the envelope gate; carry the full flow through (pinned brief → market-scan → roadmap-branches tree → owner picks → scope-cards drafts). Afterwards, compare the new branch tree against the held-out receipt and report where the runs converged and diverged."
execution_recommendation: "continue-as-is — an interactive, owner-gated dogfood run on one repo; every step is a conversation gate, so there is no parallelism or lower-tier dividend that would beat the supervisor tax."
last_updated: 2026-07-17
last_product_audit: 0.0.58 2026-07-16
horus_min_version: 0.0.26
---

# Horus — PRD

The one maintained continuity file: **PRD.md + sessions/** (prototype, 2026-07-03). Tooling reads its frontmatter directly; retired lanes remain in `archive/` and git history.

## Vision

Horus is a lightweight, repo-local **product owner** for official coding-agent CLIs (Claude Code, Codex, more later) — a PO's memory *and* rituals, made repo-local so any native agent session can pick up the role. Continuity is the proven spine. The Vision resolves into named **facets**, each with a definition of done the backlog converges toward (cards carry `vision_facet`):

| Facet | Definition of done |
|---|---|
| **Continuity core** | A fresh agent session resumes the exact next step from durable state alone, fetch-first, across machines. |
| **Dashboard / cockpit** | Owner sees fleet state and launches/resumes any project from web or phone, no terminal command. |
| **Accounts & isolation** | Every account runs isolated by default; cross-account corruption impossible; usage visible per account. |
| **Delegation calibration** | Agent picks execute-vs-dispatch + a model tier from live measured data, owner-gated, honest cost — never auto-routing. |
| **PO lifecycle** | The forward loop — market research → vision → vision-convergent roadmap → ship — runs repo-local (frontier: discovery + convergence are the open gap). |
| **Introspection & self-improvement** | Every recurring surface, skill, and process can be audited against reality on evidence, yielding owner-gated verdicts (demote/defer/retire/revise), never ceremony. |
| **Distribution** | `uv tool install` yields a safe, current, isolated setup on all three OSes; the hosted app tracks releases. |

**The roadmap breathes — divergence then convergence (2026-07-16):** the facet set and their DoD are a *living hypothesis*, not a frozen contract. A project's real path is research → **divergence** (ideas explored as PoCs, some outside the first vision) → usage → **convergence** (drop, trim, rescope toward a consistent product; directions that prove out are promoted into new facets). Convergence is triggered by usage evidence, not schedule; exploratory work is expected to lack a facet/DoD until it earns one or is dropped. This repo is the worked example (six-lane → consolidated PRD/backlog). Cards: `roadmap-convergence` (convergence machinery) + `explore-converge-lifecycle` (the explore phase).

The durable value is the **memory + planning plane, never orchestration**: repo-local `.horus/` files any native agent can use without Horus running; a read-mostly dashboard (projects, current focus, next step, sessions, accounts/usage); visibility into which agent/account/environment touched a project. Deliberately NOT the superpowers/spec-kit framework depth.

Model concretely: `project + agent + account + environment + session` — no abstract identity profiles. Native-app-first: design capabilities on Claude/Codex's own surfaces before a Horus-owned session layer. Execution planes own orchestration (see `research/omnigent.md`); Horus stays the memory/planning plane and interops via `.horus/`.

**Out of scope:** the execution/orchestration plane (distributed worker control, agent marketplace); multi-user SaaS; identity abstraction; continuous external monitoring (the always-on competitor-scraping SaaS category — discovery is one-shot, evidence-first, not a live feed).

**Product-owner expansion (2026-07-16):** widened from "continuity layer" to "repo-local product owner" after dogfooded landscape research (`research/2026-07-16-po-capabilities.md`); continuity stays the core. The open frontier is the PO-lifecycle facet (discovery + convergence).

**Continuity value finding (updated 2026-07-15):** the proven spine is resume
frontmatter + pushed git/PR state + fetch-first; local recovery notes are an optional
fallback when that durable state cannot resume incomplete work. The six-lane taxonomy
and mandatory per-session prose were overhead.

## Backlog

Prioritized open work. Features and bugs in one list; jump order is allowed — this list
is a menu, not a contract. Mark bugs **[bug]**, ops chores **[ops]**.

### Open / deferred — see `.horus/backlog/`

Nineteen active cards: the **vision-branch-x3 explore cluster** (PR #289, parallel scheduled session, merged 4099389 — a "vision branch" umbrella card `vision-branch-x3-scheduling-and-autonomous-execution` + 5 `phase: explore` cards for scheduled/attachable/consent-gated autonomous dispatch+supervision: schedule-local-dispatcher, unattended-dispatch-attachable-worktree-defaults, supervise-verify-merge-close, unattended-escalation-channel, cockpit-autonomous-dispatch-contract; deliberately no `vision_facet` — the direction sits in the Vision's out-of-scope orchestration plane, so promote-to-facet vs drop is a pending owner convergence decision); the remaining thirteen each stamped with a `vision_facet`: medium — fleet artifact refresh, stale-datum overlap reconciliation, remote open-model probe, project workflow overrides, scoped machine requirements, parallel-session-continuity-reconciliation (name sibling deliveries at close/resume; from the PR #287 parallel-session incident), and the lone remaining PO-lifecycle card explore-converge-lifecycle (open only for the usage-ripeness flag; pathfinder flow shipped in #285/#286/#288); low/deferred — account-settings-sync (sync one settings block across isolated account dirs), Codex usage-window semantics, completion-receipt trimmings, init-CI, heartbeat stall detection, and product-naming (rename pinned to first external distribution; horus-po/horus-continuity both rejected — want a more creative name).

## Shipped

**PO-lifecycle: vision-convergent roadmap + market-scan + factored `pathfinder` re-baseline flow** (2026-07-16/17, PRs #280–#283/#285/#286/#288): Vision widened to a repo-local product owner resolved into 7 facets each with a definition of done, plus a breathing divergence→convergence model; backlog cards carry `vision_facet`/`phase` and `horus consolidate` emits a phase-aware convergence read-out (per-facet coverage + exploratory bucket; warns off-vision/unknown-facet converge cards; horus-consolidate skill v12); the `market-scan` skill (outward twin of product-audit; v2 added the build-vs-adopt verdict for personal-tooling intent, v3 hands its receipt to roadmap-branches) composes deep-research into a dated `.horus/research/` receipt (advisory, never auto-writes). `pathfinder` (#285 built as `horus-kickstart`, #286 renamed age-agnostic + Step 0 intent gate + pinned-brief grounding after the first dogfood) was FACTORED by #288 after the second dogfood's nine calibration findings into independently-invocable, skill-auditable steps: `roadmap-branches` v1 emits the divergence tree (narrative position, market shells→verdict→risk stated once, one branch per direction with market-position line + numbered roadmap + convergence criterion + implied Vision diff, 1-2 speculative branches, explicit push-back re-justifying the existing backlog) and `scope-cards` v1 populates a chosen branch into self-sufficient card drafts (fresh agent + PRD + card = can start) plus Vision/existing-card diffs with a per-item owner gate; `pathfinder` v2 is the genuinely thin sequencer (intent gate → brief → market-scan → roadmap-branches → scope-cards, receipts as step interfaces). Both dogfood receipts live in `.horus/research/` (2026-07-17; the branch-tree one is held out for an e2e convergence-test rerun).
**Per-account config-dir isolation: safe + default + self-healing** (2026-07-16, PRs #277/#278/#279): `horus run` refuses a second live agent process on a config dir already in use — two CLIs on one `CLAUDE_CONFIG_DIR`/`CODEX_HOME` race on its JSON and corrupt it (`--force` overrides; the launching session's own-dir share only warns) — and a dispatch-base-aware delivery receipt stops crediting a branch resting at its base with the base's own closure commit (so a never-ran worker reads `failed`, not `failed-but-delivered`). Onboarding (`horus account --set`, dashboard add) auto-provisions `~/.horus/accounts/<agent>-<alias>` and maps it by default (`--no-isolate` opts out; explicit `horus account --isolate`). `horus doctor` flags existing ambient/shared accounts and managed blocks behind the installed version, each with its fix command. The "one live agent process per account config dir" invariant ships in the generated managed block (v11). Delivered inline from the horus-agent cockpit after a real two-worker corruption incident.
**Audit receipts + skill-audit skill** (2026-07-16, PR #276): product-audit v2 lands verdicts in dated one-page `.horus/audits/` receipts (defers recallable, anti-ceremony guard checkable, initial-stamp rule, named grep targets); the new owner-invoked skill-audit skill audits one skill's text against reality with an owner-approved revise verdict and no staleness trigger; drifted fleet-curation projections resynced; README/pyproject lead with the continuity-layer/product-owner framing.
**Evidence-first process retrospectives + exact post-merge CI watching** (2026-07-16, PRs #270/#271): a shared event-driven skill attributes one bounded incident and recommends at most three owner-gated cheapest-rung changes without automatic ceremony; literal merge-SHA watches discard PR-only contexts only from complete exact-SHA workflow evidence, fail closed on partial/unparseable evidence, preserve open-PR movement checks, and settled their own main merge green.
**Worker/supervisor process hardening** (2026-07-16, PR #267): tracked workers deny destructive cleanup of user-global Horus/Claude/Codex state while isolated probes remain possible; v3 execution prompts load only PRD plus the active plan, and shared delegation guidance discloses same-account parallel attribution loss before launch.
**Provider-valid model selector contract** (2026-07-16, PR #266): consent and execution plans distinguish calibration keys from executable provider selectors; known calibration-only Claude labels fail before side effects, accepted selectors pass unchanged, and canonical resolved model IDs preserve datum continuity.
**Optional Campaign supervision launch** (2026-07-16, PR #265): the TUI offers an owner-bounded Campaign entry distinct from Fleet Review while preserving direct-project launch, need-first dispatch judgment, explicit worker consent, and target-repository authority.
**Truthful detached-worker terminal receipt** (2026-07-16, PR #261): managed one-shot tmux runs keep the runner PID authoritative through completion, preventing concurrent reconciliation from overwriting `exited`/`delivery-ready` and precise runtime with `stale`/`blocked`/null; deterministic race coverage and a token-free private-socket tmux probe pin the invariant.
**Remote-only terminal-TUI project start** (2026-07-16, PR #257): cache-only first paint distinguishes remote/cloned/ignored/unavailable projects and reuses the canonical clone/register/projection path; a live isolated private-repository frame probe proved remote-only → cloned+registered → resumable before deleting all disposable GitHub/local state.
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
**Closure & required continuity-freshness hardening** (2026-07-14, PRs #228/#233/#236): self-reference-free acting-close (harvest-then-stage, seal own SHA in the local marker only, residual-dirty guard, final-state-only verdict); `close --check --base-ref` freshness is a required non-advisory PR gate with a quoted-prompt-safe local merge hook.
**Backlog/resume/supervision verbs** (2026-07-14, PRs #221/#222/#223): archive-on-ship card lifecycle (PR/SHA stamp → `backlog/archive/`, active views exclude terminal cards); one-verb `horus resume --preflight [--fleet]` read-only digest; Tier-0 `merge-watch`/`reinstall` and `datum close --card` primary-checkout resolution.
**Fleet curator + TUI cockpit + datum cost/reviews** (2026-07-14, PRs #217–#219/#225–#227/#229 + remote curator): remote-authoritative `fleet --review` with separated truth layers + owner-gated curation skill; PRD-first TUI launch (claimed rows, in-frame cache-only usage refresh, capabilities screen, Sol/Terra/Luna roster provenance); datum cost envelope + append-only card Reviews.
**Terminal cockpit + mobile/multi-viewer stack** (2026-07-12/13, PRs #171–#215/#178–#191, v0.0.36–0.0.52; +#287 2026-07-17 TUI backlog field picker — `f` toggles which card frontmatter fields render inline, persisted globally in `~/.horus/config.toml` `[tui]`, no-config default byte-identical; delivered by a parallel scheduled session, merged post-boundary by the supervisor): responsive phone/desktop TUI (KPIs, scrolling, unified Resume/Fresh, card resume, live-session controls, managed-tmux attach across viewers, scoped mouse, `d`-Defaults launch posture, positive-confirmation orphan-reaper); phone-width spawn + retained exits + SSE reset + verified native iOS Tailscale SSH→tmux; `dashboard --reload`/`app` child respawn; Codex account-wide usage scope; consolidated-to gitignore marker; Windows `fcntl` lazy-import (three-OS smoke green).
**Capabilities catalog + empirical delegation spine** (2026-07-11/12, PRs #157–#159/#163/#167–#169): MEASURED datums + owner priors + three consumer skills (data-only, no auto-routing); per-project `capabilities.json` regenerate-on-read artifact + Vision lead in catalog; `--models`/`--matrix` aligned tables with canonicalized model names + staleness WARNING.
**Mobile-web-app bundle + dashboard resilience** (2026-07-11, PRs #149/#151/#153/#155): PWA-installable, per-project error card isolation.
**LaunchBackend seam + fleet-reporting hardening** (2026-07-10/11, PRs #131–#148, v0.0.33–0.0.35): minimal LaunchBackend contract + LocalBackend (Omnigent optional, undepended-on, config target selection deferred); honest dispatch receipts; both-window usage preflight; fetch-first staleness signals.
**Continuity core, dashboard & GitHub bridge:** init/close/session/doctor/consolidate/distill/infer/reconcile; PRD+sessions v3; cross-agent usage/closure hooks; upgrade/sync + version-floor + fetch-first gates; async multi-project dashboard (project/session/PR/usage views, mobile terminal, add flows); cached GitHub discovery, onboard/integrate policy, private-repo fallback, dedup/tracking/ignore, `horus start`.
**Execution, companion & launch:** Fake/Claude/Codex adapters; multi-account launch; workflow handoffs; worker foundations/marking; hub orchestration; Tk mascot; worker badges; owned windows; VS Code tasks; same-version `/health` adoption.
**Distribution (current v0.0.59):** PyPI trusted publishing; three-OS install smoke; hosted pinned-install deployment; Apache-2.0. v0.0.59 (tag v0.0.59, 2026-07-17) published the PO-lifecycle work (PRs #280–#284) — convergence read-out + market-scan — with install-smoke green on all 3 OSes and the hosted dashboard redeployed to 0.0.59 (deploy-hosted.sh: /health match, / 403). v0.0.58 (PR #274) shipped the forward-compatible `SessionRecord` reader (6a655e5) that unblocked `horus tui`/`sessions` crashing on registry rows carrying newer fields.

## Rules (load-bearing)

The invariants that constrain new work. Full rationale: `archive/decisions.md` + `archive/history.md`.

- **Repo-local `.horus/` is the source of truth** — committed, vendor-neutral, works without Horus installed. Horus is a helper, never a required runtime.
- **Controls climb a ladder: instruction → deterministic signal → hard gate.** Start with instructions; promote only after an observed field failure (fetch-first + branch→PR instructions failed, so SessionStart signal + block v7 followed). Never enforce preemptively.
- **Server-side continuity is granularity-aware.** The required PR check always verifies field validity + git checkpoint state; `delivery` additionally requires canonical PRD/card hygiene in every PR, while default `handoff` and `manual` accept product commits as durable receipts until the next visible boundary checkpoint. Local PreToolUse parsing is fast feedback only and must match `gh pr merge` at shell command position, never inside quoted prompt prose.
- **Post-merge check filtering fails closed.** A literal SHA stays pinned, and only complete workflow evidence from that exact git object may remove a context proven PR-only; missing, partial, or structurally unparseable evidence leaves required contexts intact even if that means timing out.
- **Continuity must beat re-derivation.** Every capability must give a fresh session something CLAUDE.md + git log cannot, at lower cost. PRD.md is state, not behavior; behavioral text belongs in the managed block, and Rules holds only project-specific invariants earned by failure.
- **One live agent process per account config dir.** Two agent CLIs sharing a `CLAUDE_CONFIG_DIR`/`CODEX_HOME` race on its JSON and corrupt it (observed 2026-07-16: two workers on one ambient dir both died at startup). Every account gets its own isolated dir — `horus run` guards it (refuse; `--force` overrides), onboarding provisions it by default, and `doctor` flags drift. The ambient/shared default is the footgun; isolation is the invariant.
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
- **Bundled skill edits bump the skill version, always.** The version-aware install
  skips same-version content, so an unbumped text change leaves committed projections
  silently stale (observed: #247 fleet-curation drift, caught 2026-07-16). Resync with
  `skill install --force`; never hand-edit the projected `SKILL.md` copies.
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
- **Tracked workers cannot destructively clean user-global agent state.** The shared host guard blocks common destructive spellings targeting `~/.horus`, `~/.claude`, and `~/.codex` only when `HORUS_RUN_WORKER=1`; every worker probe must instead create an isolated home and clean only the exact directory it allocated. This was promoted after a worker deleted historical machine-local run logs while durable registry/datums/git state survived (2026-07-16).
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
- **`backlog/` (card pilot 2026-07-10, claim gate 2026-07-11):** one card per item with `status`/`priority`/`tier`/`created` plus optional `parallel`/`surface`/`vision_facet`/`phase`; claim via `horus backlog claim` (warnings need `--force`). After merge, `horus backlog ship <name> --pr N --sha SHA` records provenance and moves the card to `backlog/archive/`; active local/fleet views exclude terminal cards and the archive. `close --check` warns on lingering-done or shipped-but-open cards. No stale-`claimed` sweep exists.
- **Convergence (2026-07-16):** a `converge`-phase card (the default) names the `vision_facet` it advances, matched to a `## Vision` table facet; new/next-touched converge cards get one testable acceptance line. `phase: explore` marks a PoC exempt from that gate. `horus consolidate` emits the phase-aware read-out (per-facet coverage + exploratory bucket; warns off-vision/unknown-facet converge cards). The facet set is a living hypothesis — proven exploration is promoted into a new facet, not forced under an old one.
- **`sessions/`** unchanged: one note per session (`horus session new`); distilled notes → `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated` — the tooling reads them PRD-first (`resolve_focus`),
  so no shims are needed. Describe the next unit and execution posture without pinning a
  model name; choose the model from live calibration only after delegation earns its cost.
- **Closure:** at the configured boundary, update frontmatter + backlog/shipped + one campaign session note; run `close --commit --push`. One `consolidate` pass at most; do not chase warnings.
