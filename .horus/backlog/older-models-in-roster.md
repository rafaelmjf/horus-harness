---
status: open
priority: low
tier: haiku
created: 2026-07-12
created_by: overseer
parallel: true
surface: capabilities.toml (owner priors), dispatch methodology
shipped:
---

# Keep older-but-capable models in the calibration roster

**Owner methodology point (2026-07-12):** models that were frontier a few months ago
(gpt-5.5/5.4, sonnet-4.6, etc.) are likely still strong — and cheaper — for much of
the current scoped/mechanical work. Just as today's frontier will be "old" in a few
months, age alone is not a reason to dismiss. Judge by capability-for-the-task, not
recency; gather datums.

## Scope (mostly owner-prior data, not code)

- Add owner-priors to `~/.horus/capabilities.toml` for the older models the owner
  wants in rotation, tiered honestly (e.g. `tier = "prior-frontier / value"` with a
  `strength`/`caution` note). `capabilities.toml` is hand-edited and explicitly
  invites this — no code change to seed priors.
  - Needs owner to confirm the exact **model keys/aliases** that are actually
    reachable through the Claude/Codex adapters (`horus run --model <alias>`), so the
    prior keys match the datum keys the adapters emit.
- Then dispatch a few well-matched scoped tasks to each and `horus datum close` them —
  re-tag from prior to measured as datums accrue (~3–5 clean).

## Relationship

The *principle* (older models stay in the roster) is encoded in the
`delegation-rubric` template by the `delegation-matrix-display` card. This card is the
*data*: the actual priors + the datum-gathering. Also mirrored into the cockpit
dispatch discipline (horus-agent CLAUDE.md/AGENTS.md).

## Verification

`capabilities.toml` parses; `capabilities --models` renders the added models with
their priors; a dispatch to one produces a datum keyed to the same model name.
