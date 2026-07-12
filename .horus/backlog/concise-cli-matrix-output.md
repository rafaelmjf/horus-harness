---
status: open
priority: medium
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/cli.py (capabilities render)
shipped:
---

# Make the CLI capabilities/matrix output concise — glance-only

**Owner feedback (2026-07-12):** the aligned table (shipped #168) is readable but still
does too much for a CLI glance. Two concrete problems + a direction:

1. **Drop the `LAST` column from the default CLI table.** `LAST: clean clean nudged
   clean` is per-run *delegation-quality* outcomes (clean/nudged/bounced/died — the
   agent's judgment, not CI/exit status). It's insider context that confuses a quick
   read and needs a legend to interpret. Keep it in `--stdout` JSON and in the richer
   dashboard view (`model-roster-dashboard-tab`); remove it from the concise table (or
   gate behind `--verbose`).
2. **The `CAPABILITY` column truncates** (`…`) and never shows the full line. Don't cram
   a paragraph into a column: show a SHORT summary in the table (a few words), with the
   full capability/notes text available in `--stdout` JSON and the dashboard detail view.
   Consider a dedicated short `summary` field vs. the longer `capability_note`.

**Direction (owner):** keep the CLI output concise — the user checks the important info
at a glance (model · tier · price · datum count). The FULL research + per-model detail
lives in the dashboard tab (`model-roster-dashboard-tab`), not the terminal.

## Scope

- Concise default table: `model · tier · price · datums (clean/total)` + a short
  capability summary. Drop `LAST`. Keep `--stdout` JSON complete (nothing removed there).
- Optional `--verbose`/`--full` restores the fuller columns for power users.
- Keep the DISPLAY-ONLY boundary (no pick/route) and the staleness nudge intact.

## Verification

Default `capabilities --models`/`--matrix` renders the concise set (no LAST, short
capability); `--stdout` JSON still carries every field; `--verbose` restores detail.
CI green.
