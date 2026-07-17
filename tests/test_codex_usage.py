"""Tests for read-only Codex rollout usage signals."""

import json

from horus import codex_usage


def _write_rollout(home, *events):
    path = home / "sessions" / "2026" / "06" / "25" / "rollout-test.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def _turn(root):
    return {
        "timestamp": "2026-06-25T10:00:00Z",
        "type": "turn_context",
        "payload": {"cwd": str(root), "workspace_roots": [str(root)]},
    }


def _token(ts, total, window=1000, primary=12, secondary=34):
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {"total_tokens": total},
                "model_context_window": window,
            },
            "rate_limits": {
                "primary": {"used_percent": primary, "resets_at": 1782390000},
                "secondary": {"used_percent": secondary, "resets_at": 1782990000},
            },
        },
    }


def test_latest_usage_reads_matching_project_rollout(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(
        home,
        _turn(other),
        _token("2026-06-25T10:01:00Z", 990),
        _turn(project),
        _token("2026-06-25T10:02:00Z", 875, window=1000),
    )

    report = codex_usage.latest_usage(project, home=home)
    assert report is not None
    assert report.context_percent == 87.5
    assert report.primary_percent == 12


def test_usage_findings_warns_at_threshold(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(home, _turn(project), _token("2026-06-25T10:02:00Z", 910, window=1000))

    findings = codex_usage.usage_findings(project, threshold=90, home=home)
    assert findings[0].level == "warn"
    assert "Codex context 91.0%" in findings[0].message
    assert "closure ritual" in findings[0].message


def test_usage_findings_ok_when_absent(tmp_path):
    findings = codex_usage.usage_findings(tmp_path, home=tmp_path / "missing")
    assert findings[0].level == "ok"
    assert "no Codex usage signal" in findings[0].message


def test_usage_findings_marks_expired_account_window_stale(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(home, _turn(project), _token("2026-06-25T10:02:00Z", 500, primary=83))

    findings = codex_usage.usage_findings(project, home=home)
    assert "5h limit snapshot stale" in findings[0].message
    assert "5h limit 83%" not in findings[0].message


def test_latest_account_usage_picks_newest_snapshot_ignoring_project(tmp_path):
    home = tmp_path / "codex-home"
    # Older rollout (one project) + a newer rollout (another project). Rate limits
    # are account-global, so the newest snapshot wins regardless of cwd.
    _write_rollout(home, _token("2026-06-25T10:00:00Z", 500, primary=10, secondary=20))
    newer = home / "sessions" / "2026" / "06" / "26" / "rollout-new.jsonl"
    newer.parent.mkdir(parents=True)
    newer.write_text(
        json.dumps(_token("2026-06-26T10:00:00Z", 600, primary=80, secondary=90)) + "\n",
        encoding="utf-8",
    )
    report = codex_usage.latest_account_usage(home=home)
    assert report is not None
    assert report.primary_percent == 80 and report.secondary_percent == 90
    assert report.primary_resets_at is not None


def test_latest_account_usage_none_when_no_rollouts(tmp_path):
    assert codex_usage.latest_account_usage(home=tmp_path / "missing") is None


def test_current_account_reads_account_id(tmp_path):
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text(
        json.dumps({"tokens": {"account_id": "acct-abc-123"}}), encoding="utf-8"
    )
    assert codex_usage.current_account(home=home) == "acct-abc-123"


def test_current_account_none_when_file_missing(tmp_path):
    assert codex_usage.current_account(home=tmp_path / "missing") is None


def test_current_account_none_on_malformed_or_no_id(tmp_path):
    home = tmp_path / "codex-home"
    home.mkdir()
    # No account_id in the tokens object -> None (not KeyError).
    (home / "auth.json").write_text(json.dumps({"tokens": {}}), encoding="utf-8")
    assert codex_usage.current_account(home=home) is None
    # Garbage JSON -> None, never raises.
    (home / "auth.json").write_text("{not json", encoding="utf-8")
    assert codex_usage.current_account(home=home) is None


# --- window labels come from the data, never from the slot -------------------
#
# Observed 2026-07-17: Codex temporarily removed the 5-hour limit, so `primary`
# carried the WEEKLY lane (window_minutes=10080) and `secondary` was null. Horus
# read the label off the position and reported "5h limit 92% (resets
# 2026-07-23)" — a 5-hour window resetting six days out. These pin the fix
# without betting on which way that policy settles.


def _token_windows(ts, total, window=1000, *, primary=None, secondary=None):
    """A token_count event whose lanes declare their own window_minutes."""
    limits = {}
    if primary is not None:
        limits["primary"] = primary
    if secondary is not None:
        limits["secondary"] = secondary
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"last_token_usage": {"total_tokens": total}, "model_context_window": window},
            "rate_limits": limits,
        },
    }


def test_weekly_lane_in_the_primary_slot_is_not_called_5h(tmp_path):
    """The live 2026-07-17 shape: 5-hour limit removed, weekly lane in `primary`."""
    project = tmp_path / "p"
    project.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(home, _turn(project), _token_windows(
        "2026-06-25T10:02:00Z", 500,
        primary={"used_percent": 92, "resets_at": 4102444800, "window_minutes": 10080},
        secondary=None,
    ))
    message = codex_usage.usage_findings(project, home=home)[0].message
    assert "weekly limit 92%" in message
    assert "5h" not in message


def test_lanes_are_ordered_by_declared_length_not_by_slot(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    home = tmp_path / "codex-home"
    # Deliberately inverted: the long lane sits in `primary`.
    _write_rollout(home, _turn(project), _token_windows(
        "2026-06-25T10:02:00Z", 500,
        primary={"used_percent": 40, "resets_at": 4102444800, "window_minutes": 10080},
        secondary={"used_percent": 10, "resets_at": 4102444800, "window_minutes": 300},
    ))
    report = codex_usage.latest_account_usage(home=home)
    fast, slow = report.windows()
    assert (fast.percent, fast.label()) == (10, "5h")
    assert (slow.percent, slow.label()) == (40, "weekly")


def test_restored_5h_lane_reads_as_5h(tmp_path):
    """If Codex restores the 5-hour limit, nothing needs changing here."""
    project = tmp_path / "p"
    project.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(home, _turn(project), _token_windows(
        "2026-06-25T10:02:00Z", 500,
        primary={"used_percent": 55, "resets_at": 4102444800, "window_minutes": 300},
        secondary={"used_percent": 20, "resets_at": 4102444800, "window_minutes": 10080},
    ))
    message = codex_usage.usage_findings(project, home=home)[0].message
    assert "5h limit 55%" in message and "weekly limit 20%" in message


def test_an_undeclared_length_keeps_the_historical_positional_labels(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    home = tmp_path / "codex-home"
    # This fixture's resets are in the past, so both lanes render as stale — the
    # point here is only that they still carry their historical labels.
    _write_rollout(home, _turn(project), _token(
        "2026-06-25T10:02:00Z", 500, primary=12, secondary=34,
    ))
    message = codex_usage.usage_findings(project, home=home)[0].message
    assert "5h limit snapshot stale" in message
    assert "weekly limit snapshot stale" in message
    report = codex_usage.latest_account_usage(home=home)
    fast, slow = report.windows()
    assert (fast.percent, fast.label()) == (12, "5h")
    assert (slow.percent, slow.label()) == (34, "weekly")


def test_label_names_windows_from_their_length():
    def label(minutes):
        return codex_usage.RateWindow(1.0, None, minutes).label()
    assert label(300) == "5h"
    assert label(10080) == "weekly"
    assert label(1440) == "daily"
    assert label(20160) == "2-week"
    assert label(90) == "90min"
    assert codex_usage.RateWindow(1.0, None, None, "5h").label() == "5h"
