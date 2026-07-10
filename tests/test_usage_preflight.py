"""`horus run` usage preflight — warn / refuse / --force / fake-exempt."""

from horus import cli, usage_snapshot
from horus.cli import main
from horus.usage_snapshot import UsageSnapshot


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _stub(monkeypatch, snap):
    monkeypatch.setattr(usage_snapshot, "cached_usage", lambda *a, **k: snap)


def test_preflight_proceeds_below_warn(monkeypatch):
    _stub(monkeypatch, UsageSnapshot(50.0, "2026-07-04 21:10"))
    assert cli._run_usage_preflight("claude", None, force=False) is None


def test_preflight_warns_but_continues(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(83.0, "2026-07-04 21:10"))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Warning" in out and "83%" in out and "21:10" in out


def test_preflight_refuses_at_95(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(96.0, "2026-07-04 21:10"))
    assert cli._run_usage_preflight("claude", None, force=False) == 2
    out = capsys.readouterr().out
    assert "Refusing to run" in out and "96%" in out


def test_preflight_force_overrides_refusal(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(99.0, "2026-07-04 21:10"))
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
    _stub(monkeypatch, UsageSnapshot(40.0, "2026-07-04 21:10", 96.0, "2026-07-11 09:00"))
    assert cli._run_usage_preflight("claude", None, force=False) == 2
    out = capsys.readouterr().out
    assert "Refusing to run" in out and "weekly" in out and "96%" in out
    assert "2026-07-11 09:00" in out  # the weekly reset, not the 5h one


def test_preflight_weekly_refusal_honors_force(monkeypatch):
    _stub(monkeypatch, UsageSnapshot(40.0, "2026-07-04 21:10", 96.0, "2026-07-11 09:00"))
    assert cli._run_usage_preflight("claude", None, force=True) is None


def test_preflight_five_hour_wins_when_more_constraining(monkeypatch, capsys):
    # 5h (83%) is more constraining than weekly (60%): warn cites the 5h window.
    _stub(monkeypatch, UsageSnapshot(83.0, "2026-07-04 21:10", 60.0, "2026-07-11 09:00"))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Warning" in out and "5h" in out and "83%" in out


# --- Gap B: closing-window visibility band [50, 80) ------------------------ #

def test_preflight_closing_band_surfaces_percent_and_reset(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(62.0, "2026-07-04 21:10"))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    out = capsys.readouterr().out
    assert "Note" in out and "62%" in out and "2026-07-04 21:10" in out
    assert "may not finish this window" in out


def test_preflight_below_closing_is_silent(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(30.0, "2026-07-04 21:10"))
    assert cli._run_usage_preflight("claude", None, force=False) is None
    assert capsys.readouterr().out == ""


def test_preflight_closing_band_can_trip_on_weekly(monkeypatch, capsys):
    # Weekly at 55% (5h at 10%) still surfaces the closing-window note.
    _stub(monkeypatch, UsageSnapshot(10.0, "2026-07-04 21:10", 55.0, "2026-07-11 09:00"))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    out = capsys.readouterr().out
    assert "Note" in out and "weekly" in out and "55%" in out


def test_preflight_exempts_fake_adapter(monkeypatch):
    # A refusal-level snapshot must never gate the fake adapter (tests depend on it).
    _stub(monkeypatch, UsageSnapshot(99.0, "2026-07-04 21:10"))
    assert cli._run_usage_preflight("fake", None, force=False) is None


def test_run_fake_adapter_is_not_gated_by_preflight(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    # Even if the snapshot would refuse, `run --agent fake` proceeds and tracks.
    _stub(monkeypatch, UsageSnapshot(99.0, "2026-07-04 21:10"))
    rc = main(["run", "hello", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    assert "Refusing to run" not in capsys.readouterr().out
