---
state: open
priority: high
created: 2026-08-09
---

# account-isolation — make isolation real, not nominal

## The problem

Every account is meant to run isolated so that cross-account corruption is impossible. On disk it is not. Isolating a Codex account **copies its `config.toml`**, and that file carries absolute paths back to the shared home — so an "isolated" session hands its MCP server the shared directory and resolves marketplaces out of the shared temp dir. A **trust decision** was propagated by the same copy, which is not something an isolation mechanism should do silently.

A copy is also a frozen mirror: it drifts from the moment it is made, and nothing reports the drift.

Separately, there is no way to log into an account that has **no prior login** — isolation only works outward from an existing ambient session. An account can therefore be mapped and permanently unusable, which is what happened to `claude-work` after the Windows migration: every launch failed with a message that named no remedy.

Usage readings have their own blind spot — a reading on one machine cannot see another.

## What we are building

**Login becomes the isolation primitive, and file-copying retires entirely.** One provisioning function creates the directory, maps the alias, writes the statusline pointer, and drives the agent's own fresh login.

A directory generated in place cannot leak foreign paths and cannot be a stale mirror. That is why this single change fixes the path leak, the propagated trust decision and the drift together, rather than patching three symptoms separately.

Every surface reaches it through that one function — the CLI verb, the dashboard wizard, and an affordance in the cockpit for any account with no credentials. A launch against an unlogged account names the exact command to run instead of reporting a mismatch.

The cross-machine usage question is deliberately still open: the limitation is measured and honestly reported, but the remedy is undecided.
