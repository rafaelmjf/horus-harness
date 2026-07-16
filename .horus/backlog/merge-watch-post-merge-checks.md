---
status: claimed
priority: medium
tier: sonnet
created: 2026-07-16
type: bug
parallel: safe
surface: horus/mergewatch.py, horus/cli.py, tests/test_mergewatch.py, tests/test_cli.py
---

# Merge-watch settles applicable checks on a post-merge SHA

Watching squash-merge commit `28a96c2` associated it with the already-merged PR and
loaded the base branch's required PR contexts. Both Python push checks reached green,
but the PR-only `freshness` job could never appear on the main push, so
`horus merge-watch` remained pending until the supervisor interrupted it.

## Acceptance

- A literal commit SHA remains a commit target even when GitHub links it to a merged
  PR; the command does not treat the PR's different head SHA as the watched target.
- Required contexts that cannot apply to the watched commit event do not keep a
  post-merge push pending forever, while delayed applicable checks still cannot yield
  an early green.
- The command settles success/failure on the exact literal SHA and retains clear
  warnings when a genuinely watched open PR moves.
- Tests reproduce a squash-merge SHA linked to a merged PR, PR-only freshness plus
  push-only test checks, delayed check registration, and a failing applicable check.
- A live probe against a known merged main SHA exits successfully after its exact push
  checks are green.

## Boundaries

- Never retarget a caller-supplied SHA.
- Do not weaken PR-head required-check behavior or infer success from PR prose/state.
- Keep polling read-only and bounded by the existing timeout.
