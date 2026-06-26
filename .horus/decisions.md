# Decisions

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
