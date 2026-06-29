# Decisions

## 2026-06-29 - Onboarding Uses GitHub Auth; Work Uses Agent Account Aliases

Dashboard onboarding of an untracked GitHub repository should not imply a Claude or
Codex account choice. `horus onboard github:owner/repo` clones, initializes `.horus/`,
and integrates through GitHub using this machine's `gh` login. The Claude/Codex account
only matters when starting the first work session on that project.

Reasoning:

- The user wanted to onboard a repo with a new agent account that was not logged in yet,
  but the existing Onboard button did not say which account it would use.
- There are two separate auth domains: GitHub clone/PR auth (`gh`) and native agent
  account isolation (`CLAUDE_CONFIG_DIR` / `CODEX_HOME`).
- Binding Onboard to an agent account would add premature coupling: a repo can be cloned
  and initialized before the desired Claude/Codex account has logged in.

Implication: Control -> Accounts now exposes local account mapping and alias editing in
the UI. Untracked GitHub cards clarify that Onboard uses `gh`; the next dashboard polish
should make the post-Onboard launch/resume CTA offer an account-alias choice for the first
work session.

## 2026-06-29 - Execution Plans Must Justify Delegation Per Agent

`execution.md` may recommend a worker tier, but that tier is only meaningful **if**
the planning agent decides to delegate. It must not be read as "standard worker means
delegation is cheaper" or "execution planning is mandatory."

Reasoning:

- The intended product shape is: the model that crafts the execution plan decides the
  execution mode. It may choose direct work, delegated work, or a deliberate
  model-separation test.
- The correct decision can differ by agent/runtime. Claude's Opus/Sonnet economics,
  Codex's model/tooling costs, available subagent surfaces, latency, and review overhead
  are not interchangeable.
- Delegation has real overhead: worker prompt/context, handoff writing, supervisor review,
  and possible duplicated codebase reading. It should be justified by economics, risk
  isolation, context splitting, parallelism, or an explicit workflow test.

Implication: `execution.md` now carries `delegation_basis`, and the phase table records
`mode` (`direct`, `delegated`, or `test-delegation`) separately from `worker_tier`.
`horus-execution` v3 and the generated supervisor prompt make this explicit.

## 2026-06-29 - Resume Uses A Generated Minimum-Context Handoff

Fresh Horus sessions should start from a generated compact handoff (`horus resume`)
instead of asking the agent to read all `.horus/` lanes immediately.

Reasoning:

- The user observed that a simple "read `.horus` files" startup prompt consumed about
  11% of context before any feature work began.
- The minimum safe handoff is much smaller: fetch/prune first, verify branch state,
  then load current focus, next action, execution recommendation/status, and latest
  session pointer.
- Deeper lanes still matter, but they should be lazy-loaded only when the task needs
  product boundaries, shipped capability status, durable decisions, historical lessons,
  or active execution handoffs.
- Centralizing this in `routines.resume_prompt()` keeps CLI (`horus resume`), dashboard
  resume cards, and `horus start` consistent.

Implication: future resume/onboarding surfaces should reuse `horus resume` semantics;
if a more compact machine-readable form is needed, add a separate `--json` or
frontmatter-only mode rather than returning to "read every lane first."

## 2026-06-29 - Execution Workflow Tests Require Real Delegation

When the user is explicitly testing the frontier-supervisor / standard-worker workflow,
"delegated" means a distinct worker/subagent/session actually implemented the phase and
left a handoff note. A supervisor-written handoff after the supervisor did the work does
not satisfy the test.

Reasoning:

- The phase 1A dashboard Ignore/Unignore fix was implemented correctly, but it was done
  inside the supervising Codex session. That validated the product fix, not the intended
  model-tier workflow.
- The `horus-execution` skill said to use workers "when useful" and to delegate bounded
  phases, but did not make real delegation a hard gate when workflow validation itself
  was the point.
- `horus-execution` v2 and the generated supervisor prompt now say: if model separation
  is being tested, the supervisor must not implement delegated work itself; if no native
  worker/subagent can be spawned, stop and report that the test cannot proceed faithfully.

Implication: phase 1B must either run through a real standard-tier worker/subagent and
frontier review, or stop before implementation.

## 2026-06-29 - GitHub Onboarding + Workflow Policy

Planning a dashboard surface for managing GitHub-tracked projects, prompted by a real gap:
a fresh repo (`agentic-gym-coach`) had no committed `.horus/`, so Horus's catalog — which
intentionally lists only Horus-enabled repos — never showed it. Three tracks (roadmap:
"GitHub project onboarding", "Dashboard artifact-staleness flag", "Workflow policy +
settings panel"). Locked calls:

- **Untracked repos are shown opt-out.** Discovery surfaces repos without `.horus/project.md`
  as a separate "Not tracked" bucket; the user hides ones they don't care about (old
  projects) via a per-machine ignore list. Default-show matches "I just want to hide the old
  ones". A brand-new repo has no verdict-cache entry, so it always surfaces on next discovery
  — no permanent silent hiding.
- **Discovery cost is bounded by caching the verdict.** Classifying every repo costs a `gh
  api` call; the `pushedAt` cache (shipped 2026-06-29) is extended to also remember the
  "not a Horus repo" verdict so unchanged repos are not re-checked.
- **Per-machine config, with a blank-owner warning.** `github_owners` and `ignored_repos`
  stay per-machine (config is not git-synced by design). When `github_owners` is blank the
  dashboard shows a "configure a GitHub owner" warning/CTA — the one onboarding-clarity fix
  pulled forward; broader onboarding polish is deferred.
- **Default integration policy: branch → PR → auto-merge unless review.** Horus-driven git
  actions (`horus onboard`, `horus close --commit`) follow a configurable workflow policy so
  onboarding never leaves a local-only `.horus/` (the "forgot to push" worry). This automates
  exactly the branch→PR→merge done by hand this session. Policy is per-machine config now
  (`[workflow]`), editable from a dashboard Settings panel.
- **"All work" has a boundary.** Horus can own the policy for *its own* commits; the
  in-session agent's code work is steered only indirectly, by projecting the policy into the
  managed instruction block (AGENTS.md/CLAUDE.md). That projection and a per-project
  git-synced override are **deferred** — MVP is the per-machine default applied to Horus's
  own actions.
- **Build order avoids a throwaway:** a minimal `[workflow]` resolver (C-min) ships before
  `horus onboard` (A3) so onboard consumes the real policy from day one; the Settings UI
  (C-full) and Track B (read-only staleness badge, independent) follow.

This is queued as a phased `execution.md` plan, **drafted and awaiting user review before
any implementation** — itself the second run of the `horus-execution` workflow.

## 2026-06-29 - Execution-Workflow Pilot: Findings + GitHub Incremental-Refresh Heuristic

First real pilot of the `horus-execution` supervisor/worker workflow. The supervisor
(frontier) planned `execution.md`, delegated one bounded phase to a standard-tier worker
(implement incremental GitHub catalog refresh), required a `.horus/temp/1A.md` handoff,
reviewed the diff + tests, accepted, and distilled here. The loop worked end-to-end.

Shipped capability (the pilot's vehicle): `discover()` takes an optional `prior` cache
snapshot keyed by `full_name`; when a repo's live `pushedAt` equals the cached
`pushed_at` (both non-empty) it skips both `.horus/` `gh api` reads and reuses the cached
focus/next-action/next-prompt, while still recomputing volatile fields (url, branch,
pushed_at, local match). `refresh_cache()` builds the prior map from the on-disk cache.

- **Heuristic is deliberately conservative.** `pushedAt` reflects *any* push, so an
  unrelated commit re-fetches `.horus/`. Chosen over content-hashing/ETag bookkeeping
  because it errs toward freshness, needs no new cache fields, and leaves the cache
  format unchanged. A web-UI `.horus/` edit also bumps `pushedAt`, so edits aren't missed.

Workflow-tuning findings (the actual deliverable — the roadmap NEXT asked to tune from
observed friction):

1. **Hand workers the known pre-existing test-failure baseline.** The worker spent effort
   diagnosing whether a red `test_config` test was its fault (it wasn't — a non-portable
   forward-slash path assertion on Windows, `config.py` untouched). The supervisor brief /
   handoff template should state known-failing tests so a non-green suite isn't ambiguous.
2. **Name a small phase status vocabulary** (`planned/delegated/accepted/blocked`) in the
   `horus-execution` skill + `execution.md` template; the table had a `review` column but
   no "accepted" status, so acceptance had to be improvised.
3. **The handoff template's "Suggested Durable Horus Updates" section paid off** — it
   gave the supervisor a ready routing list for this closure. Keep it.

Implication: the NEXT step folds findings 1–2 into the bundled skill text and the
`execution.md` scaffold (small, single-surface — `continue-as-is`).

## 2026-06-29 - Project Execution Via Prompts, Skills, And Handoffs First

Project the new execution workflow into Claude/Codex through `horus execution`
prompts, structured `.horus/temp/` worker notes, and a bundled `horus-execution`
skill before generating native agent configuration files.

Reasoning:

- Claude and Codex already have native subagent/custom-agent surfaces, but users may
  have personal/project agent configs that Horus should not overwrite or own by
  default.
- A target-aware supervisor prompt plus a worker handoff template gives the main
  value immediately: phase discipline, model-tier routing, and reviewable worker
  output.
- Keeping model tiers symbolic (`frontier`, `standard`, `economy`) avoids baking
  transient model names into durable project files while still letting each local
  agent resolve the tier to current availability.
- Native agent-file generation can be added later if the pilot shows repeated
  boilerplate and a clear safe ownership boundary.

Implication: `horus-execution` is an opt-in supervisor skill. It tells agents when
to use subagents/workers, but durable lane updates still happen only after
supervisor review.

## 2026-06-29 - `execution.md` Is A Fluid Active Plan, Temp Notes Are Worker Handoffs

Add `.horus/execution.md` as an optional tracked lane for the currently active phased implementation plan, and `.horus/temp/` as a gitignored scratch area for worker/subagent handoff notes.

Reasoning:

- Large features often benefit from a stronger supervisor model decomposing the work and cheaper/faster worker models implementing isolated phases.
- The implementation worker has the freshest context about files changed, tests run, surprises, and risks, so it should write a factual phase handoff note.
- Durable Horus lanes still need review and routing judgement; the supervisor should distill accepted worker notes into `roadmap.md`, `features.md`, `decisions.md`, `history.md`, and session summaries.
- `execution.md` should stay fluid and replaceable when the next roadmap item starts. It is not a changelog or durable history.

Implication: workers may update `.horus/temp/*.md`; supervisors own durable lane updates. Future native Claude/Codex projection should consume this file without making phased subagent execution mandatory for simple tasks.

## 2026-06-29 - Every NEXT Carries An Execution Recommendation

When an agent authors `roadmap.md` `next_action`, it must also author `execution_recommendation`.

Reasoning:

- The decision to use direct single-agent work versus a phased supervisor/worker plan belongs at the handoff point, before the next session starts.
- Keeping the recommendation in `roadmap.md` frontmatter makes it visible with the NEXT without forcing every project or task to fill `execution.md`.
- `execution.md` should be created or refreshed only when the recommendation is to plan execution; simple or low-risk tasks can explicitly stay `continue-as-is`.

Implication: `horus close --check` treats a missing recommendation as stale continuity, and the dashboard shows the recommendation beside NEXT.

## 2026-06-29 - Omnigent Is An Interop Target, Not Horus's Core

Keep Horus separate from Omnigent/OmniAgent rather than integrating it as a dependency or deferring Horus's core to it.

Reasoning:

- Omnigent is already a broad meta-harness: server + runner, WebSocket-hosted sessions, multi-user collaboration, policies, sandboxes, DB-backed session state, agent YAML, and many native harness bridges.
- Competing with that execution/auth/policy surface would pull Horus away from its strongest differentiator: durable repo-local project continuity that native Claude/Codex sessions can use even when Horus is not running.
- Horus should keep wrapping official CLIs where needed, but only to serve continuity, closure, dashboard visibility, project inventory, and cross-machine pickup.
- The useful boundary is interop, not replacement: Horus can export `.horus` state to Omnigent as project context/tools, and may later display Omnigent session metadata when configured, while Omnigent owns orchestration/auth/sandboxing for sessions started through it.

Implication: future specs should avoid "build a general agent harness" unless the feature directly advances Horus continuity. If a user wants shared live multi-agent sessions, Omnigent is the likely host; Horus should make that host better informed by `.horus` state.

## 2026-06-24 - Project-First Product Shape

Horus should be project-centric rather than Telegram-first.

Reasoning:

- Telegram is useful for remote control, but not the core.
- The strongest value is preserving project continuity across agents, accounts, environments, and days.
- The dashboard should start from projects and show recaps, roadmap, decisions, and sessions.

## 2026-06-24 - No Identity Profiles In MVP

Do not introduce abstract identity profiles yet.

Use concrete accounts directly, such as `claude-personal`, `claude-work`, `codex-personal`, or their equivalent config entries.

Reasoning:

- Current needs do not require cross-tool identity bundles.
- Identity profiles would add abstraction before there is pain.
- The dashboard should organize by project and show accounts/environments inside the project view.

## 2026-06-24 - Repo-Local `.horus/`

Project continuity should live inside each repository.

Initial structure:

```text
.horus/
  project.md
  roadmap.md
  decisions.md
  sessions/
```

Reasoning:

- Native Claude/Codex sessions can use the context without Horus running.
- Project continuity travels with the project.
- Horus remains a helper/control panel, not a required runtime.

## 2026-06-24 - Git Policy For Sessions

Commit durable project state:

```text
.horus/project.md
.horus/roadmap.md
.horus/decisions.md
```

Ignore local session summaries by default:

```text
.horus/sessions/
```

Reasoning:

- Sessions are useful context for Horus and local continuity.
- They may contain private operational/account details.
- Durable state should be consolidated into project, roadmap, and decisions.

## 2026-06-24 - Both `AGENTS.md` And `CLAUDE.md` Stay Native

Do not force a single canonical instruction file.

Use Horus-managed shared blocks:

```md
<!-- HORUS:BEGIN shared-instructions -->
...
<!-- HORUS:END shared-instructions -->
```

Reasoning:

- Codex and Claude have native conventions.
- The user does not want to manually reconcile diffs.
- Horus can safely sync marked shared sections and warn about drift elsewhere.

## 2026-06-24 - Closure Is Part Of The Workflow

A project-moving session is not complete until continuity is updated.

Reasoning:

- Sessions go stale.
- The user often shifts attention and returns the next day.
- Horus should preserve useful context before the user has to decide whether to resume an old session.

Closure mode should be restricted to:

- `.horus/**`;
- `AGENTS.md`;
- `CLAUDE.md`.

It should not continue source-code edits after the user has walked away.

## 2026-06-24 - Context Rollover Is Valuable

Horus should eventually recommend closure when a session appears near useful context/quota limits.

Reasoning:

- Large sessions become expensive and harder to resume.
- Quota windows can make closure-before-refresh useful.
- A fresh session should be able to continue from `.horus/` state instead of carrying old context.

## 2026-06-24 - First Version Scope: Continuity + Dashboard, Execution Deferred

The first shippable Horus is: the `.horus/` convention, `horus init`, doctor checks, closure routines, and a read-only multi-project dashboard. Agent execution / multi-session is deferred.

Reasoning:

- The `.horus/` convention + managed instruction blocks already deliver most continuity value with zero code; the first code must add value beyond the convention (enforcement, checks, cross-project aggregation), not just render files.
- The dashboard is built early despite being thin before execution, because the user can clone several existing projects to populate it and wants it working in v1.
- Multi-session execution is the hardest layer and the least urgent: Claude Code and Codex apps already let the user run both from the same project folder by hand, so its absence is not blocking.

## 2026-06-24 - Closure Is Hybrid, Phased To Avoid Pulling In Execution

Closure verifies first; it generates a summary only when one is missing/stale.

Phasing:

- v1: Horus verifies continuity (no agent spawned). If a summary is missing/stale, Horus emits a closure prompt that the already-running in-loop agent executes.
- Later (once the execution layer exists): Horus autonomously spawns a summarizer subprocess for the missing summary.

Reasoning:

- The "spawn a summarizer" path needs an agent runner (the deferred execution layer); the verify path does not.
- Delegating to the in-loop agent keeps the hybrid UX while keeping v1 free of the execution build.

## 2026-06-24 - Instruction Drift Check Must Normalize Cross-References

`horus doctor instructions` cannot use naive byte-equality on the shared managed blocks.

Reasoning:

- The `HORUS:BEGIN/END shared-instructions` blocks in `AGENTS.md` and `CLAUDE.md` are intentionally not identical: each ends with a line pointing at the other file ("keep aligned with the matching block in CLAUDE.md" vs "...AGENTS.md").
- The drift checker must normalize/ignore that cross-reference line, or it will report false drift on every run.

## 2026-06-25 - Cognitive Routines Ship As Claude Skills; rulesync Is The Portability Path

The context-aware / LLM parts of the routines (`consolidate`, `distill-history`, and the previously-deferred `infer`) ship as **native Claude Code skills** that run *inside* the app. The files-only `horus` CLI commands stay the deterministic signal layer + the headless/fresh-session path.

Reasoning:

- A skill runs in the active session, so it sees the **live context window** — decisions and work from the conversation that aren't on disk yet. The CLI pre-pass is blind to that (files + git only). Session-closure consolidation is exactly where that context is most valuable.
- This pulls the *interactive* LLM routines out of the MVP3-deferred bucket: the native app already supplies the agent runtime, subscription auth, and context. Only the **unattended/orchestrated** path (Horus spawning its own session) still needs the deferred execution layer. Notably this makes LLM-based `infer` available now (it was deferred only because Horus couldn't call an LLM).
- The skill and the CLI's printed ritual both derive from `docs/routines.md` — one source for the routine, not two.

Distribution / install-on-demand:

- Skills are bundled as package data and ship on PyPI with the CLI.
- `horus init` scaffolds project skills into `.claude/skills/<name>/SKILL.md` (`--no-skills` opt-out, same no-clobber discipline as `.horus/`).
- For already-initialized repos: version-stamp each skill so `horus doctor` warns on missing/stale, add `horus skill install [--project|--user] [--force]`, and have the file-only commands **nudge** (not gate) toward the skill when it's absent. The CLI path stands alone.

Portability (Phase 3, deferred behind Claude-first):

- **rulesync** (verified 2026-06-25) now treats skills as a first-class feature: native for Claude Code, and "**simulated**" for Codex CLI (which lacks native project skills) by copying to `.codex/skills/` referenced via instructions. Workflow: `rulesync generate --targets "*" --features skills` (and `rulesync import` the other direction).
- So the Codex/other-tool port becomes a rulesync *projection*, not a hand-port — refines the earlier "defer rulesync" decision: rulesync is now the chosen mechanism for the skill/command/instruction layer, and could later subsume `reconcile`. Still deferred behind Claude-first; author native `SKILL.md` now and keep skills self-contained so `rulesync import` picks them up cleanly. rulesync is npm/Node, so Horus shells out / documents it — never embeds. See [[horus-core-constraints]].

## 2026-06-24 - Defer rulesync Integration To Post-MVP

Do not integrate `rulesync` (or build instruction/skill projection) until after the first MVP.

Reasoning:

- It adds an external dependency to prove a convenience that is not the core thesis (continuity is).
- `rulesync` already does conversion well, so the eventual choice is "embed/shell out," not "build" - nothing to prove early.
- Adding it now risks being a feature that ends up unused before the core is validated.

## 2026-06-24 - Distribute on PyPI via Trusted Publishing; uv for build

Publish `horus-harness` to PyPI; do not pursue npm (the project is Python, not TypeScript).

Decisions:

- Release via GitHub Actions **Trusted Publishing** (OIDC) on a published Release - no long-lived PyPI token stored anywhere (`.github/workflows/publish.yml`, environment `pypi`).
- Build with `uv` (`uv build`); publish with `uv publish --trusted-publishing always`.
- Real working code is published rather than a name-holding stub, which is a stronger, anti-squatting-safe claim.
- Package author is name-only (no email) to avoid publishing a personal address on PyPI.
- Consumers install via `uv tool install horus-harness` / `uvx --from horus-harness horus`, or pip.

Reasoning:

- Subscription-auth / lightweight constraints are unaffected by packaging; this is pure distribution.
- Trusted publishing avoids secret management and matches the project's security posture.

## 2026-06-24 - License: Apache-2.0

License the project under Apache-2.0 (initially drafted as MIT).

Reasoning:

- Permissive OSS with an explicit patent grant and clearer terms than MIT.
- As sole copyright holder, future versions can still be relicensed/commercialized; only an already-published version stays under its license. Loosening later is easy, tightening is hard - Apache-2.0 is a safe permissive default without giving up that optionality.
- To preserve relicensing freedom if outside contributions arrive, require a DCO/CLA or stay sole author.
- Repo made public (was private) so GitHub Environments are available for the `pypi` trusted-publishing environment.

## 2026-06-24 - Infer Project State From Existing Files (Deterministic)

`horus init` seeds `.horus/` from existing files instead of blank templates; `horus infer` exposes/re-runs it.

Approach:

- Mine README, ROADMAP/TODO/PLAN, PROJECT_STATUS.md (glob-discovered), and CLAUDE.md/AGENTS.md (managed block stripped) for title, description, status, current focus, and roadmap tasks.
- Tasks come from `[ ]` checkboxes AND from leading status emoji (✅/⬜/🚧 -> done/todo/partial), which many hand-written status docs use as checkboxes; plus plain bullets under roadmap/TODO-like headings.
- Deterministic, no model calls (matches the deterministic-first stance, like reconcile). `--no-infer` forces blank templates; `horus infer --write [--force]` re-populates placeholder `.horus/` files.

Reasoning:

- Most repos already encode their state; starting from zero discards it.
- Known limitation: rich prose/emoji status docs extract partially (multi-line bullets truncate at the first line). The high-quality version is a future agent-assisted `horus infer` driving the official CLI (no API keys) - fits the deferred execution layer.

## 2026-06-24 - Deterministic Inference Stays Default; LLM Path Deferred

Keep inference deterministic by default; add an opt-in agent-assisted path later (not now).

Reasoning:

- The user is open to an LLM check "if it genuinely gives better results," but neither `claude` nor `codex` CLI is on PATH in this environment, and an LLM path is the deferred execution-layer work (Horus must drive the official CLI, not call an API).
- Deterministic inference was made strong enough to cover the common cases: explicit `NEXT STEP:` / `Next:` banners (highest priority for current_focus), status emoji as checkboxes, `[ ]` checkboxes, and bullets under roadmap/TODO headings.
- An agent-assisted `horus infer --agent` remains a logged future enhancement for unstructured prose, to land with the execution layer.

## 2026-06-25 - Remove Deterministic Inference; LLM-Based `infer` Under MVP3

Removed the deterministic inference (`horus/infer.py`, the `horus infer` command, init-time mining). Supersedes the 2026-06-24 "Infer Project State (Deterministic)" and "Deterministic Inference Stays Default" decisions.

Reasoning (from a real agent's review of the seeded `.horus/` in fabric):

- Brittle parsing truncated multi-line bullets mid-sentence and produced empty scaffold sections.
- Copying existing prose into `.horus/` created a second, drifting source of "what's next" alongside the project's own docs — against the don't-duplicate ethos.

New approach:

- `horus init` scaffolds clean templates + a `.horus/README.md` that explains the structure and says: this is the single concise source; distill from the project's canonical docs and point at them, don't maintain duplicates; mark superseded docs as stale.
- Rich population becomes the **LLM-based `horus infer`** (MVP3, CLI-spawn): follow doc pointers, distill clean project + roadmap (planned/in-progress/done), mark old docs stale, prompt the user when unclear. Deferred with the rest of the execution layer (no `claude`/`codex` here to drive).
- Near term, the in-loop agent populates `.horus/` from canonical docs, guided by the README + managed block.

The four sibling repos' code-generated `.horus/` content was reset to clean templates + README.

## 2026-06-25 - Agent Execution Is the Next Major Phase, Deferred Until a CLI-Equipped Machine

The execution layer (launching official agent CLIs as subprocesses, multiple isolated accounts, live oversight) is the project's core wedge and the agreed next major phase. Deferred for now because `claude`/`codex` are not installed on the current machine, so the subprocess-driving layer cannot be end-to-end tested here.

Locked approach (so resumption is clean):

- Build order: the spawn primitive + session/process registry FIRST; the live oversight app comes after, built on the registry.
- First real adapter: **Claude Code** (`claude -p --output-format stream-json`, `--resume`, `CLAUDE_CONFIG_DIR` per account); Codex second.
- Thin owned adapter against a shared contract (`spawn`/`resume`/`parse_event`/`permission_flags`); a fake adapter can validate orchestration on any machine, including this one.
- Multi-account isolation via per-account home dirs + a startup identity check.
- The SQLite registry (previously deferred) becomes justified here, once there are real live processes to track.
- Turning the static dashboard into a live oversight app is part of this phase, not before it.

Reasoning:

- Don't ship a subprocess-driving layer that can't be run/tested; build it where the CLIs live (e.g. the VM / another machine).
- Keeps faith with the core constraints: subscription-auth only, official CLIs, lightweight (see [[horus-core-constraints]]).

## 2026-06-24 - Defer the SQLite Session Registry; Keep Session Continuity File-First

Do not build the SQLite session/event registry or persisted session states yet.

Reasoning:

- Session `.md` files are local, gitignored, ephemeral context that distills into the durable files (project/roadmap/decisions); they are not a long-lived entity to manage in a DB.
- At solo scale (a few projects, dozens of sessions) re-parsing markdown is instant, so a DB index adds no real performance value.
- Session states (`closing`/`needs_closure`/`closed_stale`) presuppose Horus orchestrating sessions — that is the deferred execution layer. Until then they are heuristics computable on the fly from file metadata.
- A machine-local SQLite store cuts against the file-first, git-synced, lightweight ethos.

Instead (still file-first, no DB): staleness/context-rollover signals derived from mtime/age/git, surfaced in doctor + dashboard; and `horus close --commit` to close the multi-machine sync seam. Revisit the registry only when scale hurts perf or the execution layer lands.

## 2026-06-24 - Dashboard: Explicit Next-Step Banner + Clickable Roadmap Breakdown

- The dashboard NEXT callout lists up to 3 suggested directions (not a strict order): the explicit `current_focus` banner first, then in-progress tasks, then open tasks. Goal is "a few ideas of where to go next," not just the single next action.
- The roadmap progress count (e.g. 21/39) links through to an anchored, state-grouped breakdown (Open & in progress / Completed) so the items behind the number are one click away.

## 2026-06-25 - Structure v2 + distillation routines (prototyping in fabric, not yet locked)

Using `fabric-metadata-driven-medallion` as a live design fixture (user-steered, commit `a39d118`) to evolve the `.horus/` structure beyond the canonical four files before packaging it back into Horus. **Not locked** — the drift between fabric and Horus's templates/dashboard/managed-block is intentional during ideation.

Structure direction (6 lanes, each in its own lane):

- `project.md` — vision / shape / boundaries / current focus.
- `roadmap.md` — open **action points** only (any type), pruned when done.
- `features.md` — **capability ledger**: shipped / in-progress / planned *packages*. Status only; action points live in `roadmap.md`. Distinct from roadmap because a feature is a closed shippable unit, not a task.
- `decisions.md` — durable rules + reasoning, dated.
- `history.md` — curated "bumps in the road" (lessons/war-stories), NOT a log and NOT open issues.
- `sessions/` — local ephemeral, distills upward.

Key insight: a multi-list structure (roadmap vs features) only stays honest if a **routine owns the routing**, not human discipline. That motivates two new LLM-driven (CLI-spawn, MVP3 family) routines, alongside the deferred `infer`:

- **`consolidate`** — distillation/routing pass over a live `.horus/`: on ship, close roadmap action points and write/update the `features.md` row; prune done/stale; distill session summaries into the durable files; flag roadmap↔features overlap. Runs during `close` / on demand.
- **`distill history`** — compress a giant raw log (e.g. fabric's 1538-line `docs/HISTORY.md`, copied into `history.md` as the fixture) into the high-signal curated subset. Most valuable when onboarding Horus into a long-running project with a large existing changelog.

Split of work: the file-structure changes (templates, README, managed block, **dashboard parsing** of `features.md`/`history.md`) are NOT LLM-dependent and can be packaged once the structure locks. The two routines are LLM-shaped distillation → execute under MVP3 (need `claude`/`codex` to drive), but their contracts are designable now against fabric. See [[horus-locked-decisions]].

Reasoning:

- Designing against a real long-running project (fabric) surfaces the real failure modes (roadmap/features duplication, giant-log onboarding) that blank templates hide.
- Keeps faith with the lightweight ethos: `history.md`'s end state is the distilled subset, not the verbatim archive — the copy is input for `distill history`, not the deliverable.

## 2026-06-25 - Routines Are Agent-Delegated First (pre-pass + emitted prompt), Autonomous Variant Deferred

`horus consolidate` and `horus distill-history` ship as **agent-delegated** routines: Horus runs a deterministic, read-only pre-pass (parse the lanes, detect candidates, report signals) and the CLI prints a ritual prompt for the **in-loop agent already running in the repo** to execute. Nothing is spawned. This mirrors the established `horus close` phasing (see "Closure Is Hybrid, Phased To Avoid Pulling In Execution").

Reasoning:

- Makes a *working, invocable* prototype possible on any machine — including ones without `claude`/`codex` installed — because the LLM is whatever agent is already in the loop. This is what lets the user install the CLI and run the routines on other projects now, ahead of MVP3.
- The autonomous variant (Horus spawns its own summarizer/consolidator subprocess) needs the deferred execution layer; the verify/emit path does not. Forward-compatible: the same pre-pass + prompt can later be handed to a spawned agent instead of printed.
- Edit scope is `.horus/**` only (tighter than `close`, which also touches AGENTS/CLAUDE); routines never edit source. Idempotent, never-invent. Full contract in `docs/routines.md`.

Also decided this session: structure v2 (`features.md` + `history.md`) is no longer "not yet locked" for the **non-LLM** parts — templates, managed block, and dashboard rendering shipped and are dogfooded in this repo. `features.md`/`history.md` are `RECOMMENDED_FILES` (warn-if-missing, not fail) so pre-v2 repos migrate gently. The overlap heuristic strips project-name tokens and requires ≥2 distinctive shared tokens to avoid false positives. See [[horus-locked-decisions]].

## 2026-06-25 - Codex Rollout Telemetry Can Bootstrap Context Warnings

Use local Codex rollout JSONL as a read-only, best-effort source for the first context/usage warning.

Reasoning:

- A real Codex session records `token_count` events under `$CODEX_HOME/sessions`, including `last_token_usage`, `model_context_window`, and rate-limit percentages.
- That gives Horus enough signal to warn during `horus close` and in the dashboard when a project is near its context or rate-limit budget, without waiting for the full MVP3 spawn/registry layer.
- The inspector must be conservative: read-only, scoped to the matching project `turn_context`, tolerant of missing/schema-drifted files, and never dependent on secrets or auth files.
- This is a bridge, not the final session model. Horus-managed sessions should later get usage directly from adapter events and the registry.

## 2026-06-25 - Project Horus Skills Project Directly To Codex

Project-scoped Horus skills should be written directly to Codex's native repo skill location, `.agents/skills/`, alongside Claude Code's `.claude/skills/`.

Reasoning:

- The current Codex manual says repo skills are discovered from `.agents/skills` from the working directory up to the repo root.
- Claude and Codex both consume the same core `SKILL.md` authoring format, so Horus can project its own bundled skills without adding a conversion dependency.
- Direct projection keeps the Claude-first skill authoring path intact while making the same routines usable from Codex immediately.
- `rulesync` remains a candidate for broader multi-tool sync/projection, especially AGENTS/CLAUDE and future target-specific files, but it is heavier than needed for Horus's own three skills.

## 2026-06-25 - Native App Functionality Comes Before Horus-Owned Sessions

When designing or building a Horus feature, first define how it works inside the
native apps the user already uses: Claude Code and Codex. Prefer their native
surfaces - repo instructions, skills, hooks, and local config - before building a
Horus-owned session runner.

Reasoning:

- The native apps already provide the interactive agent loop, subscription auth,
  context window, permissions UI, and user trust model.
- Horus-owned sessions are still valuable for unattended orchestration, multiple
  accounts/environments, and live oversight, but that layer is less mature and
  should not block useful native workflows.
- Skills are a good native shape for context-aware routines the user or model can
  invoke, while hooks are the right native shape for periodic or event-triggered
  nudges such as context/usage rollover warnings.
- Each future feature spec should state the native Claude path, native Codex path,
  and only then the Horus-owned/session path if native surfaces are insufficient.

## 2026-06-25 - Companion App Before Owned Session Orchestration

The first "real app" slice should be a tiny always-on-top Horus companion/mascot,
not the full Horus-owned session runner.

Reasoning:

- A visible companion makes Horus feel active and available while keeping the
  actual agent loop inside Claude Code/Codex for now.
- Clicking the companion to open the dashboard gives immediate product value
  without inventing a new control plane.
- The companion becomes a natural home for native-app bridge signals: usage
  rollover, closure needed, stale summaries, uncommitted continuity, and later
  hook/session health.
- It preserves the native-app-first rule: build the presence/status layer around
  existing apps before Horus takes responsibility for spawning and supervising
  agent sessions.

## 2026-06-25 - Read Claude Usage Via The OAuth `/usage` Endpoint

Claude Code exposes no subscription usage to hooks or transcripts, but the data its
`/usage` panel shows comes from `GET https://api.anthropic.com/api/oauth/usage`
(endpoint found in the CLI binary), authenticated with the OAuth token Claude Code
already stores in `~/.claude/.credentials.json` plus header `anthropic-beta:
oauth-2025-04-20`. It returns `five_hour.utilization`, `seven_day.utilization`,
`resets_at`, and a structured `limits[]` array. `horus/claude_usage.py` reads it with
stdlib `urllib` (no new deps) — the Claude peer of the Codex rollout telemetry in
`codex_usage.py`.

Threshold → closure: `horus hook install --target claude` writes a `.claude/
settings.json` `Stop` hook running `horus usage check --target claude --hook`. When an
active limit ≥ threshold (default 90), the hook emits `{"decision":"block","reason":
<closure instruction>}`, which Claude feeds back as the next instruction — driving the
session into the closure routine. A per-session sentinel (keyed off the hook's stdin
`session_id`) plus the `stop_hook_active` flag fire it once per session.

Reasoning:

- Subscription-auth-consistent: it uses the subscription's own OAuth token, read-only,
  to GET the user's own usage — no API key, matching [[horus-core-constraints]].
- This is the signal that actually matters for Opus (quota, not context — context
  rarely fills before the 5h/weekly limit). Codex already had it via rollouts; this
  closes the gap for Claude Code. Graceful when the token is missing/expired or offline.

## 2026-06-25 - rulesync: stay direct at two tools; own the behavioral layer always

Cross-tool support splits into two layers: (1) **projection** of artifacts (rules,
skills `SKILL.md`, commands, MCP) — what `rulesync` does well across 20+ tools; and (2)
the **behavioral/semantic** layer (hook control protocols — Codex stdout-as-context vs
Claude `decision:block`; usage signal *sources* — Codex rollouts vs Claude OAuth
`/usage`). rulesync cannot touch layer 2; those adapters are inherently Horus's own and
are where the value is. Decision: at exactly two tools (Claude + Codex), keep our
direct, **zero-dependency** projection (dual-write `SKILL.md`, `reconcile`); do NOT
build our own rulesync and do NOT adopt rulesync yet. Adopt it (shell out / document)
for layer 1 only when a **3rd target** appears or the dual-write gets unwieldy — and
keep owning layer 2 regardless. Sharpens [[horus-locked-decisions]] / the earlier
"defer rulesync" calls.

## 2026-06-25 - Mascot: stay Tkinter; fix the fringe offline; no new tool/skill

Researched lightweight desktop-mascot approaches. Conclusion: **stay on Tkinter**
(zero runtime deps, lightest packaging, fine for subtle blink/bob). There is **no**
Claude skill/plugin or mature Python desktop-pet library worth installing; PySide6 is
the only thing with true per-pixel alpha but costs ~80 MB + Qt packaging — overkill.
Tk's `-transparentcolor` is a chroma key (no true alpha), so the white halo is
anti-aliased edge pixels not matching the key. Highest-value fix is in the **offline
Pillow asset step**: edge-color bleed into the partial-alpha ring → erode alpha ~1px →
flatten edge to the colorkey, **keyed on the alpha edge (not on whiteness)** so the
white hat survives. "Active" indicator = a small extra PNG frame set swapped via
`after()` on the same Canvas item. Do NOT add `pystray` (pulls Pillow into the runtime).

## 2026-06-25 - Refinements (after the first live fire):

- **Closure triggers on the 5-hour window only**, not weekly. The 5h limit is the
  fast-moving one you actually hit mid-session; the weekly figure is shown for context
  but does not force closure. A separate, softer weekly-aware nudge is a future feature.
- **The hook drives the context-aware skill, not the file-only script.** The whole
  point of closing inside the live app session (vs a fresh CLI/spawned session) is that
  the agent can see the conversation. `USAGE_CLOSURE_INSTRUCTION` now tells the agent to
  run the `horus-consolidate` skill and fold the session's *context* (decisions + why,
  dead ends, next step) into the lanes — `horus consolidate` (the script) is only the
  signal layer the skill uses, never a replacement, because it can't see the session.

## 2026-06-25 - OAuth Token Auto-Refresh + Account Anchor

The usage→closure hook silently never fired: the on-disk `accessToken` in
`~/.claude/.credentials.json` is routinely stale (Claude Code refreshes in-process and
rewrites the file on its own cadence), so reading it and giving up on expiry meant no
signal regardless of threshold.

Decision: `claude_usage._oauth_token()` refreshes an expired token from `refreshToken`
via `POST https://api.anthropic.com/v1/oauth/token` (client_id
`9d1c250a-e61b-44d9-88ed-5944d1962f5e`, a `claude-cli` `User-Agent` — Cloudflare 1010s
an empty UA) and **persists the rotated pair**.

Reasoning / gotchas:

- Refresh tokens are **single-use**: a refresh that succeeds but doesn't persist burns
  the on-disk token → next refresh `invalid_grant` until re-login. Always persist.
- `.credentials.json` always holds the **currently logged-in** account's tokens (Claude
  Code overwrites on account switch), so the token path is inherently current-account;
  no cross-account staleness check is needed there.
- Account identity for *continuity* comes from `~/.claude.json` `oauthAccount.emailAddress`
  (read-only, no secret) via `current_account()`. Sessions now carry a real `account:`
  tag + a full timestamp (`YYYY-MM-DD-HHMMSS` filename, ISO `date:`), so multiple
  sessions/day don't collide and each is attributable to an account — the anchor a
  future MVP3 "startup identity check" can compare against.

## 2026-06-25 - Default To Native Apps + Agent-Authored Metadata (core, until a session-manager UI)

Core product stance for now: **default to the native agent apps and agent-authored
metadata; do not use Python to *infer* judgment metadata.** This holds until Horus has
a proper session-manager UI that owns sessions.

Concretely:

- Judgment metadata — the single next step, the resume prompt, the session summary,
  status — is **authored by the session agent** (at closure, via `horus-consolidate`)
  and stored in `.horus/` frontmatter/files. The dashboard *reads and displays* it.
- The dashboard must **not infer** these. The parser-derived "next step"
  (`roadmap.next_step`) was dropped from the dashboard; NEXT now reads the authored
  `roadmap.md` `next_action`, and the resume prompt reads `next_prompt`. When unset, the
  UI shows a "set it at closure" hint, not a guess.
- Still fine (it's display of explicit content, not inference): rendering the checkbox
  list, the progress count, the features table, git freshness. The line is *inference of
  judgment*, not *rendering of what the agent literally wrote*.
- Extends "The Session Agent Maintains The Lanes, Not Scripts" — same principle, now the
  explicit default until the session manager exists.

## 2026-06-25 - The Session Agent Maintains The Lanes, Not Scripts

The `.horus/` lanes are filled by the **agent running the session**, from the live
conversation context, via the `horus-consolidate` skill — NOT by Python that parses
files and rewrites lane content.

Reasoning:

- The high-value content (decisions + *why*, dead ends, the real next step, what
  shipped) lives in the session's context window, which a file-only script cannot see.
  Deterministic extraction from files can only reshuffle what's already written, and
  earlier attempts at it were brittle (the removed deterministic `infer`).
- So the CLI is a **signal + verification + scaffolding** layer only: `horus close` /
  `consolidate` / `doctor` emit candidates and checks and print the ritual; `init` /
  `session new` scaffold empty templates. None of them write lane *content*.
- The dashboard *reads* the lanes to display them (gitstate, feature buckets, next-step
  highlight) — that's presentation, not maintenance, and is fine. What must never happen
  is a script deciding lane content.
- Clarified in the managed instruction block (templates.py + AGENTS.md/CLAUDE.md) so an
  agent reads this at session start. See also "Cognitive Routines Ship As Claude Skills".

## 2026-06-25 - Git Is The Cross-Machine Transport (MVP2.5 shape)

The multi-machine project overview will **not** use a central server, hosted session
store, or Tailscale for data. Git already syncs the durable lanes
(project/roadmap/decisions/features/history); the overview just needs each machine's
dashboard to read its local clones and **show whether they're fresh**.

Decisions:

- **Dashboard becomes git-aware** (freshness, dirty, behind/ahead) instead of silently
  rendering possibly-stale local files. Deterministic signal layer, no LLM.
- **Config stays per-machine.** `~/.horus/config.toml` lists local paths and is not
  synced; "path changes per machine" is avoided by never sharing it. Portable identity
  (remote URL) is optional/YAGNI until cross-machine dedup is actually wanted.
- **Sessions stay local + distill into the committed lanes** (upholds Git-Policy-For-
  Sessions: ephemeral + may hold private account details). Cross-machine memory flows
  through `decisions.md`/`history.md`/`roadmap.md`, not raw sessions.
- **No implicit network on render.** behind/ahead come from existing refs; an explicit
  "fetch all" updates them. `fetch` is allowed (no working-tree mutation); `pull`
  (mutating) is shown as a command, not auto-run — preserving the read-only-on-files
  invariant.
- **Tailscale** is reserved for reaching a *running* Horus's live state (MVP3), not for
  static durable state. `tailscale serve` of the read-only dashboard is an optional ops
  convenience, no code.

## 2026-06-25 - Adapter Contract Shape: Thin ABC + Four Pure Methods, Fake Mirrors stream-json

The MVP3 agent-adapter contract (`horus/adapters/`) is an ABC (`AgentAdapter`), not a
bare Protocol, so the heavy, identical parts live once in the base and real adapters stay
thin. An adapter implements exactly four **pure, individually-testable** methods —
`permission_flags(posture)`, `build_command(spec, resume_id=...)`, `build_env(spec)`,
`parse_event(line)`. The base owns `spawn`/`resume`, subprocess launch+streaming, and
`AgentRun` (the iterable handle that fills in `session_id` from the first event and flips
status to a terminal value at end-of-stream). `SpawnSpec` / `AgentSession` / `AgentEvent`
/ `PermissionPosture` / `EventType` normalize the I/O; `AgentSession`'s fields are exactly
the future registry row `(agent, account, project, environment, pid, session_id, status)`.

`FakeAdapter` implements the *whole* contract in memory over a JSON-lines stream that
mirrors the **shape** of stream-json (init → text/tool → result), so it exercises the same
`parse_event` → `AgentRun` path a real adapter will, and lets the orchestration layer be
built/tested on a machine with no `claude`/`codex`. The real Claude Code adapter (next)
only fills in the four methods. Implements the locked "thin owned adapter against a shared
contract; a fake adapter validates orchestration anywhere" approach.

## 2026-06-25 - Session Account Tag Is an Alias, Never the Raw Email

`current_account()` reads the logged-in email (`~/.claude.json` → `oauthAccount.emailAddress`)
as the "which account ran this" anchor, but session summaries distill upward into the
committed lanes and the repo is public — so the raw email must never reach a summary.
`config.alias_for(identifier)` returns a configured alias from `~/.horus/accounts.toml`
(its own file, so the projects serializer in `config.py` can't clobber it), or a stable,
non-reversible `acct-<sha6>` fallback that keeps accounts distinguishable without exposing
the email. `horus session new` records the alias; `horus account [--set ALIAS]` shows the
detected account and manages the mapping. Refines the prior "account-tagged sessions" work,
which wrote the email directly. See [[horus-core-constraints]] (subscription-auth, no secrets/PII in the repo).

## 2026-06-25 - Claude Code Adapter: Ground-Truth Schema + Contract Refinement

Built `horus/adapters/claude.py` against the *real* `claude` 2.1.191 headless surface (probed
directly, not from memory):

- Spawn `claude -p <prompt> --output-format stream-json --verbose`; stream-json under `-p`
  **requires** `--verbose`. Resume `--resume <session_id>`; the id is echoed in the
  `system/init` event, so no pre-assigned id is needed (`--session-id <uuid>` exists if we
  later want to set it). Posture → `--permission-mode` (plan/acceptEdits/bypassPermissions/
  default; no pure read-only mode, so READ_ONLY→plan). Per-account isolation via
  `CLAUDE_CONFIG_DIR` (unmapped account → ambient login).
- **Contract refinement forced by reality:** `parse_event` now returns a **list** of events,
  not `AgentEvent | None` — one `assistant` line routinely carries several content blocks
  (text + tool_use), which the single-event shape silently dropped. Also `stdin=DEVNULL` in
  the base launch (Claude waits ~3s on stdin otherwise). Sharpens the prior "Adapter Contract
  Shape" decision; the fake had masked the gap because both were authored together.
- Subscription-auth only: runs the user's own logged-in `claude`; no API key. spawn+resume
  proven live (spawn → session id; resume of that id recalled context from the first turn).

## 2026-06-25 - Multi-Account Isolation: Per-Account CLAUDE_CONFIG_DIR + Alias-Round-Trip Identity Check

Per-account isolation runs each account under its own `CLAUDE_CONFIG_DIR` (a separate
Claude login/home), mapped alias→dir in `~/.horus/accounts.toml` `[config_dirs]` (its own
section, preserved alongside `[aliases]`). `ClaudeAdapter` defaults its `config_dirs` from
that map and sets the env per spawn.

The startup identity check uses the **alias round-trip** as the equality test:
`verify_account(account)` reads `<config_dir>/.claude.json` → `oauthAccount.emailAddress`,
then asserts `config.alias_for(email) == account`. This reuses the existing email→alias map
(no new identity store) and never exposes the email beyond the in-memory `IdentityCheck`.
`_launch` runs the guard **before** any subprocess and raises `AccountMismatch` when a
*mapped* account's login doesn't match — so a misconfigured account can't silently run
under the wrong login. The guard fires only when an explicit per-account dir is configured;
ambient single-account runs (e.g. the spawn/resume proof) are unaffected.

## 2026-06-26 - Attended (`horus open`) vs Headless (`horus run`) Session Launch

Horus needs both launch modes. `horus run` is **headless** (`claude -p --output-format
stream-json`): one-shot, streams events, blocks, ends `exited`. `horus open` is **attended**:
it opens the real `claude` TUI in its *own terminal window* the user types into, and returns
immediately, so the session is genuinely `running` until the user exits.

Mechanics that make attended tracking work:
- **Pre-assigned `--session-id` (uuid4).** Interactive runs don't stream stream-json back to us,
  so we can't parse the id from `system/init`. Passing `--session-id` means we know it up front
  and can register the session before it produces anything.
- **`CREATE_NEW_CONSOLE` (Windows).** Launching `claude.exe` this way gives it a real console the
  user can interact with AND makes the returned PID the child's own — so `registry.reconcile()`
  flips the record to `exited` exactly when the user closes the window. (`os.kill`-on-Windows
  caveat from the registry decision is why liveness uses the WaitForSingleObject path.)
- Same `build_env` (per-account `CLAUDE_CONFIG_DIR`) and `verify_account` identity guard as the
  headless path. `horus/launcher.py` isolates the platform bits; `interactive_command` is the
  adapter's attended-argv builder (Claude + Fake have it; Codex will when it lands).

This is what makes the dashboard show *live* sessions, not just finished ones — the visible
payoff of the registry + oversight work.

## 2026-06-26 - Strategic Review After MVP3 (on track? reinventing? the wedge?)

A mid-project evaluation against the founding docs (`product_interview.md`, `plan.md`,
`codex-plan-review.md`). Conclusions, for continuity:

- **On track, with disciplined deliberate deviations.** plan.md's 6 steps are largely
  done; the divergences were all reasoned and documented: Claude-first not Codex (machine
  had Claude), JSON registry not SQLite (lightweight; SQLite re-justified only at scale),
  companion/mascot emerged, Telegram fully deferred. The one strategic fork: the external
  review thought *Telegram remote* was the wedge; we pivoted to **continuity-first** —
  judged correct (Telegram bots are commoditized; continuity is not), but remote control
  remains a logged later need.
- **Not meaningfully reinventing the wheel.** We build intentionally *thin* versions of
  things that exist only as heavy platforms (claw-orchestrator = multi-CLI subprocess
  runtime; tmux/kube-coder = sessions; PACE = memory; rulesync = rule projection). Watch-
  item: the **execution layer is the part most at risk of drifting into "yet another
  orchestrator"** — keep continuity the headline.
- **Biggest value others don't provide:** (1) continuity that **survives without Horus
  running** and is agent-maintained (no competitor does this — they're runtimes you live
  inside); (2) **subscription-auth, multi-account, official CLIs** (no API keys); (3)
  **usage→closure** — reading the subscription's own `/usage`/rollouts to divert an
  over-budget session into a continuity-preserving close (the single most novel feature).
- **Honest risks:** account isolation ≠ security isolation (don't oversell); CLI-automation
  is ToS-adjacent (re-check before public); the "vendor-neutral contract" is **unproven at
  N=1** until the Codex adapter lands; lightweight-vs-creep (mascot + growing execution);
  continuity debt (this very backlog).
- **Next phases:** MVP4 = prove the abstraction (Codex adapter) + actionable oversight
  (terminate/resume from UI) + user's flagged UI work + `horus doctor compat`. MVP5 =
  autonomous closure (the thematic heart, now unblocked) + stale-session detection + LLM
  `infer`. MVP6 = optional remote surfaces (Telegram/Tailscale). Plus the new **Cross-tool
  interface sync** track (two-layer model; see its own decision and roadmap section).

## 2026-06-26 - Unified In-App Terminal: Own xterm.js Viewer, Not a VS Code Extension

The Control tab launches real agent sessions and hosts them as **in-app terminals** — the
actual `claude`/`codex` TUI under a pseudo-terminal, rendered with xterm.js *inside* the
dashboard. When the question arose (real TUI + window controls → "is this still its own app,
or pivot to a VS Code extension?"), the decision was: **keep the viewer in Horus.**

Reasoning:

- The vision is *oversight across projects/accounts*, with attach/detach and (later) remote
  streaming. That is **multi-host terminal multiplexing**, which a VS Code extension does NOT
  provide for free (its integrated terminal is local to that instance). Once "stream from
  other machines / re-attach" is the requirement, VS Code's free terminal advantage collapses.
- Horus is a Python *brain* (CLI + adapters + registry + files); the dashboard is one
  front-end. The right move is to build the **host/attach protocol** and keep the viewer ours
  (a thin xterm.js client). VS Code could later be *a* viewer (webview), never the strategy —
  and coupling the control surface to VS Code would betray the terminal-first/editor-agnostic
  thesis (Claude Code/Codex users aren't all in VS Code).
- Architecture = **session-host vs viewer** (tmux-style). The host (`pty_host.py`) owns PTYs and
  keeps them alive regardless of who's watching; a viewer attaches by replaying scrollback +
  live bytes over SSE and detaches by disconnecting. "Drag out" = a **pop-out window** = a second
  viewer of the same persistent session. This only works for sessions **Horus started** (it owns
  the PTY); attaching to an externally-started TUI is infeasible (can't attach a PTY you don't own).
- Scope locked **local + persistent + re-attachable**; **remote deferred** (per-machine daemon +
  tailnet + auth — Tailscale already reserved for live state). Re-attach today spans tabs/reloads
  while Horus runs; surviving a Horus *restart* needs a standalone daemon (deferred). The attach
  protocol is kept transport-agnostic so the remote stage slots in without reshaping it.
- **Monitoring sessions Horus did NOT start** is a separate, read-only future idea: discover
  foreign `claude`/`codex` sessions from the transcripts they already write
  (`~/.claude/projects/<slug>/<uuid>.jsonl`; Codex rollouts already read by `codex_usage`), and
  optionally "continue this here" via `claude --resume <id>` into a Horus-owned PTY. Observe-only;
  no driving a foreign PTY. Noted in roadmap, not built.

## 2026-06-26 - Cross-Platform PTY: pywinpty on Windows, stdlib `pty` Elsewhere (the one accepted dep)

A real agent TUI needs a pseudo-terminal. `horus/pty_session.py` is one byte-oriented handle with
two backends: **ConPTY via `pywinpty`** on Windows, the **stdlib `pty`** module on macOS/Linux.

Reasoning / consequence:

- This **crosses the "zero runtime deps" non-negotiable** ([[horus-core-constraints]]) — accepted
  deliberately, because there is no stdlib Windows ConPTY binding and a real TUI has no zero-dep
  path. The cost is contained: declared as a **conditional** dependency
  (`pywinpty>=2.0; sys_platform == 'win32'`), so macOS/Linux stay dependency-free, which fits the
  user's stated intent to support Mac/Linux later. A pure-ctypes ConPTY was rejected (Windows-only
  anyway, and exactly the 64-bit-handle ctypes trap that already bit `horus focus` — see history.md).
- **xterm.js is vendored** (`horus/assets/vendor/xterm/`, served at `/assets/xterm/`), not a CDN —
  keeps the dashboard local-only/offline and is a JS asset, not a Python dependency.
- Transport stayed **SSE-out + POST-in** (reused the existing stdlib `http.server`); WebSocket is a
  latency optimization for later, not required for a human-paced terminal. base64-framing keeps
  control bytes intact. Verified live: real `claude` TUI renders; keystrokes reach the PTY; two
  concurrent viewers share one session.

## 2026-06-26 - Closure Freshness Is Gated (LLM Authors, Python Detects); the PR Hook Is Pre-Merge

The closure ritual kept leaving stale lanes (e.g. `project.md current_focus` stale since
before MVP3; a growing done-items/undistilled-sessions backlog) even though it ran several
times. Root causes: per-session close and backlog cleanup were **conflated** (so the heavy
backlog half was always deferred), the ritual never enumerated **what the dashboard reads**
(so fields rotted), and **nothing failed** on staleness (so drift was invisible).

Decision — fix it without breaking "the session agent maintains the lanes, not scripts"
([[horus-locked-decisions]]): keep **LLM authoring**, add **deterministic detection**.

- **`routines.freshness_signals` + `horus close --check`** (`closure.freshness_gate`):
  detect (never author) when a dashboard field is stale — lane `last_updated` < newest
  session, empty `next_action`/`next_prompt`/`current_focus`, `next_action` matching a
  Shipped capability (≥3 shared tokens to avoid context-mention false positives). `--check`
  exits non-zero, so closure isn't "done" until the dashboard is fresh. Scoped to
  dashboard-freshness — usage/drift and the mtime-nagging work-commits signal stay in the
  full `horus close` (the latter would otherwise nag within the very session being closed).
- **Skill v3 + CLOSURE_PROMPT**: an explicit **dashboard-contract checklist** (the exact
  rendered fields) and a **per-session-close vs backlog-consolidation split** — the
  structural fix for "the ritual got half-done because the backlog looked huge." Per-session
  close runs every time and is bounded; the backlog pass is opt-in.

The PR hook (user's idea): **a PRE-merge gate, not a post-merge action.** Closure *authoring*
needs the live session context, which exists *before* merge; a merge-time hook has no context
(the rejected brittle path) and could only run deterministic stubs or a context-poor diff
reader. So the same `horus close --check` runs as an **advisory** CI check on PRs
(`.github/workflows/continuity.yml`) — annotates rather than blocks, since `.horus/sessions/`
is gitignored and absent on CI (so CI sees the committed-lane subset + a "code changed without
lane update" git heuristic). Promote to required by dropping the warning fallbacks. The
post-merge *autonomous spawn* (Horus spawns the closer) remains the deferred, weaker option.

## 2026-06-26 - The Pre-Merge Closure Gate Is a Local PreToolUse Hook, Not Just CI

The "pre-merge closure gate" intent (a feature isn't done until the lanes reflect it,
enforced *before* the merge) had shipped only as the advisory CI workflow
(`continuity.yml`). That runs **server-side, after push, and never blocks**, and is blind
to `.horus/sessions/` (gitignored) — so it nudges, it doesn't gate, and it isn't where
the session context that closure *authoring* needs still exists.

Decision: add a real **local** gate as a Claude **`PreToolUse` hook** matching the `Bash`
tool, running `horus close --hook`. The command filters for `gh pr merge` (everything else
passes instantly), runs the freshness gate, and on stale lanes emits
`permissionDecision:deny` with `MERGE_CLOSURE_INSTRUCTION` — Claude blocks the merge and
the agent is diverted to `horus-consolidate` first. This mirrors the usage hook's
block-and-divert, but the trigger is the **action** (merge) rather than **quota**.

Reasoning / shape:
- **Trigger at the merge command**, not at PR-create or push: the latest safe point where
  in-session context is still available, with the fewest false positives. (`gh pr merge`
  only; configurable later.)
- **Block, don't warn** — the CI already covers the soft-nudge posture; the local hook is
  the hard gate. Self-clearing: consolidate → `horus close --check` passes → re-running the
  merge proceeds. Errs toward *allowing* on any checker error (never wedge the user).
- **Matcher is the tool name** (`Bash`), since Claude Code matches PreToolUse on tool name,
  not command substring — so the command itself does the `gh pr merge` filtering.
- **Baked into `horus hook install --kind {usage,merge,all}`** (default `usage` preserves
  prior behavior); Claude-only (Codex has no gh-pr-merge interception surface). The two
  layer: local hook = the gate inside Claude Code; CI = backstop for merges done elsewhere.
- **Known limitation:** the freshness signal is date-granular, so a same-day feature whose
  lanes were already authored earlier that day may pass the gate without a forced re-bump —
  the authored-field checks still apply, but the mtime signal won't fire within the day.

## 2026-06-26 - Codex Account Usage: Used% From Rollout Rate-Limits, Last-Observed

The dashboard Accounts panel shows Codex accounts with the same usage affordances as Claude
(donut ring + weekly bar), sourced from the Codex rollout `rate_limits` that `codex_usage`
already parses — `primary` = 5h, `secondary` = weekly. No new endpoint, no new auth.

- **Used%, not remaining.** Codex's own app shows usage *remaining* (e.g. "5h 99%"); Horus
  shows *used* (1%), because the ring/bar must mean the same thing across agents — it fills and
  reddens as you consume, exactly like the Claude ring. Cross-agent consistency beats matching
  each vendor's display convention. Same source value, just `100 − remaining`.
- **Last-observed, not live.** Claude polls the OAuth `/usage` GET per render; Codex exposes no
  such endpoint, so `latest_account_usage()` reads the newest `rate_limits`-bearing
  `token_count` event across the account's rollouts. Rate limits are account-global (written
  into whatever session was active), so the newest rollout anywhere is the best snapshot — but
  it is only as fresh as the last Codex activity. The UI is framed as "last observed."
- This corrects the initial N=2 shortcut that left the Codex ring permanently gray, which
  conflated per-session *context* usage (genuinely not an account number) with the
  account-global *rate limits* (which are). Context% stays a per-session signal on the
  live-session cards. See [[horus-core-constraints]] (subscription-auth, read-only).

## 2026-06-26 - The Self-Restart Footgun Is Fixed Guard-First (PreToolUse), Daemon Deferred

The MVP5 footgun — an in-app agent restarting/killing the dashboard process that hosts its
own PTY, killing itself mid-task (history.md) — has two candidate fixes: a **lightweight
guard** (refuse the dangerous command) or the **structural daemon** (host PTYs in a process
that outlives the dashboard). We shipped the guard first and deferred the daemon.

Shape: `pty_host.start` injects `HORUS_HOSTED_SESSION=1` + `HORUS_PTY_HOST_PID` into the PTY
env; a Claude `PreToolUse(Bash)` hook (`horus guard-host --hook`) inherits those (it's a child
of the agent's shell) and — **only when hosted** — emits `permissionDecision:deny`
(`templates.HOSTED_RESTART_INSTRUCTION`) for a command that would restart the app
(`horus app`/`dashboard`), kill the host PID, or kill the host by interpreter/name
(`python`/`horus`/`dashboard`). Outside a hosted session it's a no-op, so normal terminals are
untouched; it errs toward *allowing* (never wedge the user). `hook install --kind guard|all`;
coexists with the usage + merge hooks as a second `PreToolUse/Bash` group.

Reasoning:
- **Cross-OS was the deciding criterion** (user-raised). The guard is pure env-vars + string
  matching — identical on every OS; the only OS-flavored part is the *list of recognized
  command spellings* (`kill`/`pkill` vs `taskkill`/`Stop-Process`), which is data, not a
  code-path fork. The daemon is the **opposite**: detach + survive-parent + reap is exactly
  where Windows and POSIX diverge most — the same class of trap that already bit `horus focus`
  (ctypes 64-bit handle truncation) and the `os.kill`-terminates-on-Windows registry caveat.
- **Native-app-first** ([[horus-locked-decisions]]): mirrors the proven usage + pre-merge
  `PreToolUse` gates (block-and-divert), so it slots into the established pattern.
- **The guard only stops the *agent* from triggering it.** A user restart, a crash, or a code
  reload still drops live PTYs — so the structural daemon stays the real fix, deferred and
  tracked in MVP5/MVP4. The two are complementary, not alternatives.

## 2026-06-26 - pywebview Tried and Rejected; Edge `--app` + Mascot Now, Proper App Later

Attempted to graduate the UI shell from "Edge `--app=` window + Tkinter mascot" to a
Python-owned **pywebview** window (to own the window lifecycle: close-window→quit, no stale
tab). **Live-tested on the Win11 dev machine and rejected** — reverted to the prior Edge +
Tk-mascot shell. This supersedes the same-session "graduate to pywebview" idea (it was never
committed).

Why pywebview was rejected (live evidence, not theory):
- **Unstable**: pywebview's WebView2/WinForms integration crashed intermittently with
  `AccessibilityObject.Bounds … maximum recursion depth exceeded` — at startup *and* after the
  windows were up — even with the AppUserModelID call removed. Not shippable when it crashes on
  the developer's own machine.
- **Slow**: tab navigation took ~4 s (the dashboard uses full-page navigation; pywebview's
  wrapper made each reload heavy). The same dashboard in a real Edge `--app` window was fast.
- **Key insight**: a plain Edge `--app` (full Chromium) was both fast and stable, so **the
  Chromium engine is fine — pywebview's wrapper was the problem.** Measuring proved the server
  renders in ~15 ms (cold `/control` 750 ms = synchronous OAuth `/usage` calls), so the lag was
  the shell, not the Python brain.

Decision — a two-tier frontend, with the **Python brain + web UI as the stable contract** (any
window host just loads `http://127.0.0.1:8765`, so hosts are swappable and forward-compatible):
- **Lightweight tier (ships now, via uv): the existing Edge/Chrome `--app` window + the Tk
  mascot.** Fast, stable, zero heavy deps. Accepts the known lifecycle drawbacks for now
  (closing the dashboard window does not quit the app; the 8765-server-leak/single-instance
  gaps remain) — these are the user's accepted trade-offs until the proper app exists. The Tk
  mascot returns (it has real chroma-key transparency, which WebView2 lacks) using the refreshed
  Horus-falcon art.
- **Proper-app tier (planned, separate downloadable package): a real native desktop app** that
  owns the window lifecycle, taskbar icon, and tray. Stack **not yet chosen** — needs more eval;
  the candidates and trade-offs (recorded for that decision):
  - **PySide6 / Qt WebEngine** — bundled Chromium, **stays all-Python (one runtime)**, native
    window/tray/icon, trivial in-process lifecycle; heavy (~100–150 MB). Best fit if staying
    single-language matters.
  - **Electron** — bundled Chromium + **Node (a 2nd runtime beside Python)**; the most mature/
    polished shell (auto-update, tray); heaviest. User said acceptable if it buys stability.
  - **Tauri** — Rust shell + **system WebView2** (the engine that misbehaved here, but via a
    cleaner integration than pywebview's WinForms wrapper) + a JS SPA; tiny binary (~5–15 MB);
    most toolchain (Rust + frontend build).

Reasoning / lesson: don't "graduate" a shell on theory — pywebview *looked* ideal (system
webview, Python, cross-OS) but failed on contact with the real machine. Ship the proven
lightweight thing; make the proper app a deliberate, separately-evaluated choice. See
history.md "pywebview was the worst of both worlds".

## 2026-06-27 - Codex Usage Hooks Must Emit Structured Hook JSON

The Codex usage hook is an active closure diversion, not a plain console warning. Current
Codex hook semantics require `Stop` hooks that exit 0 to emit JSON on stdout, and
`UserPromptSubmit` can inject pre-task context with `hookSpecificOutput.additionalContext`.

Decision:

- Install the Codex usage check on both `UserPromptSubmit` and `Stop`.
- Under threshold, hook mode stays silent and exits 0.
- At threshold, `UserPromptSubmit` emits `hookSpecificOutput` with the Horus closure
  instruction as additional context, so the agent closes before starting another task.
- At threshold, `Stop` emits `{"decision":"block","reason":...}` with the same closure
  instruction, so the just-finished turn is followed by the closure ritual.
- Keep the per-session re-arm sentinel used by Claude, so the hook does not loop or nag.

Reasoning: the previous Codex hook file was installed in the right place, but hook mode printed
plain `[warn] ...` text. That was useful to a human and covered by tests that only asserted exit
code 0, but it was not a valid Codex `Stop` response and would not reliably drive closure.
Codex may still require the user to review/trust the project hook with `/hooks`; Horus can write
the file, but trust remains a native Codex step.

## 2026-06-27 - Codex Supports The Pre-Merge Closure Gate

The pre-merge closure gate is not fundamentally Claude-only. Current Codex hooks support
`PreToolUse` for `Bash`, including structured denial of a supported tool call. Horus's previous
installer policy rejected `--target codex --kind merge` because it assumed Codex only had the
usage/Stop hook surface; that assumption was stale.

Decision:

- `horus hook install --target codex --kind merge` installs a `.codex/hooks.json`
  `PreToolUse` hook with matcher `Bash`.
- The hook runs `horus close --hook`, the same command as Claude, because the parser already
  accepts the native hook input shape and filters for `gh pr merge`.
- Fresh lanes allow silently; stale lanes deny with the Horus consolidation instruction.
- The hosted-session self-restart guard is a separate hook from the PR merge gate; Codex parity
  for that guard was added immediately afterward (see next decision).

## 2026-06-27 - Codex Also Gets The Hosted-Session Guard

After adding the Codex pre-merge gate, the same `PreToolUse`/`Bash` hook surface proved suitable
for the hosted-session self-restart guard too. The guard logic was already app-neutral: it checks
the `HORUS_HOSTED_SESSION` and `HORUS_PTY_HOST_PID` environment markers that `pty_host` injects
for any Horus-hosted PTY, then denies only clear restart/kill-the-host Bash commands.

Decision:

- `horus hook install --target codex --kind guard` installs a `.codex/hooks.json`
  `PreToolUse` hook with matcher `Bash`.
- The hook runs `horus guard-host --hook`, the same command used by Claude.
- The installer keeps the Codex usage, merge, and guard hooks as separate matcher groups so
  reinstalling one does not clobber the others.
- Codex still requires native hook trust review (`/hooks`) for changed project-local hooks.

Reasoning: this is not a separate OS/process-control mechanism. The hard part was already solved
by the env-marker guard design; Codex only needed a project hook projection that matches its
documented hook shape (`hooks.json`, `PreToolUse`, `Bash`, `commandWindows`).

## 2026-06-28 - Cross-Computer View Starts As A Remote Catalog, Not A Runtime

Horus should become useful across the user's Linux machine, VM, desktop, GitHub-backed projects,
and non-git folders without making the lightweight `uv` tool pretend to be a distributed app.

Decision:

- Keep the lightweight CLI/repo tool file-first: it owns `.horus/`, local project registration,
  local accounts, local launches, hooks, and closure checks.
- Use GitHub as the first remote catalog for durable project memory: discover repos that expose
  `.horus/project.md` and `.horus/roadmap.md`, show their focus/next action, and compare them to
  local clones by normalized remote URL.
- Treat the future proper app as an aggregator of machine observations, not a replacement for the
  CLI. Git syncs project memory; Horus app syncs machine observations such as local paths, dirty
  state, running sessions, account availability, and clone freshness.
- Non-git / Google Drive projects will need explicit identity later; remote URL is enough only for
  GitHub-backed projects.

Reasoning: this gives a central-view feeling now for GitHub projects with no daemon, database, or
new auth system beyond `gh`, while preserving the low-friction workflow the user is already
dogfooding in native Claude/Codex windows. A heavier proper app remains justified for multi-machine
snapshot aggregation, live session routing, and lifecycle ownership.
