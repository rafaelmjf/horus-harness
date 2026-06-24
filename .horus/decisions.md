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

