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

