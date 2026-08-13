---
status: open
priority: low
readiness: ready
autonomy: eligible
created: 2026-08-13
created_by: agent
last_refined: 2026-08-13
refine_passes: 1
topic: curator-portfolio
tier: low
type: bug
parallel: safe
surface: "horus/curate.py — discover() account labels (account_dir.name is `claude-<alias>`, and aliases already contain the agent, so isolated accounts render as `claude-claude-personal`)"
---

# curator-account-label-doubling [bug] — isolated account names double the agent prefix

## Why

In the portfolio view the accounts read `claude-claude-personal` / `claude-claude-work`:
`discover()` labels a session by its account directory name, which is
`f"{tool}-{alias}"`, but the alias itself already starts with the agent
(`claude-personal`). Cosmetic in the view, but the account string is also the
filter key and the color-grouping key, so the doubled label is what the owner
sees and clicks. The 2026-08-12 PoC had an `account_label()` helper that cleaned this.

## How

Add a small `account_label(raw)` that collapses a duplicated leading agent prefix
(`claude-claude-personal` → `claude-personal`, `codex-ambient` → `codex-ambient`).
Apply it where the label is presented (payload/manifest display), keeping the raw
account dir name as the internal key so routing/isolation is unaffected.

## Acceptance

- When an isolated account dir is named `claude-claude-personal`, the portfolio view
  and `horus curate` output should label it `claude-personal`, while the underlying
  session→account mapping is unchanged.
- Gate: a unit test on `account_label` covering the doubled and non-doubled cases.

## Non-goals

- No change to account isolation, routing, or the on-disk dir naming.

## Source

Observed 2026-08-13 while rendering the regenerated sumi-e view (#511).
