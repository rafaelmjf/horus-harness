---
status: open
priority: medium
readiness: shaping
readiness_reason: "Needs investigation of two disagreeing readers over the same snapshot + a staleness horizon before a gate change; not yet a clean ready leg."
created: 2026-07-23
created_by: owner
last_refined: 2026-07-23
vision_facet: "Delegation calibration"
tier: medium
type: bug
parallel: safe
surface: "horus/codex_usage.py (rollout snapshot), horus/usage_snapshot.py (shared preflight+check source), horus/cli.py:1168 (run preflight refusal) / :5067 (--force skip)"
---

# codex-usage-stale-snapshot gates dispatch — wrong, and two readers disagree

**Reported by owner, 2026-07-23 (agentic-travel-guide dispatch).** Dispatching a
`--worker codex --account personal` leg was **refused** by the `horus run` preflight
on a Codex usage reading that is flat wrong, and two Horus code paths reported two
*different* wrong numbers for the same account/window.

## Evidence (same account, same reset window)

- Ground truth (owner checked ChatGPT directly): **~100% remaining / ~0% used.**
  Codex had not been used for a while.
- `horus run` preflight (`cli.py:1168`): *"Refusing to run: codex account personal
  weekly usage is **99%** (resets 2026-07-25 08:55). The window is nearly exhausted —
  the session would likely die mid-run."* → had to pass `--force` to launch.
- `horus usage check`: *"Codex context 39.2% (138586/353400 tokens); weekly limit
  **21%** (resets 2026-07-25 08:55)."*

Same reset timestamp (2026-07-25 08:55) → both claim to read the same weekly window,
yet report **99% vs 21% used**, and **both** contradict the real ~0%.

## Why it matters

This is **dispatch-routing correctness**, not cosmetics: a best-effort telemetry
snapshot is used as an authoritative gate that *refuses a launch*. A stale/idle read
either blocks valid dispatch (false 99% → forced `--force`) or would wave through an
actually-exhausted account. It also undermines the `dispatch-decision` /
`execution-decision` skills, which tell the owner to gate account choice on
`horus usage check`.

## Suspected cause

`codex_usage.py` is documented as a **read-only best-effort inspector** of the last
Codex rollout's `token_count` rate-limit percentages under `$CODEX_HOME/sessions`.
When Codex is idle, the newest rollout snapshot is **old** — so the percentage is
whatever Codex reported at that past moment, presented as current with no staleness
signal. Separately, the preflight (99%) and `usage check` (21%) diverging over the
same window points at a second defect: the two paths pick a different rollout / a
different lane (primary vs secondary), or one orients **used vs remaining** opposite
to the other. Both hypotheses should be checked; the divergence proves at least one
reader is wrong beyond mere staleness.

## Acceptance

- Preflight and `horus usage check` report the **same** percentage and orientation
  (used vs remaining) for the same account/window from one shared source.
- **Staleness guard:** a reading older than a documented horizon (or when the account
  is idle / no fresh rollout) is not treated as an authoritative *refusal*. Degrade to
  a warning and/or surface "stale as of <ts>"; never hard-gate a launch on a stale read.
- Regression tests: idle-Codex stale snapshot, primary-only vs dual-window payloads,
  and used-vs-remaining orientation.

## Boundaries / relation

- Distinct from [[codex-usage-window-semantics]] — that card is window *labeling*
  (5h vs weekly), deferred, and explicitly scoped to "display/telemetry correctness,
  **not** dispatch routing or a spend policy." This card is exactly that excluded
  routing/gating correctness, so it should not be folded into it.
- Workaround today: `horus run --force` (`cli.py:5067`) skips the preflight refusal.

## Reviews

- 2026-07-23 — **Live evidence, agentic-travel-guide `tabi-triage-1` dispatch.**
  The codex-personal leg (`activity-image-cache`) was *refused* by the `horus run`
  preflight: *"codex account personal weekly usage is 99% (resets 2026-07-25 08:55)
  … the session would likely die mid-run."* Owner checked ChatGPT directly →
  **~100% remaining (~0% used)**; Codex had simply been idle for a while. Launched
  with `--force`: the worker **ran to completion (rc=0), opened PR #37, which was
  reviewed and merged (`4a6efa5`)** — a full build+test+PR dispatch on an account
  the gate declared all-but-dead. The refusal was flatly wrong. For the same window
  and reset timestamp, `horus usage check` independently reported **21% used** — a
  third, different number — confirming the two readers disagree, not just that the
  snapshot is old. Net: the gate produced a **false refusal that only `--force`
  bypassed**, and would equally have waved through a genuinely-exhausted account.
  This is the concrete routing-correctness failure the card predicted.
