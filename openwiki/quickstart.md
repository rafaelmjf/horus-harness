---
type: wiki entrypoint
title: Horus Repository Wiki
description: Navigate Horus architecture, control surfaces, continuity model, session isolation, and contributor workflows.
tags: [horus, navigation, architecture]
---

# Horus Repository Wiki

Horus is a Python control plane for official coding-agent CLIs. It keeps shared project orientation and backlog state in repository-local files while keeping credentials, processes, hosts, and dispatch authorization machine-local. It does not replace the Claude/Codex agent loop or own model API keys.

## Architecture map

| Area | Canonical page | Key source entrypoints |
|---|---|---|
| Overall boundaries and surface composition | [Architecture overview](architecture/overview.md) | `horus/cli.py`, `horus/dashboard.py`, `horus/terminal_tui.py` |
| Repo-local continuity, format compatibility, closure, projections | [Continuity](architecture/continuity.md) | `frontmatter.py`, `closure.py`, `initialize.py`, `upgrade.py` |
| Card-backed backlog | [Cards](backlog/cards.md) | `backlog.py`, `backlog_migrate.py`, `backlog_refine.py` |
| Commands and parser routing | [CLI command architecture](cli/commands.md) | `build_parser()`, `main()` in `horus/cli.py` |
| Account isolation, adapters, launch/backend/proxy limits | [Accounts and launch](sessions/accounts-and-launch.md) | adapters, `launch.prepare_interactive()`, `backend.py` |
| Registry, session hosts, browser PTY, worktrees | [Hosts and registry](sessions/hosts-and-registry.md) | `registry.py`, `terminal_sessions.py`, `pty_host.py`, `worktree.py` |
| Dashboard, exposure controls, desktop companion | [Dashboard](surfaces/dashboard.md) | `dashboard.py`, `companion.py` |
| Terminal fallback and TUI cockpit | [TUI](surfaces/tui.md) | `terminal_app.py`, `terminal_tui.py` |
| Envelopes, execution evidence, schedules, supervision | [Dispatch and delivery](operations/dispatch-and-delivery.md) | `envelope.py`, `run_executor.py`, `datums.py`, `delivery.py`, `supervise.py` |
| GitHub catalog and local bootstrap | [Catalog and onboarding](operations/catalog-and-onboarding.md) | `github_catalog.py`, `remote_start.py` |
| Source contribution, projected artifacts, release | [Contributor workflows](contributors/workflows.md) | `pyproject.toml`, `.github/workflows/` |

## Task routing

| Intent | Read first | Owner / symbols | Focused tests | Minimal validation |
|---|---|---|---|---|
| Add a command or option | [CLI](cli/commands.md) | `horus/cli.py:build_parser`, `cmd_*` | `tests/test_cli.py` | `pytest -q tests/test_cli.py` |
| Change PRD/card/close policy | [Continuity](architecture/continuity.md), [Cards](backlog/cards.md) | `closure.py`, `backlog.py` | `test_closure.py`, `test_backlog.py` | focused two suites |
| Change agent account/login/argv | [Accounts and launch](sessions/accounts-and-launch.md) | adapters, `prepare_interactive` | adapter and `test_launch.py` | `pytest -q tests/test_launch.py tests/test_codex_adapter.py` |
| Change attach/restore/host behavior | [Hosts and registry](sessions/hosts-and-registry.md) | `Registry`, `terminal_sessions` | registry/session-host tests | `pytest -q tests/test_registry.py tests/test_terminal_sessions.py` |
| Change web/dashboard launch/terminal | [Dashboard](surfaces/dashboard.md) | `load_project`, `process_launch`, PTY routes | dashboard/access tests | `pytest -q tests/test_dashboard.py` |
| Change cockpit interaction/context | [TUI](surfaces/tui.md) | `HorusTUI`, `_launch_prompt` | `test_terminal_tui.py` | `pytest -q tests/test_terminal_tui.py` |
| Change worker scheduling/authorization/acceptance | [Dispatch and delivery](operations/dispatch-and-delivery.md) | envelope, executor, supervisor | envelope/schedule/supervise tests | targeted suites, then `pytest -q` |
| Change GitHub discovery/start/onboard | [Catalog and onboarding](operations/catalog-and-onboarding.md) | catalog, `start_github_project` | catalog/remote-start tests | `pytest -q tests/test_github_catalog.py tests/test_remote_start.py` |
| Change skills, hooks, package, CI, release | [Contributor workflows](contributors/workflows.md) | skills/hooks/`pyproject.toml`/workflows | skills/upgrade tests | focused tests; inspect workflow |

## Key concepts

- **Canonical continuity:** v3 `.horus/PRD.md` plus card files; Git/PR history is delivery evidence. The dashboard and TUI consume this material; they do not replace it.
- **Not canonical:** `.horus/archive/` is historical; `.horus/sessions/` is optional ignored local recovery material; `.horus/temp/` is fleeting worker evidence.
- **Isolation:** accounts, session PIDs, terminal targets, envelopes, and catalog cache live under machine-local `~/.horus/`; selected agent state is injected per spawned process.
- **Execution truth:** worker lifecycle evidence moves through registry, JSONL run logs, datums, delivery records, and independent supervision. A dead PID is not evidence of a delivery.
- **Remote vocabulary:** GitHub support discovers and bootstraps repositories locally. It is not remote agent execution.

## Validation baseline

```sh
pytest -q
```

Use the narrower commands in the task-routing table while iterating. The repository’s test workflow targets Python 3.12 and 3.13; package metadata declares Python `>=3.12`.

## Backlog

No documentation areas are deferred. Historical `.horus/archive/` and optional `.horus/sessions/` are deliberately described only as non-canonical supporting material, per their source-backed scope.
