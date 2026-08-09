---
type: operations reference
title: Machine Configuration, Accounts, Usage, and Hooks
description: Machine-local configuration ownership, agent account isolation, usage telemetry, projected hooks, and proxy boundaries.
tags: [configuration, accounts, usage]
---

# Machine Configuration, Accounts, Usage, and Hooks

Horus separates repository continuity from sensitive machine-local operations. `config.config_dir()` owns `~/.horus`; none of the following should become project truth.

| Location | Purpose |
|---|---|
| `~/.horus/config.toml` | projects, workspace, owners, workflow, launch/TUI/terminal settings |
| `~/.horus/accounts.toml` | aliases and Claude/Codex isolation mappings |
| `~/.horus/accounts/<agent>-<alias>/` | isolated native agent homes/configs |
| `~/.horus/registry.json`, `logs/`, `datums.json` | sessions, logs, observed runs |
| `~/.horus/cache/usage-*.json` | short-lived usage snapshots |
| `~/.horus/envelopes/` | unattended authorization state |

## Configuration and accounts

`_write_config()` round-trips unmanaged tables while updating known settings; this deliberately preserves security-relevant `[access]` data. Project registration is resolved-path and idempotent; prune removes paths missing `.horus/`.

Aliases are privacy-preserving labels. `isolate_account()` maps each agent independently to a copied login-defining state directory and never alters/deletes the ambient login. Unknown explicit aliases fail rather than silently falling back to ambient credentials. Sharing a config directory is a warning because it risks account-state corruption.

## Usage telemetry and preflight

`usage_snapshot` is best effort: it must never raise or block merely because credentials, network, provider schema, or local rollout data are unavailable. It caches positive and negative readings for 60 seconds. Claude reads OAuth/statusline signals; Codex derives windows from rollout JSONL metadata.

Interactive preflight warns/notices based on capacity and refuses only fresh high-utilization signals unless forced. Unattended envelopes impose the stricter unknown-capacity refusal. This difference exists because an owner can interpret uncertainty interactively.

## Projected hooks

`native_hooks` writes/merges Claude and Codex hook files while retaining foreign handlers. Marker-based ownership (`_handler_has_marker`) means only generated Horus handlers are replaced; repeated installation is idempotent. Codex stop/turn-boundary handlers are replaced in position, while `_merge_codex_pretooluse_hook` removes stale matcher placement and rehomes the generated handler without moving user handlers. This lets usage, merge, guard, checkpoint, and fetch-check generated hooks coexist rather than competing for one slot.

Guard syntax is platform-specific: Codex uses `_guard_posix` for POSIX/Git Bash and `_guard_windows` for PowerShell; Claude uses its guarded command form. In every case, missing or import-failing `horus` exits zero/no-op so a committed consumer hook never breaks a collaborator without the CLI. Hooks advise or inject context but do not override agent authority.

`proxy` is a distinct opt-in provider-routing integration; it does not redefine account identity semantics.

**Focused tests:** `tests/test_config.py`, `tests/test_account_isolation.py`, `tests/test_account_resolution.py`, `tests/test_usage_snapshot.py`, `tests/test_usage_preflight.py`, `tests/test_native_hooks.py`. The native-hook suite proves selective foreign-hook preservation, repeatable installation, coexistence of usage/merge/guard handlers, stale Claude matcher rehoming, Windows-safe guarding, and missing-CLI no-op behavior.

See [project projections](../continuity/project-lifecycle.md), [dashboard security](../operator-surfaces/dashboard.md), and [unattended dispatch](../automation/unattended-dispatch.md).
