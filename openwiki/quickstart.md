---
type: wiki entrypoint
title: Horus Harness Code Wiki
description: Source-grounded navigation for the Horus continuity CLI, its project state, agent execution, operator surfaces, and safe change paths.
tags: [horus, navigation, architecture]
---

# Horus Harness Code Wiki

Horus is a Python CLI continuity layer for native coding-agent CLIs. It keeps durable project orientation in committed `.horus/` files, while machine-local state holds accounts, sessions, telemetry, schedules, and authorization. It wraps Claude/Codex rather than implementing a model loop.

## Map

- [CLI composition](architecture/cli.md): public command surface and handler routing.
- [Continuity model](continuity/model.md): PRD/frontmatter, resume, closure, legacy compatibility.
- [Backlog](continuity/backlog.md): card lifecycle, readiness, claims, portfolio tree.
- [Project lifecycle](continuity/project-lifecycle.md): init, instructions, skills/hooks, upgrade floor.
- [Agents and runs](execution/agents-and-runs.md): adapters, run executor, registry/log evidence.
- [Git delivery](delivery/git-integration.md): worktrees, delivery receipts, integration, gates.
- [Unattended dispatch](automation/unattended-dispatch.md): envelopes, schedules, supervision.
- [Planning and fleet intelligence](planning/fleet-intelligence.md): datums, priors, capability/fleet read models.
- [Terminal/TUI](operator-surfaces/terminal.md), [dashboard](operator-surfaces/dashboard.md), and [native entrypoints](operator-surfaces/native-entrypoints.md).
- [Remote projects](fleet/remote-projects.md): GitHub catalog, start, onboarding.
- [Configuration](operations/config-and-projections.md) and [release/deployment](operations/release-and-deployment.md).

## Task routing

| Intent | Start here | Owning sources | Focused validation |
|---|---|---|---|
| Add or alter a CLI command | [CLI](architecture/cli.md) | `horus/cli.py:build_parser`, `cmd_*` | `pytest -q tests/test_cli.py` |
| Change PRD/resume/close behavior | [Continuity](continuity/model.md) | `frontmatter.py`, `routines.py`, `closure.py` | `pytest -q tests/test_routines.py tests/test_closure.py` |
| Extend card behavior | [Backlog](continuity/backlog.md) | `backlog.py`, `backlog_tree.py` | `pytest -q tests/test_backlog.py tests/test_backlog_tree.py` |
| Change native agent launch or events | [Agents and runs](execution/agents-and-runs.md) | `adapters/`, `launch.py`, `run_executor.py` | `pytest -q tests/test_adapters.py tests/test_launch.py` |
| Change worker Git flow or merge policy | [Git delivery](delivery/git-integration.md) | `worktree.py`, `delivery.py`, `integration.py`, `supervise.py` | `pytest -q tests/test_worktree.py tests/test_delivery.py tests/test_supervise.py` |
| Change away-mode safety | [Unattended dispatch](automation/unattended-dispatch.md) | `envelope.py`, `schedule.py`, `supervise.py` | `pytest -q tests/test_envelope.py tests/test_schedule.py tests/test_supervise.py` |
| Change terminal session behavior | [Terminal/TUI](operator-surfaces/terminal.md) | `hosts/`, `terminal_sessions.py`, `terminal_tui.py` | `pytest -q tests/test_terminal_sessions.py tests/test_terminal_tui.py` |
| Change dashboard route or access policy | [Dashboard](operator-surfaces/dashboard.md) | `dashboard.py`, `pty_host.py` | `pytest -q tests/test_dashboard.py tests/test_dashboard_access.py` |
| Change account/config/usage/hooks | [Configuration](operations/config-and-projections.md) | `config.py`, `usage_snapshot.py`, `native_hooks.py` | `pytest -q tests/test_config.py tests/test_usage_snapshot.py tests/test_native_hooks.py` |
| Change package/release/hosted operation | [Release/deployment](operations/release-and-deployment.md) | `pyproject.toml`, `scripts/deploy-hosted.sh` | `pytest -q tests/test_deploy_hosted.py tests/test_versioning.py` |

## Core boundaries

1. **Repo-local versus machine-local:** `.horus/PRD.md` and cards are committed continuity; `~/.horus/` sessions/accounts/envelopes are machine-local.
2. **Evidence versus acceptance:** worker delivery evidence does not grant merge or completion authority; independent supervision does.
3. **Orientation versus permission:** resume prose explains context; native agent posture governs permitted actions.
4. **Planning versus routing:** datums/capability/fleet views advise an owner and never auto-dispatch.

## Backlog

No documentation area was deferred. The repository’s existing product backlog is separate from this code wiki and remains authoritative for product work.
