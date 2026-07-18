"""Keep a Claude account's 5-hour usage window continuously warm.

``horus warmup`` (see ``horus.warmup``) opens the 5h window ONCE. This is the
standing counterpart: a per-account loop that re-warms the account just after each
window reset, so the window is always open when the owner sits down to work later —
the "Tokenmaxxing" toggle surfaced in the TUI Control pane.

**Cadence — fixed-5h primary, ``resets_at`` correction.** Claude's 5h window is
anchored to the FIRST turn on the account, and the warmup *is* that first turn, so
the window resets at ``warmed_at + 5h``; arming the next fire ~1 minute after is
deterministic and needs no reading — which matters because a headless ``claude -p``
warmup does not populate ``resets_at`` (that field is recorded by the statusline
render, which does not fire on ``-p``). When a fresher ``resets_at`` *was* recorded
(the owner did interactive work), we prefer it — it can only be more accurate than
the fixed anchor. A stale/past reading never shortens the cadence below a floor.

**Claude-only by construction:** it warms ``config.load_account_config_dirs()``
accounts (Claude ``CLAUDE_CONFIG_DIR`` map); Codex has no 5h window to keep warm.

Best-effort: a failed warmup is counted, never fatal — the loop retries on the next
cycle, still spaced by the window so a persistent failure never hammers the API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from horus import usage_snapshot, warmup

FIVE_HOURS = 5 * 60 * 60
# Fire ~1 minute AFTER the window resets, so the re-warm lands inside the fresh
# window rather than racing the reset boundary.
REFRESH_OFFSET = 60
# Never busy-loop: a stale/past recorded reset must not collapse the cadence.
MIN_DELAY = 60.0


def next_delay(
    account: str, *, warmed_at: float, now_fn: Callable[[], float] = time.time
) -> float:
    """Seconds to sleep before the next warmup of ``account``.

    Primary: ``warmed_at + 5h + offset`` (the window is anchored to this warmup).
    Correction: a recorded FUTURE ``resets_at`` for the account overrides it, since
    an observed reset is more accurate than the fixed anchor. Floored at
    ``MIN_DELAY`` so a stale reading can never busy-loop the service.
    """
    now = now_fn()
    target = warmed_at + FIVE_HOURS + REFRESH_OFFSET
    snapshot = usage_snapshot.read_cache_only("claude", account)
    if snapshot is not None:
        reset_ts = usage_snapshot.reset_epoch(snapshot.resets_at)
        if reset_ts is not None and reset_ts > now:
            target = reset_ts + REFRESH_OFFSET
    return max(MIN_DELAY, target - now)


@dataclass(frozen=True)
class KeepWarmResult:
    account: str
    cycles: int
    warmed: int
    stopped: str


def _default_warm(account: str) -> bool:
    results = warmup.warmup([account])
    return bool(results and results[0].ok)


def keep_warm(
    account: str,
    *,
    max_cycles: int | None = None,
    warm: Callable[[str], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], float] = time.time,
) -> KeepWarmResult:
    """Warm ``account`` now, then re-warm just after each 5h reset, indefinitely.

    ``max_cycles`` bounds the loop for tests; production runs it unbounded until the
    service is stopped (or ``KeyboardInterrupt``). ``warm``/``sleep``/``now_fn`` are
    test seams. Returns once bounded or interrupted, reporting the cycle counts.
    """
    warm_one = warm or _default_warm
    cycles = warmed = 0
    stopped = "max cycles"
    try:
        while True:
            if max_cycles is not None and cycles >= max_cycles:
                break
            cycles += 1
            warmed_at = now_fn()
            ok = False
            try:
                ok = bool(warm_one(account))
            except Exception:  # noqa: BLE001 - a warm failure never stops the loop
                ok = False
            if ok:
                warmed += 1
            delay = next_delay(account, warmed_at=warmed_at, now_fn=now_fn)
            # Each cycle logs to the journal (PYTHONUNBUFFERED under the service), so a
            # 24/7 keep-warm unit is debuggable remotely and its live probe can confirm
            # it is doing its job, not merely installed.
            print(f"keep-warm {account}: {'warmed' if ok else 'warm failed'}; "
                  f"next in {int(delay)}s", flush=True)
            sleep(delay)
    except KeyboardInterrupt:
        stopped = "interrupt"
    return KeepWarmResult(account, cycles, warmed, stopped)
