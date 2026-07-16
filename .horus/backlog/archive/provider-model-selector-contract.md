---
status: shipped
priority: high
tier: sonnet
created: 2026-07-16
type: bug
parallel: safe
surface: horus/adapters/claude.py, horus/cli.py, horus/datums.py, bundled decision/execution skills
shipped_pr: 266
shipped_sha: ffbb9688c648e10feeeaaa3010fe8c1ca5cb3eb6
---

# Provider-valid model selector contract

Horus calibration keys describe the model that ran (`sonnet-5`), but they are not
necessarily valid provider CLI selectors. A real approved dispatch passed the
calibration key directly to Claude Code; Claude rejected it before work because the
executable full selector was `claude-sonnet-5`. The consent envelope looked exact but
did not describe an executable launch.

## Acceptance

- Recommendations and execution plans distinguish the canonical calibration key from
  the exact provider selector that will be passed to the worker CLI.
- Before creating a worktree or managed session, `horus run` rejects a known
  calibration-only Claude label with an actionable provider-selector correction;
  provider aliases and full selectors otherwise pass through unchanged.
- The correction is advisory and deterministic: Horus still never selects a model,
  silently substitutes a different selector, falls back, or launches without owner
  approval of the executable selector.
- Datum capture continues to store the canonical resolved model so existing
  calibration history remains one series.
- Bundled dispatch/execution guidance requires a provider-valid selector in the exact
  consent envelope and renewed approval if that selector changes.
- Tests pin preflight-before-side-effects, accepted aliases/full selectors, datum
  canonicalization, and Claude/Codex instruction parity.

## Evidence

- 2026-07-16 — Session `5e704890-b6de-4d32-ab19-3818a578e0ee` launched with
  `--model sonnet-5`, failed in five seconds with no delivery and unchanged observed
  usage. Claude Code 2.1.211 documents aliases such as `sonnet` and full selectors
  such as `claude-sonnet-5`.

## Boundaries

- Do not query a provider or spend model tokens merely to discover a selector.
- Do not turn calibration into routing or automatic model selection.
- Keep provider-specific validation in the adapter boundary; shared orchestration
  should not learn Claude naming conventions.
