---
status: open
priority: medium
readiness: ready
readiness_reason: "Both remaining rungs of `claude-usage-account-attribution` ride on the primitive that shipped with it (`claude_usage.session_identity()`), so there is nothing left to shape. The desktop record's schema, its org tagging and its lag were all measured on disk during that fix; the `overseer==worker` call site is one function. Scope is two named surfaces, not an investigation."
autonomy: attended
created: 2026-08-14
created_by: claude
last_refined: 2026-08-14
refine_passes: 1
topic: accounts-isolation
tier: small
type: feature
parallel: safe
surface: "horus/claude_usage.py (a desktop-record reader beside session_identity); horus/cli.py::_overseer_collision"
---

# usage-attribution-fallbacks — close the two rungs `claude-usage-account-attribution` left

## Why

`claude-usage-account-attribution` (#516) made a Claude usage reading refuse rather than
misattribute, and routes the hook and default check to the session's *own* registered
account. Two rungs from that card were deliberately left, and both are now cheap because
`claude_usage.session_identity()` exists and is measured, not inferred.

## Rung 2 — read the desktop app's own usage record

Today a session whose account is **not registered** as an isolated account gets a refusal.
`%APPDATA%\Claude\plan-usage-history.json` would answer it correctly: it is local, needs no
token and no network, and is **org-tagged**, so it is per-account correct by construction.
Schema (measured 2026-08-13/14): `{version: 2, samples: [{t, org, u:{fh, sd}}]}`, sampled
roughly every five minutes.

**It must be read as a lagging signal, never as current truth.** Measured during #516: its
last `ceeaba38` sample read `sd 85` at 09:50 while that account's weekly window had already
reset to `0` at ~10:00 — a 85-point error from a ten-minute lag. Cross-check `fh`/`sd`
against the window's own reset time and treat a sample older than its reset as expired
(`UsageSnapshot.without_expired_windows` already encodes that idea).

## Rung 4 — stop asserting `overseer==worker` from ambient config

`cli._overseer_collision` still compares the requested account against
`claude_usage.current_account()` — the *ambient login*. Under the desktop app that is not
the account the session runs under, so the advisory
`overseer==worker: '<alias>' is the account this session runs under` can state the wrong
thing as measurement, and a dispatch routed on it goes to the wrong account. Derive it from
`session_identity()`, or downgrade the claim to "cannot determine" when the session's
account is unknown.

## Acceptance

- When the session's account is not registered as an isolated account and the desktop
  record covers it, `horus usage check --target claude` should report that account's figure
  with its age, rather than refusing.
- When the newest sample for the session's org predates its own window reset, the tool
  should treat that window as having no reading rather than reporting the pre-reset percent.
- When the session runs under an account other than the requested alias,
  `--account <alias>` should not print the `overseer==worker` advisory.

## Note on scope

Attribution correctness already shipped; this is about **restoring a signal** where the fix
currently goes quiet, plus one advisory that still infers identity from ambient config.
Neither rung may reintroduce a confidently wrong number: a lagging reading must carry its
lag, and an undeterminable one must stay refused.
