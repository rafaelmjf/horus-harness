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


def test_preflight_unreadable_proceeds_silently(monkeypatch, capsys):
    _stub(monkeypatch, None)
    assert cli._run_usage_preflight("claude", None, force=False) is None
    assert capsys.readouterr().out == ""


def test_preflight_percent_none_proceeds_silently(monkeypatch, capsys):
    _stub(monkeypatch, UsageSnapshot(None, None))
    assert cli._run_usage_preflight("codex", None, force=False) is None
    assert capsys.readouterr().out == ""


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
