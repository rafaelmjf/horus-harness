---
status: shipped
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
shipped_pr: 429
shipped_sha: 52ecc0b
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
- **One reading is labelled with one window, everywhere.** `usage all`, the datum
  capture, `usage check`, the TUI and the dashboard must not disagree about which window
  a given percentage belongs to (see the 2026-07-26 review: the same 82% was rendered as
  `weekly` by `usage all` and as `5h` by the worker datum).
- **Never invent a window duration.** Preserve the provider's reported primary/secondary
  percentages and reset timestamps; label a window `5h` or `weekly` only when the
  provider contract or the reset horizon supports it, otherwise render a neutral
  `primary`/`secondary`. (Folded from the retired `codex-usage-window-semantics`.)
- Tests cover primary-only, dual-window, and changed/reset-horizon payloads.
- **Staleness guard:** a reading older than a documented horizon (or when the account
  is idle / no fresh rollout) is not treated as an authoritative *refusal*. Degrade to
  a warning and/or surface "stale as of <ts>"; never hard-gate a launch on a stale read.
- Regression tests: idle-Codex stale snapshot, primary-only vs dual-window payloads,
  and used-vs-remaining orientation.

## Boundaries / relation

- **Absorbed [[codex-usage-window-semantics]] on 2026-07-26 (owner decision).** That card
  owned window *labeling* (5h vs weekly vs a neutral primary/secondary) and was deferred
  pending upstream stability. An earlier draft of this card argued the two should stay
  split — display correctness vs gate correctness — and the owner overruled that: one card
  now owns every wrong-usage-reading defect in this subsystem, because in practice the
  same readings feed both the display and the gate, and splitting them meant neither card
  owned the whole picture. That card is retired; its acceptance criteria are folded in
  below. The tradeoff accepted: this card is now broader than pure routing correctness,
  so its scope must be re-checked before it is called Ready.
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
- 2026-07-26 — **Reproduced in horus-harness itself, and the staleness leg is now
  measured end-to-end.** The owner stated codex-personal had reset to 100%
  available; `horus usage all` reported **weekly 82% (resets 2026-07-29 09:11)** and
  both `horus run` launches printed *"weekly usage is 82% … launching into a closing
  window."* The reading's source was a rollout file dated **2026-07-25 09:48**, ~27
  hours old — Codex had not run since. Then the dispatched worker's own recorded
  readings closed the loop: `start=5h=82%[fresh] → end=5h=1%[fresh]`. The 82% was the
  stale artifact; one real session collapsed it to ~1%, confirming the owner's figure
  and that nothing but a Codex turn can refresh it.

  Also observed: the two readers disagreed **again**, differently. `usage all` showed
  a confident `82%` while `usage check` on the same account said *"weekly limit
  snapshot stale (reset 2026-07-25 08:55)"* — a **different reset timestamp** for the
  same window. So the divergence is not only used-vs-remaining orientation: the two
  paths select different rollouts. `without_expired_windows` only blanks a percent
  whose *recorded* reset has passed, which is why the older reading self-reported
  stale and the newer one did not.

  Process note worth keeping: this card was invisible to the session that hit the
  defect, because the branch carrying it had never merged. The defect was
  re-diagnosed from scratch and a duplicate card was nearly minted. Land cards
  promptly, and check unmerged remote branches before filing.

- 2026-07-26 (second entry) — **Absorbed `codex-usage-window-semantics` by owner decision.**
  New evidence that made the split untenable: for the same account at the same moment,
  `horus usage all` rendered `5h — · weekly 82%` while the worker datum for session
  `5d8ce1ad` recorded `start=5h=82%`. The same number, two different window labels. It
  repeated with the later value (`usage all` weekly 2% vs datum `5h=2%`).

  `_read_codex` carries a comment about routing each lane "by the length Codex declared
  for it, not by its slot", added 2026-07-17 to fix precisely this, so either the datum
  path regressed that fix or `usage all` mislabels. **Which one is wrong is unverified** —
  the datum write path was not read. Establishing that is the first concrete step.

  Retiring the other card loses a deliberate boundary (display correctness vs gate
  correctness) that its own text defended; the owner judged that one owner for all
  wrong-reading defects is worth more, since the same readings feed both surfaces.

- 2026-07-26 (third entry) — **Five of six acceptance items now met; one remains.**

  Met: (a) preflight and `usage check` report the same percentage and orientation from
  one shared source — the two readers were never picking different *rollouts*, they were
  reading different **homes** (`closure.py:570`, `cli.py:3415`, `dashboard.py:237` all
  fall back to the ambient `~/.codex`, which under account isolation no real session ever
  writes to, so they were permanently stale by construction; PR #419 makes a homeless
  read scan every known home). (b) One reading, one window label everywhere — the datum
  path classified lanes positionally and recorded weekly percentages as `pct_5h`
  (PR #417). (c) Never invent a window duration — `windows()` classifies by declared
  length with a neutral fallback. (d) Tests cover primary-only, dual-window and
  changed-horizon payloads (#417). (e) Orientation regression tests (#418), which also
  established from ground truth that Codex reports `used_percent`, i.e. USED like Claude.

  **NOT met — the staleness guard.** There is still no age/horizon check on the preflight
  refusal. `without_expired_windows` only blanks a percent whose recorded reset has
  already *passed*, which does not catch the case that started all of this: a reading 27
  hours old whose reset is still in the future. An idle account therefore continues to
  produce a confident stale figure that can hard-gate a launch.

  Well-defined remaining leg, and it needs no invented horizon: each lane declares
  `window_minutes` and `resets_at`, so the current window's start is
  `resets_at - window_minutes*60`. A reading whose own timestamp predates that start
  describes a **previous** window — it must degrade the refusal to a warning and surface
  "stale as of <ts>" rather than gate on it.

### 2026-07-27 — Rafael Figueiredo (agent)
Verdict: staleness guard implemented; the handoff's proposed formula was wrong

2026-07-27 — the last acceptance item (the staleness guard) is implemented, but NOT by the formula the previous session's handoff proposed. That handoff said: 'a reading predating `resets_at - window_minutes*60` describes a previous window and must degrade the preflight refusal to a warning.' That test cannot fire. A provider reading is always captured INSIDE the window its own `resets_at` closes, so `captured_at < resets_at - window` is never true for a self-consistent reading — it is equivalent to the `without_expired_windows` check that already exists. Checked against this card's own reproduced case: capture 2026-07-25 09:48, resets_at 2026-07-29 20:53, weekly window 10080min → window span [07-22 20:53, 07-29 20:53]. The capture sits inside it, so the formula scores that reading FRESH — the very reading the card documents as 27h stale and wrongly refusing. Implemented instead what the card's own acceptance bullet asks for ('a reading older than a documented horizon ... is not treated as an authoritative refusal'): an AGE horizon. `UsageSnapshot` now carries `captured_at` — the provider's capture time, not Horus's cache time, which is the distinction that matters because an idle Codex account yields an hours-old rollout through a seconds-old cache entry. `_read_codex` populates it from the rollout event's own timestamp (it was being discarded). A reading older than `REFUSAL_MAX_READING_AGE` (2h) can still WARN but can no longer REFUSE. Horizon rationale: the cost is asymmetric — a false refusal blocks valid dispatch and teaches `--force`, which disables the gate wholesale, whereas a false green-light only lets a run die in a window it would have died in anyway, which the run itself reports. Readings with no capture time (Claude's pushed statusline) keep refusing unchanged; weakening those was not in scope. Probed live against real rollout files: the 99%-stale case now warns and proceeds, the same 99% captured now still refuses.
