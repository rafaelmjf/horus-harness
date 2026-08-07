---
type: CLI reference
title: Horus CLI Command Architecture
description: Entrypoints, argparse dispatch, command families, mutation guards, and validation conventions.
tags: [cli, commands, operations]
---

# Horus CLI Command Architecture

The installed script is `horus = "horus.cli:main"`; `python -m horus` imports the same `main()`. `build_parser()` in `horus/cli.py` registers required top-level argparse subcommands using `set_defaults(func=...)`; `main(argv)` parses then invokes `args.func(args)`. Thus parser registration, handler, domain module, and focused test are the complete change surface for public commands.

## Command-family map

| Family | Representative commands | Primary ownership |
|---|---|---|
| Project continuity | `init`, `doctor`, `resume`, `close`, `checkpoint`, `consolidate`, `infer`, `reconcile`, `upgrade-project` | `initialize`, `continuity`, `closure`, `routines`, `upgrade` |
| Cards and delivery | `backlog list|claim|ship|review|refine|migrate`, `merge-watch`, `datum` | `backlog*`, `delivery`, `datums` |
| Agent/session control | `run`, `open`, `sessions`, `attach`, `stop`, `reap`, `tail`, `account` | adapters, `launch`, `terminal_sessions`, registry |
| User interfaces | `dashboard`, `app`, `tui`, `status`, `fleet`, `capabilities` | dashboard, companion, terminal UI |
| Dispatch/oversight | `schedule`, `envelope`, `supervise`, `usage`, `notify`, `warmup` | schedule, envelope, supervise, usage/notify modules |
| Catalog and local setup | `discover`, `refresh`, `start`, `onboard`, `config`, `forget`, `prune` | GitHub catalog, remote start, config/registry |
| Integrations/projections | `hook`, `skill`, `proxy`, `vscode-*`, `statusline`, `overhead` | native hooks, skills, proxy, VS Code, overhead |

Nested families are intentionally strict; invalid choices are argparse errors (typically exit 2). Bare `horus backlog` is explicitly defaulted to `backlog list`.

## Shared safety behavior

- `_enforce_version_floor()` refuses a state mutation below a project’s `horus_min_version`, returning 4 unless `HORUS_IGNORE_VERSION_FLOOR=1` is set.
- Project commands generally accept `--path`; handlers resolve that root before delegation.
- `cmd_run` validates agent/model/account and authorization **before** worktree/session side effects. The delivery posture guard refuses Codex delivery/worktree work unless posture is `full-auto`.
- `close --check` emits a gate verdict; normal close reports the ritual and optionally makes a bounded continuity commit/push.
- Hook modes are machine-facing exceptions: for example closure/hook paths can read JSON from stdin. Keep those schemas and no-op/failure behavior covered by focused tests.

## Public command change recipe

1. Add parser arguments/subparser registration in `build_parser()` and set the correct handler.
2. Keep argument validation at argparse level when choices are static; put state-dependent policy in the owning module.
3. Invoke the domain operation from a `cmd_*` handler, preserving explicit return codes and human/JSON output conventions.
4. Add an in-process `main([...])` test in `tests/test_cli.py`; add/adjust the owning module’s focused test.
5. If a command mutates durable state, verify version floor, account/authorization, and ordering relative to side effects.

```sh
pytest -q tests/test_cli.py
# then the owning focused suite, for example:
pytest -q tests/test_closure.py tests/test_backlog.py
```

For operational composition rather than argument syntax, use [continuity](../architecture/continuity.md), [sessions](../sessions/accounts-and-launch.md), and [dispatch and delivery](../operations/dispatch-and-delivery.md).
