"""The standing keep-warm loop (`horus warmup --keep`).

Cadence logic and the loop are unit-tested with injected clock/warm/sleep seams;
the one thing only a live probe can prove — the systemd service reaching `active`
and logging a warm cycle — is in the PR's runtime gate.
"""

from __future__ import annotations

from horus import keepwarm, usage_snapshot


def test_next_delay_uses_the_fixed_5h_anchor_when_no_reset_is_recorded(monkeypatch):
    # No recorded snapshot → the window is anchored to this warmup: warmed_at + 5h + offset.
    monkeypatch.setattr(usage_snapshot, "read_cache_only", lambda agent, account: None)
    delay = keepwarm.next_delay("claude-personal", warmed_at=1000.0, now_fn=lambda: 1000.0)
    assert delay == keepwarm.FIVE_HOURS + keepwarm.REFRESH_OFFSET


def test_next_delay_prefers_a_recorded_future_reset(monkeypatch):
    # A fresher recorded reset (interactive work populated the statusline cache) wins.
    now = 1000.0
    reset_ts = now + 900.0  # window resets in 15 min per the recording
    snap = usage_snapshot.UsageSnapshot(42.0, "recorded-reset")
    monkeypatch.setattr(usage_snapshot, "read_cache_only", lambda agent, account: snap)
    monkeypatch.setattr(usage_snapshot, "reset_epoch", lambda value: reset_ts)
    delay = keepwarm.next_delay("claude-personal", warmed_at=now, now_fn=lambda: now)
    assert delay == 900.0 + keepwarm.REFRESH_OFFSET  # reset + offset, not the 5h anchor


def test_next_delay_ignores_a_past_reset_and_floors_the_delay(monkeypatch):
    # A stale/past recorded reset must never shorten the cadence below the floor.
    now = 1000.0
    snap = usage_snapshot.UsageSnapshot(42.0, "stale")
    monkeypatch.setattr(usage_snapshot, "read_cache_only", lambda agent, account: snap)
    monkeypatch.setattr(usage_snapshot, "reset_epoch", lambda value: now - 500.0)
    # warmed_at far in the past too, so the fixed anchor is also behind now → floor applies.
    delay = keepwarm.next_delay("claude-personal", warmed_at=now - 99999.0, now_fn=lambda: now)
    assert delay == keepwarm.MIN_DELAY


def test_keep_warm_loops_bounded_and_reports_cycle_counts():
    warmed: list[str] = []
    slept: list[float] = []
    result = keepwarm.keep_warm(
        "claude-work",
        max_cycles=3,
        warm=lambda account: (warmed.append(account) or True),
        sleep=slept.append,
        now_fn=lambda: 1000.0,
    )
    assert warmed == ["claude-work", "claude-work", "claude-work"]
    assert len(slept) == 3
    assert result.cycles == 3 and result.warmed == 3 and result.stopped == "max cycles"


def test_keep_warm_survives_a_failing_warm_and_keeps_going():
    calls = {"n": 0}

    def flaky(account: str) -> bool:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("transport blip")
        return True

    result = keepwarm.keep_warm(
        "claude-work", max_cycles=3, warm=flaky, sleep=lambda d: None, now_fn=lambda: 0.0,
    )
    # All three cycles ran; the raising one counted as not-warmed but did not stop the loop.
    assert result.cycles == 3 and result.warmed == 2
