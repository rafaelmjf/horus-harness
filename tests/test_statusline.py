"""Tests for the portable status-line renderer (horus/statusline.py)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from horus import statusline


def _epoch(dt: str) -> int:
    return int(datetime.fromisoformat(dt).replace(tzinfo=timezone.utc).timestamp())


def _payload(**over):
    base = {
        "cwd": "/home/rafa/projects/horus-harness",
        "workspace": {"current_dir": "/home/rafa/projects/horus-harness"},
        "model": {"display_name": "Opus 4.8"},
        "context_window": {"used_percentage": 42},
        "rate_limits": {
            "five_hour": {"used_percentage": 60, "resets_at": _epoch("2026-07-18T12:30")},
            "seven_day": {"used_percentage": 12, "resets_at": _epoch("2026-07-24T10:00")},
        },
        "pr": {"number": 320, "review_state": "approved"},
    }
    base.update(over)
    return base


def _render(payload, **kw):
    kw.setdefault("home", Path("/home/rafa"))
    kw.setdefault("user", "rafa")
    kw.setdefault("host", "box")
    kw.setdefault("branch_of", lambda d: "main")
    return statusline.render(payload, **kw)


def test_full_payload_renders_three_rows(tmp_path):
    # workspace.current_dir must exist for the branch segment (the renderer guards
    # git behind is_dir); use tmp_path so this holds in CI too. branch_of is stubbed.
    out = _render(_payload(workspace={"current_dir": str(tmp_path)}))
    rows = out.split("\n")
    assert len(rows) == 3
    # row 1: user@host + ~-collapsed cwd + model
    assert "rafa@box" in rows[0] and "~/projects/horus-harness" in rows[0] and "Opus 4.8" in rows[0]
    # row 2: all three meters with percents
    assert "ctx" in rows[1] and " 42%" in rows[1]
    assert "5h" in rows[1] and " 60%" in rows[1]
    assert "7d" in rows[1] and " 12%" in rows[1]
    # row 3: branch + PR
    assert "⎇ main" in rows[2] and "PR #320" in rows[2] and "approved" in rows[2]


def test_meter_bar_reflects_percent_and_never_empty_for_nonzero():
    line = statusline._meter("5h", 1, None)
    assert statusline._BAR_FILLED in line  # 1% still lights one block
    assert " 1%" in line
    full = statusline._meter("x", 100, None)
    assert full.count(statusline._BAR_FILLED) == statusline.BAR_WIDTH


def test_no_rate_limits_drops_the_meters_but_keeps_ctx():
    out = _render(_payload(rate_limits={}))
    rows = out.split("\n")
    # ctx still present (context_window is separate from rate_limits)
    assert any("ctx" in r for r in rows) and not any("5h" in r for r in rows)


def test_no_meters_at_all_drops_row_two():
    out = _render(_payload(rate_limits={}, context_window={}))
    assert not any("ctx" in r or "5h" in r for r in out.split("\n"))


def test_no_git_repo_drops_branch():
    out = _render(_payload(pr={}), branch_of=lambda d: None)
    # no branch and no PR -> row 3 gone entirely
    assert "⎇" not in out and "PR #" not in out


def test_pr_without_git_still_shows_pr():
    out = _render(_payload(), branch_of=lambda d: None)
    assert "PR #320" in out and "⎇" not in out


def test_bad_input_renders_nothing():
    assert statusline.render(None) == ""
    assert statusline.render("not a dict") == ""
    assert statusline.render([]) == ""


def test_missing_cwd_falls_back_to_home():
    out = _render(_payload(cwd=""), branch_of=lambda d: None)
    assert "rafa@box" in out  # row 1 still renders


def test_week_reset_has_no_gnu_only_directive():
    # `%b %-d`-equivalent without the Windows-rejected %-d, and no leading zero on
    # the day. Expected is computed via the same local conversion (tz-independent).
    ts = _epoch("2026-07-04T10:00")
    local = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    reset = statusline._week_reset(ts)
    assert reset == f"{local.strftime('%b')} {local.day}"
    assert "0" not in reset.split()[1] or int(reset.split()[1]) >= 10  # no zero-padded day


# --- CLI: cmd_statusline (render from stdin + --install) ----------------------


def test_cmd_statusline_renders_from_stdin(monkeypatch, capsys):
    import argparse
    import io
    import json
    from horus import cli, usage_snapshot
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload(pr={}, rate_limits={}))))
    # do not touch the real usage cache
    monkeypatch.setattr(usage_snapshot, "record_snapshot", lambda *a, **k: None)
    rc = cli.cmd_statusline(argparse.Namespace(install=False, account=None))
    out = capsys.readouterr().out
    assert rc == 0 and "ctx" in out


def test_cmd_statusline_bad_stdin_prints_nothing(monkeypatch, capsys):
    import argparse
    import io
    from horus import cli
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    rc = cli.cmd_statusline(argparse.Namespace(install=False, account=None))
    assert rc == 0 and capsys.readouterr().out == ""


def test_cmd_statusline_install_writes_pointers(monkeypatch, capsys, tmp_path):
    import argparse
    import json
    from horus import cli, config
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"work": str(tmp_path / "w")})
    rc = cli.cmd_statusline(argparse.Namespace(install=True, account=None))
    assert rc == 0
    assert "set statusLine for work" in capsys.readouterr().out
    data = json.loads((tmp_path / "w" / "settings.json").read_text())
    assert data["statusLine"]["command"] == "horus statusline"


def test_usage_bar_rounds_up_and_never_empty_for_nonzero():
    assert statusline.usage_bar(0, width=8) == "░" * 8
    assert statusline.usage_bar(100, width=8) == "█" * 8
    # 1% rounds up to one filled block, never an empty bar.
    assert statusline.usage_bar(1, width=8).startswith("█")
    assert statusline.usage_bar(50, width=8) == "█" * 4 + "░" * 4
    # Clamps negatives.
    assert statusline.usage_bar(-5, width=8) == "░" * 8


def test_usage_level_bands():
    assert statusline.usage_level(0) == "ok"
    assert statusline.usage_level(49) == "ok"
    assert statusline.usage_level(50) == "warn"
    assert statusline.usage_level(79) == "warn"
    assert statusline.usage_level(80) == "high"
    assert statusline.usage_level(100) == "high"
