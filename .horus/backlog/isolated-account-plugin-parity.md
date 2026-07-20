---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Whether this is Horus's job at all is undecided — the cheap cause (marketplace re-clone uses SSH) may make it a Claude-surface problem needing no Horus code. Probe that before scoping."
phase: explore
type: spike
vision_facet: "Accounts & isolation"
---

# isolated-account-plugin-parity — an isolated account starts with no plugins

## Why

Horus provisions `~/.horus/accounts/<agent>-<alias>` from the current login, but
copies only credentials (and the statusline pointer). Everything else in the
ambient config dir stays behind — most visibly **plugins**, but also the model
default. So an account launched through Horus gets a *barer* Claude than the same
person gets by typing `claude`, with no indication anything is missing.

Found while setting up the owner's Windows machine (2026-07-20): the four
Power BI plugins the owner relies on were simply absent under both isolated
accounts.

## Intended outcome

A decision on whether Horus owns plugin parity for the dirs it provisions — and
if it does, the isolation story stated honestly: which parts of a config dir are
*meant* to be per-account (credentials, usage, sessions) versus merely
*accidentally* per-account (plugins, model default, marketplaces).

## Broad boundaries

Probe the cheap cause first, because it may close the card with no code:

- `claude plugin marketplace add <repo>` failed inside an isolated dir with a git
  SSH auth error — it re-clones the marketplace rather than reusing the ambient
  copy. **Does the HTTPS form work?** If yes, parity is one documented command
  per account and Horus writes nothing.
- If it does not: the manual fallback used today was copying
  `plugins/marketplaces/<mp>` + `plugins/cache/<mp>` and hand-writing
  `known_marketplaces.json` + `installed_plugins.json` with paths rewritten to
  the isolated dir. It works (verified: `claude plugin list` shows all four
  enabled under both accounts) but it is undocumented private structure that can
  change under us — a poor thing for Horus to generate.

**Trap worth keeping regardless of the verdict:** PowerShell 5.1's
`Out-File -Encoding utf8` writes a BOM, and the plugin records parse as *empty*
with no error when one is present. Cost a debugging cycle. Any Windows JSON
writing needs `UTF8Encoding($false)`.

Non-goals: not syncing plugins between machines; not Codex (the owner uses
plugins only with Claude today).

## Open decisions for backlog-refine

- Is plugin parity Horus's responsibility, or explicitly the user's after
  provisioning?
- If Horus's: copy at provision time, or a separate `horus account --sync-plugins`
  the user runs deliberately?
- Does the same gap apply to anything else worth carrying (MCP servers, settings)?

## Source

In-session, 2026-07-20, Windows machine setup run (owner-attended). Fix applied
by hand on that machine for `claude-personal` and `claude-work`; this card exists
because the *mechanism* is unresolved, not the immediate need.
