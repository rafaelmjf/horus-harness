"""`horus run` usage preflight — warn / refuse / --force / fake-exempt."""

from datetime import datetime

from horus import cli, usage_snapshot
from horus.cli import main
from horus.usage_snapshot import UsageSnapshot

NOW = datetime(2026, 7, 4, 12, 0).timestamp()
PAST_RESET = "2026-07-04 11:59"
FUTURE_RESET = "2026-07-04 21:10"
FUTURE_WEEKLY_RESET = "2026-07-11 09:00"


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _stub(monkeypatch, snap, *, refresh=None, now=NOW):
    monkeypatch.setattr(usage_snapshot.time, "time", lambda: now)
    monkeypatch.setattr(usage_snapshot, "cached_usage", lambda *a, **k: snap)
    if callable(refresh):
        monkeypatch.setattr(usage_snapshot, "refresh_usage", refresh)
    else:
        monkeypatch.setattr(usage_snapshot, "refresh_usage", lambda *a, **k: refresh)


def test_preflight_proceeds_below_warn(monkeypatch):
    _stub(monkeypatch, UsageSnapshot(50.0, FUTURE_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) is None


def test_preflight_warns_but_continues(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(83.0, FUTURE_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Warning" in out and "83%" in out and "21:10" in out


def test_preflight_refuses_at_95(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(96.0, FUTURE_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) == 2
    out = capsys.readouterr().out
    assert "Refusing to run" in out and "96%" in out


def test_preflight_force_overrides_refusal(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(99.0, FUTURE_RESET))
    assert cli._run_usage_preflight("claude", None, force=True) is None


# --- Gap C: unknown != healthy -------------------------------------------- #

def test_preflight_unknown_surfaces_notice_and_proceeds(monkeypatch, capsys):
    # No snapshot at all: surface the blind spot (default proceeds — a courtesy).
    _stub(monkeypatch, None)
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Capacity unknown for claude" in out
    assert "Proceeding anyway" in out


def test_preflight_percent_none_surfaces_notice_and_proceeds(monkeypatch, capsys):
    # Snapshot present but neither window readable -> still "unknown", still surfaced.
    _stub(monkeypatch, UsageSnapshot(None, None))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    out = capsys.readouterr().out
    assert "Capacity unknown for codex" in out


def test_preflight_refuse_on_unknown_gates_critical_launch(monkeypatch, capsys):
    _stub(monkeypatch, None)
    assert cli._run_usage_preflight("claude", "work", force=False, refuse_on_unknown=True) == 2
    out = capsys.readouterr().out
    assert "Capacity unknown for claude account work" in out
    assert "Refusing to run" in out


def test_preflight_unknown_notice_names_the_account(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(None, None))
    cli._run_usage_preflight("claude", "work", force=False)
    assert "account work" in capsys.readouterr().out


# --- Gap A: multi-window (more-constraining of 5h/weekly) ------------------ #

def test_preflight_weekly_more_constraining_refuses(monkeypatch, capsys):
    # 5h is comfortable (40%) but the weekly window is nearly exhausted (96%).
    _stub(monkeypatch, UsageSnapshot(40.0, FUTURE_RESET, 96.0, FUTURE_WEEKLY_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) == 2
    out = capsys.readouterr().out
    assert "Refusing to run" in out and "weekly" in out and "96%" in out
    assert "2026-07-11 09:00" in out  # the weekly reset, not the 5h one


def test_preflight_weekly_refusal_honors_force(monkeypatch):
    _stub(monkeypatch, UsageSnapshot(40.0, FUTURE_RESET, 96.0, FUTURE_WEEKLY_RESET))
    assert cli._run_usage_preflight("claude", None, force=True) is None


def test_preflight_five_hour_wins_when_more_constraining(monkeypatch, capsys):
    # 5h (83%) is more constraining than weekly (60%): warn cites the 5h window.
    _stub(monkeypatch, UsageSnapshot(83.0, FUTURE_RESET, 60.0, FUTURE_WEEKLY_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Warning" in out and "5h" in out and "83%" in out


def test_preflight_stale_five_hour_window_does_not_refuse_on_cached_percent(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(100.0, PAST_RESET, 20.0, FUTURE_WEEKLY_RESET))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    out = capsys.readouterr().out
    assert "Refusing to run" not in out
    assert "Warning" not in out
    assert "100%" not in out


def test_preflight_stale_weekly_window_does_not_refuse_on_cached_percent(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(20.0, FUTURE_RESET, 100.0, PAST_RESET))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    out = capsys.readouterr().out
    assert "Refusing to run" not in out
    assert "Warning" not in out
    assert "100%" not in out


def test_preflight_all_stale_windows_route_through_unknown_capacity(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(100.0, PAST_RESET, 99.0, PAST_RESET))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    out = capsys.readouterr().out
    assert "Capacity unknown for codex" in out
    assert "Proceeding anyway" in out
    assert "100%" not in out
    assert "99%" not in out


def test_preflight_refuse_on_unknown_applies_when_all_windows_are_stale(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(100.0, PAST_RESET, 99.0, PAST_RESET))
    assert cli._run_usage_preflight("codex", None, force=False, refuse_on_unknown=True) == 2
    out = capsys.readouterr().out
    assert "Capacity unknown for codex" in out
    assert "Refusing to run: --refuse-on-unknown" in out


def test_preflight_refreshes_expired_snapshot_before_deciding(monkeypatch, capsys):
    calls = {"n": 0}

    def refresh(*a, **k):
        calls["n"] += 1
        return UsageSnapshot(96.0, FUTURE_RESET)

    _stub(monkeypatch, UsageSnapshot(100.0, PAST_RESET), refresh=refresh)
    assert cli._run_usage_preflight("claude", None, force=False) == 2
    out = capsys.readouterr().out
    assert calls["n"] == 1
    assert "Refusing to run" in out and "96%" in out


# --- Gap B: closing-window visibility band [50, 80) ------------------------ #

def test_preflight_closing_band_surfaces_percent_and_reset(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(62.0, FUTURE_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Note" in out and "62%" in out and "2026-07-04 21:10" in out
    assert "may not finish this window" in out


def test_preflight_below_closing_is_silent(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(30.0, FUTURE_RESET))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    assert capsys.readouterr().out == ""


def test_preflight_closing_band_can_trip_on_weekly(monkeypatch, capsys):
    # Weekly at 55% (5h at 10%) still surfaces the closing-window note.
    _stub(monkeypatch, UsageSnapshot(10.0, FUTURE_RESET, 55.0, FUTURE_WEEKLY_RESET))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    out = capsys.readouterr().out
    assert "Note" in out and "weekly" in out and "55%" in out


def test_preflight_exempts_fake_adapter(monkeypatch):
    # A refusal-level snapshot must never gate the fake adapter (tests depend on it).
    _stub(monkeypatch, UsageSnapshot(99.0, FUTURE_RESET))
    assert cli._run_usage_preflight("fake", None, force=False) is None


def test_run_fake_adapter_is_not_gated_by_preflight(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    # Even if the snapshot would refuse, `run --agent fake` proceeds and tracks.
    _stub(monkeypatch, UsageSnapshot(99.0, FUTURE_RESET))
    rc = main(["run", "hello", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    assert "Refusing to run" not in capsys.readouterr().out


# --- staleness: a best-effort reading must never HARD-GATE a launch -----------
#
# 2026-07-23: a valid `--worker codex --account personal` dispatch was refused at
# "99% used" on an account that was ~0% used — the reading came from a rollout hours
# old because Codex had been idle, and only `--force` got the work through (it then
# ran to completion and merged a PR). Reproduced 2026-07-26 from a ~27h-old rollout.

STALE_CAPTURE = NOW - (27 * 3600)   # the reproduced case: a 27-hour-old rollout
FRESH_CAPTURE = NOW - 600           # ten minutes old


def test_stale_reading_warns_instead_of_refusing(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(99.0, FUTURE_RESET, captured_at=STALE_CAPTURE))

    assert cli._run_usage_preflight("codex", "personal", force=False) is None

    out = capsys.readouterr().out
    assert "Refusing to run" not in out
    assert "Warning" in out and "99%" in out
    assert "27h ago" in out                      # names how old, not just "stale"
    assert "Not refusing on a stale reading" in out


def test_fresh_reading_still_refuses(monkeypatch, capsys):
    """The gate is not weakened generally — only readings that can't describe now."""
    _stub(monkeypatch, UsageSnapshot(99.0, FUTURE_RESET, captured_at=FRESH_CAPTURE))

    assert cli._run_usage_preflight("codex", "personal", force=False) == 2
    assert "Refusing to run" in capsys.readouterr().out


def test_reading_without_a_capture_time_keeps_refusing(monkeypatch, capsys):
    """Claude's pushed statusline readings report no capture time; silently
    weakening their gate is not this fix's job."""
    _stub(monkeypatch, UsageSnapshot(99.0, FUTURE_RESET))

    assert cli._run_usage_preflight("claude", None, force=False) == 2
    assert "Refusing to run" in capsys.readouterr().out


def test_a_stale_reading_still_warns_in_the_warn_band(monkeypatch, capsys):
    """Staleness gates only the REFUSAL. "possibly low" is exactly what an old
    reading can honestly say, so the advisory bands keep firing."""
    _stub(monkeypatch, UsageSnapshot(83.0, FUTURE_RESET, captured_at=STALE_CAPTURE))

    assert cli._run_usage_preflight("codex", "personal", force=False) is None
    assert "Warning" in capsys.readouterr().out


def test_refusal_age_boundary_is_the_documented_horizon(monkeypatch):
    horizon = usage_snapshot.REFUSAL_MAX_READING_AGE
    just_inside = UsageSnapshot(99.0, FUTURE_RESET, captured_at=NOW - horizon + 1)
    just_outside = UsageSnapshot(99.0, FUTURE_RESET, captured_at=NOW - horizon - 1)

    _stub(monkeypatch, just_inside)
    assert cli._run_usage_preflight("codex", "personal", force=False) == 2
    _stub(monkeypatch, just_outside)
    assert cli._run_usage_preflight("codex", "personal", force=False) is None
