# Work: `deploy-hosted.sh` can silently succeed on the wrong version

## Status

Not a reproduced bug — a **hardening gap** identified 2026-07-10 while reviewing the
release→deploy path after v0.0.33. The prior symptom it belongs to (0.0.31 shipped for
the 0.0.32 release) is already partially fixed; this file captures the remaining hole
plus the verification and cross-repo checks that make the pipeline genuinely reliable.
Self-contained and delegatable.

## Background — how hosted deploy works

Publishing a horus-harness release does **not** update the hosted dashboard at
`horus.rafaelfigueiredo.com` on its own. The pipeline is:

```
GitHub `release` event
  -> cloudflared `deploy-hook.rafaelfigueiredo.com`
  -> loopback HMAC receiver (lives in `horus-hub ops/deploy-hook/`,
     `horus-deploy-hook.service`; only ever runs one fixed script)
  -> scripts/deploy-hosted.sh   (this repo)
       - uv tool install --force --refresh the pinned version
       - sudo systemctl restart horus-dashboard.service
       - verify /health is 200 and / is 403 (gated)
```

The systemd unit runs the pinned uv-tool install (`~/.local/bin/horus … --exposed`), so
restarting it picks up the upgrade. Wiring lives in `horus-hub ops/deploy-hook/README.md`.

## What already went wrong (context, already fixed)

The webhook fires the instant a release publishes, but PyPI's **simple index** (what
`uv` resolves against) lags its JSON API by 1-2 minutes. A plain
`uv tool install --refresh` therefore resolved the *previous* version — it installed
**0.0.31 for the 0.0.32 release**.

Fixed in `deploy-hosted.sh`: it now reads the target version from PyPI's fresh JSON API,
pins `==<latest>`, and retries up to 8x/20s until the simple index catches up.

## The remaining gap (the actual work)

`deploy-hosted.sh` verifies the dashboard is **up** (`/health` 200) and **gated** (`/`
403) — but it never verifies the **running version matches the target**. So the deploy
can exit 0 having deployed the *wrong* (old) version:

- If the retry loop exhausts (index lags past ~160s, or the target version is genuinely
  absent from the index), the `uv tool install ==<latest>` never succeeds, `installed`
  stays empty, and the **previous install remains in place**.
- The script restarts the service anyway and both post-checks pass on the **stale build**
  (it's up, it's gated — just old).
- Result: a silent stale deploy. This is the exact failure class that already bit
  (0.0.31-for-0.0.32), now *silent* instead of loud.

This is a missing **runtime gate**: per this repo's instruction -> signal -> gate ladder
(see PRD Rules), the deploy currently *hopes* it worked; it should *observe* the version.

## The fix

`/health` already returns the running build's version, so the assertion needs no new
endpoint. From `horus/dashboard.py` (`/health` handler, ~line 3761):

```python
{"app": "horus-dashboard", "version": __version__, "pid": os.getpid()}
```

After the restart + existing `/health`/`403` checks, add a version assertion:

1. Fetch `/health` (already fetched into `$health`), parse `.version` (JSON — prefer
   `python3 -c` / `jq` over grep, matching the existing style of the script).
2. If `$latest` is known and the reported version `!= $latest`, print a loud error and
   `exit 1`. Do not let the script report success.
3. Also treat an **empty `installed`** (retry loop exhausted without a successful pinned
   install) as a hard failure with a clear message — today it falls through to the
   success path.

Keep the existing behavior when `$latest` could not be resolved (no target to assert
against): warn, but still assert `installed` was set, and log that the version could not
be confirmed rather than claiming success.

## Two accompanying checks (no code, or cross-repo)

### A. Verification owed — prove the retry fix under a real release

The retry-and-pin fix has **never run under a real webhook-triggered release**: v0.0.33
was deployed **manually**. So it is reasoned + coded but not *observed* under the race.
Per the repo's "reproduce the gate" discipline: on the **next release, let the webhook do
it** and watch hosted `/health` flip to the new version — do **not** pre-empt with a
manual `deploy-hosted.sh` run. The version assertion above makes that observation
automatic and fail-loud.

### B. Latent risk — confirm the receiver runs the *fixed* script (in `horus-hub`)

The fix lives in `horus-harness/scripts/deploy-hosted.sh`, but the receiver lives in
`horus-hub ops/deploy-hook/`. If the receiver invokes a **frozen copy** of the script
rather than an up-to-date checkout/symlink, the retry+assert fix is **inert** and the
race recurs on the next release. Confirm how the receiver resolves the script path
(fresh `git pull` of the harness checkout, or a symlink to it) and fix if it points at a
stale copy. This check happens in `horus-hub`, not here.

## Suggested implementation order

1. **P0 — version assertion + empty-`installed` guard in `deploy-hosted.sh`** (this
   repo, small, closes the silent-stale-deploy class). Ships on the next release.
2. **P1 — observe the webhook end-to-end on that next release** (check A; no code, just
   discipline — don't manually deploy).
3. **P1 — confirm the receiver runs the fixed script** (check B; in `horus-hub`).

## Acceptance criteria

- After a successful deploy, `/health` reports **exactly** the target version; a mismatch
  makes `deploy-hosted.sh` **exit non-zero** with a message naming installed-vs-target.
- Retry loop exhausted (pinned install never succeeded) => script fails loudly; it never
  restarts-and-claims-success on the old build.
- Unresolvable target version => script warns and still asserts an install happened;
  it never silently blesses an unknown state.
- Next real release is deployed **by the webhook** (not manually) and observed flipping
  hosted `/health` to the new version.
- Receiver in `horus-hub` is confirmed to invoke the current `deploy-hosted.sh`, not a
  frozen copy.

## Relevant code

- `scripts/deploy-hosted.sh` — pin/retry install, restart, and the verify block that
  needs the version assertion (this repo).
- `horus/dashboard.py` — `/health` handler returning `{"app","version","pid"}` (~3761);
  the version source of truth for the assertion.
- `horus-hub ops/deploy-hook/` (`README.md`, `horus-deploy-hook.service`) — the webhook
  receiver; target of check B (other repo).
- CLAUDE.md / AGENTS.md "Releasing horus-harness" — the instruction rung that says
  `deploy-hosted.sh` is the last release step; update if the assertion changes the flow.
