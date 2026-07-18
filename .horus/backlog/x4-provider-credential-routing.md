---
status: open
priority: medium
created: 2026-07-18
tier: high
type: feature
parallel: unsafe
phase: explore
created_by: owner
branch: vision-branch-x4-model-harness-plane
surface: horus/proxy.py, horus/config.py, horus/cli.py, horus/adapters/base.py, local CLIProxyAPI OAuth metadata
---

# x4-provider-credential-routing — separate harness profile from the subscription that serves the model

## Why

A proxied session launched under `claude-work` still used the proxy's only Claude
credential, personal, for explicit Claude-family subagents. `CLAUDE_CONFIG_DIR`
selects Claude Code settings/history; `ANTHROPIC_BASE_URL` moves model authentication
to CLIProxyAPI. Presenting those as one “account” is misleading and can silently
spend the wrong subscription. Evidence: [[2026-07-18-claudex-first-session-findings]].

## Design

- Model a launch route with separate fields for:
  - harness profile (`claude-work`, `claude-personal`, ambient), and
  - provider credential (`codex-personal`, `claude-work`, etc.).
- Enumerate CLIProxyAPI OAuth files without printing tokens. Match Claude credentials
  by masked email/known alias and Codex credentials by account id to configured
  `CODEX_HOME` identities.
- Add guided `horus proxy login <provider> --account <alias>` binding. The actual
  login identity must match the requested account; mismatches stay unbound.
- Preserve every unknown/secret JSON field with an atomic metadata update. Assign a
  deterministic, CLIProxyAPI-supported per-auth `prefix` and human-readable note.
- Prefixed model routes select exactly one named credential. If it is unavailable,
  report the credential and available alternatives; require an owner choice before
  retrying.
- Store only safe route metadata in Horus state/registry/receipts. OAuth secrets stay
  in their provider-owned local files.

## Acceptance

- `horus proxy status` lists masked provider credentials, bound account aliases,
  prefix, readiness/cooldown when observable, and unlinked identities.
- A prefixed request reaches only its named credential with two same-provider
  credentials installed.
- Binding refuses an alias/identity mismatch and preserves token plus unknown fields
  byte-semantically.
- A `claude-work` harness profile can explicitly use `codex-personal` for GPT without
  claiming those are the same account.
- Exhaustion never round-robins or fails over to another named subscription silently.

## Non-goals

- No automatic usage/cost router.
- No shared failover pool: one OAuth record has one prefix, and hidden account
  switching conflicts with Horus's owner-authorization rule.
- No TUI layout (owned by [[x4-tui-execution-route-axis]]).
