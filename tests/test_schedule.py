"""Scheduling a `horus run` to fire later on this machine.

Everything that can be tested without a real systemd is tested here — time parsing,
unit generation, reading schedules back, refusal paths. The one thing only a live
probe can prove (a timer actually firing) is in the PR's runtime gate.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from horus import cli, schedule

NOW = datetime(2026, 7, 17, 15, 0).astimezone()


@pytest.fixture
def units(tmp_path, monkeypatch):
    """Unit files in a temp dir; systemctl stubbed to succeed and record calls."""
    monkeypatch.setattr(schedule, "unit_dir", lambda: tmp_path / "systemd-user")
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(True, "stubbed"))
    calls: list[tuple[str, ...]] = []

    class _Ok:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake(*args, **kwargs):
        calls.append(args)
        return _Ok()

    monkeypatch.setattr(schedule, "_systemctl", _fake)
    monkeypatch.setattr(schedule, "_live_state", lambda unit, when: {"next_run": None, "fired": False})
    return calls


# --- parsing a time: never guess ---------------------------------------------


@pytest.mark.parametrize("text,expected", [
    ("+30s", timedelta(seconds=30)),
    ("+15m", timedelta(minutes=15)),
    ("+2h", timedelta(hours=2)),
    ("+1d", timedelta(days=1)),
    ("+ 2 h", timedelta(hours=2)),
    ("+2H", timedelta(hours=2)),
])
def test_relative_offsets(text, expected):
    assert schedule.parse_when(text, now=NOW) == NOW + expected


def test_absolute_local_time():
    assert schedule.parse_when("2026-07-22 09:00", now=NOW).strftime("%Y-%m-%d %H:%M") == "2026-07-22 09:00"


def test_rfc3339_with_offset_is_accepted():
    parsed = schedule.parse_when("2026-07-22T09:00:00+02:00", now=NOW)
    assert parsed.hour == 9 and parsed.utcoffset() == timedelta(hours=2)


def test_a_naive_time_is_read_as_local():
    assert schedule.parse_when("2026-07-22 09:00", now=NOW).tzinfo is not None


def test_natural_language_is_refused_not_guessed():
    """A misread "5:30 tomorrow" fires a real worker at the wrong hour, unattended."""
    for text in ("5:30 tomorrow", "next monday", "in a bit", "tomorrow morning"):
        with pytest.raises(schedule.ScheduleError, match="could not read"):
            schedule.parse_when(text, now=NOW)


def test_a_past_time_is_refused():
    with pytest.raises(schedule.ScheduleError, match="in the past"):
        schedule.parse_when("2020-01-01 09:00", now=NOW)


def test_a_zero_or_negative_offset_is_refused():
    with pytest.raises(schedule.ScheduleError, match="positive"):
        schedule.parse_when("+0m", now=NOW)


def test_an_empty_time_is_refused():
    with pytest.raises(schedule.ScheduleError, match="no time given"):
        schedule.parse_when("", now=NOW)


# --- the units it writes ------------------------------------------------------


def _create(units_dir: Path, **kw):
    defaults = dict(
        when=NOW + timedelta(hours=2),
        command=("/usr/bin/python", "-m", "horus", "run", "do it", "--card", "x"),
        description="card x",
        cwd=Path("/repo"),
    )
    defaults.update(kw)
    return schedule.create(**defaults)


def test_create_writes_a_timer_and_a_service(units, tmp_path):
    created = _create(tmp_path)
    directory = schedule.unit_dir()
    assert (directory / f"horus-sched-{created.id}.timer").exists()
    assert (directory / f"horus-sched-{created.id}.service").exists()


def test_the_timer_survives_reboot_and_catches_up_a_missed_slot(units, tmp_path):
    """Transient units (systemd-run) live in RAM: a reboot silently erases every
    pending dispatch. On-disk + enabled + Persistent is what makes a 6-day trip safe."""
    created = _create(tmp_path)
    timer = (schedule.unit_dir() / f"horus-sched-{created.id}.timer").read_text()
    assert "Persistent=true" in timer          # fires a slot missed while suspended/off
    assert "WantedBy=timers.target" in timer   # re-armed after a reboot
    assert "RemainAfterElapse=no" in timer     # one-shot: a card is done once
    assert "OnCalendar=2026-07-17 17:00:00" in timer
    assert f"AccuracySec={schedule.ACCURACY}" in timer
    # `enable` (not merely `start`) is what survives the reboot.
    assert any("enable" in call for call in units)


def test_the_service_carries_PATH_so_the_worker_can_find_its_agent(units, tmp_path, monkeypatch):
    """A systemd user unit starts with a minimal environment; without PATH the
    dispatch fires and then fails at the last inch looking for `claude`."""
    monkeypatch.setenv("PATH", "/opt/bin:/usr/bin")
    created = _create(tmp_path)
    service = (schedule.unit_dir() / f"horus-sched-{created.id}.service").read_text()
    assert "Environment=PATH=/opt/bin:/usr/bin" in service
    assert "WorkingDirectory=/repo" in service
    assert "Type=oneshot" in service


def test_exec_start_quotes_arguments_with_spaces(units, tmp_path):
    created = _create(tmp_path, command=("/py", "-m", "horus", "run", "fix the bug", "--card", "x"))
    service = (schedule.unit_dir() / f"horus-sched-{created.id}.service").read_text()
    assert 'ExecStart=/py -m horus run "fix the bug" --card x' in service


def test_a_newline_in_a_description_cannot_inject_a_directive(units, tmp_path):
    """A unit file is newline-delimited, so an unescaped newline in any value would
    let a description become a directive. Landing inside the Description VALUE is
    harmless; starting its own line is not."""
    created = _create(tmp_path, description="evil\nExecStart=/bin/rm -rf /")
    timer = (schedule.unit_dir() / f"horus-sched-{created.id}.timer").read_text()
    assert not any(line.startswith("ExecStart=") for line in timer.splitlines())
    assert len([l for l in timer.splitlines() if l.startswith("Description=")]) == 1


def test_create_refuses_with_no_command(units, tmp_path):
    with pytest.raises(schedule.ScheduleError, match="nothing to schedule"):
        _create(tmp_path, command=())


def test_create_refuses_where_systemd_is_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule, "unit_dir", lambda: tmp_path / "u")
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(False, "this is Windows"))
    with pytest.raises(schedule.ScheduleError, match="this is Windows"):
        _create(tmp_path)


def test_a_rejected_unit_leaves_nothing_behind(monkeypatch, tmp_path):
    """A half-written schedule is worse than none: it looks armed and never fires."""
    monkeypatch.setattr(schedule, "unit_dir", lambda: tmp_path / "u")
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(True, "ok"))
    monkeypatch.setattr(schedule, "_live_state", lambda unit, when: {"next_run": None, "fired": False})

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "bad unit"

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _Fail())
    with pytest.raises(schedule.ScheduleError, match="rejected"):
        _create(tmp_path)
    assert not list((tmp_path / "u").glob("*.timer"))
    assert not list((tmp_path / "u").glob("*.service"))


# --- reading them back --------------------------------------------------------


def test_load_all_reconstructs_from_the_units_systemd_reads(units, tmp_path):
    """systemd owns the state; there is no second registry to drift out of sync."""
    created = _create(tmp_path, description="card alpha")
    loaded = schedule.load_all()
    assert len(loaded) == 1
    assert loaded[0].id == created.id
    assert loaded[0].description == "card alpha"
    assert loaded[0].when == "2026-07-17 17:00:00"
    assert loaded[0].command == ("/usr/bin/python", "-m", "horus", "run", "do it", "--card", "x")


def test_load_all_survives_a_quoted_command(units, tmp_path):
    _create(tmp_path, command=("/py", "-m", "horus", "run", "fix the bug", "--card", "x"))
    assert schedule.load_all()[0].command == ("/py", "-m", "horus", "run", "fix the bug", "--card", "x")


def test_load_all_ignores_foreign_units(units, tmp_path):
    _create(tmp_path)
    (schedule.unit_dir() / "someone-elses.timer").write_text("[Timer]\nOnCalendar=daily\n")
    assert len(schedule.load_all()) == 1


def test_load_all_is_empty_before_anything_is_scheduled(units, tmp_path):
    assert schedule.load_all() == []


def test_fired_is_read_from_the_persistent_stamp_not_the_timers_runtime_state(
    tmp_path, monkeypatch
):
    """Verified live 2026-07-17: once a one-shot elapses, its
    `LastTriggerUSecRealtime` reads EMPTY and its `ActiveState` still reads `active`
    — so a list built on either calls a fired dispatch "pending". Persistent's stamp
    file survives deactivation AND reboot, which is why systemd itself uses it.

    Deliberately does NOT use the `units` fixture: this is the one test that must
    exercise the real `_live_state`.
    """
    stamps = tmp_path / "stamps"
    stamps.mkdir()
    monkeypatch.setattr(schedule, "unit_dir", lambda: tmp_path / "systemd-user")
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(True, "stubbed"))
    monkeypatch.setattr(schedule, "stamp_path", lambda unit: stamps / f"stamp-{unit}.timer")

    class _Fired:
        returncode = 0
        # Exactly what a fired one-shot reports: no next elapse, and (for the service)
        # no retained start timestamp either.
        stdout = "NextElapseUSecRealtime=\n"
        stderr = ""

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _Fired())
    created = _create(tmp_path)   # due NOW + 2h
    stamp = stamps / f"stamp-{schedule.UNIT_PREFIX}{created.id}.timer"

    assert schedule.load_all()[0].fired is False          # no stamp at all -> pending

    # systemd creates the stamp when the timer is ENABLED, so an mtime BEFORE the
    # scheduled time means it has not run yet — presence alone proves nothing.
    stamp.touch()
    os.utime(stamp, (0, (NOW + timedelta(hours=1)).timestamp()))
    assert schedule.load_all()[0].fired is False

    # Advanced to the trigger time -> it fired.
    os.utime(stamp, (0, (NOW + timedelta(hours=2)).timestamp()))
    assert schedule.load_all()[0].fired is True


def test_cancel_drops_the_persistent_stamp(units, tmp_path, monkeypatch):
    """The stamp outlives the units; a recycled id would otherwise read as fired."""
    stamps = tmp_path / "stamps"
    stamps.mkdir()
    monkeypatch.setattr(schedule, "stamp_path", lambda unit: stamps / f"stamp-{unit}.timer")
    created = _create(tmp_path)
    stamp = stamps / f"stamp-{schedule.UNIT_PREFIX}{created.id}.timer"
    stamp.touch()
    schedule.cancel(created.id)
    assert not stamp.exists()


def test_pending_schedules_sort_before_fired_ones(units, tmp_path, monkeypatch):
    a = _create(tmp_path, when=NOW + timedelta(hours=5), description="later")
    b = _create(tmp_path, when=NOW + timedelta(hours=1), description="sooner")
    fired = {a.id}
    monkeypatch.setattr(
        schedule, "_live_state",
        lambda unit, when: {"next_run": None, "fired": any(i in unit for i in fired)},
    )
    assert [s.description for s in schedule.load_all()] == ["sooner", "later"]


# --- cancelling ---------------------------------------------------------------


def test_cancel_disarms_and_removes(units, tmp_path):
    created = _create(tmp_path)
    assert schedule.cancel(created.id).id == created.id
    assert schedule.load_all() == []
    assert any("disable" in call for call in units)


def test_cancel_accepts_a_unique_prefix(units, tmp_path):
    created = _create(tmp_path)
    assert schedule.cancel(created.id[:4]).id == created.id


def test_cancel_of_an_unknown_id_reports_rather_than_touching_anything(units, tmp_path):
    _create(tmp_path)
    assert schedule.cancel("nope") is None
    assert len(schedule.load_all()) == 1


def test_cancel_never_touches_a_unit_it_did_not_create(units, tmp_path):
    """Only `horus-sched-` units are ever candidates, so a mistyped id cannot disable
    an unrelated user timer."""
    foreign = schedule.unit_dir()
    foreign.mkdir(parents=True, exist_ok=True)
    (foreign / "backup.timer").write_text("[Timer]\nOnCalendar=daily\n")
    assert schedule.cancel("backup") is None
    assert (foreign / "backup.timer").exists()


# --- the CLI ------------------------------------------------------------------


def _args(**kw):
    base = dict(at="+2h", describe=None, path=".", run_args=[])
    base.update(kw)
    return argparse.Namespace(**base)


def test_cli_refuses_with_no_run_args(units, capsys):
    assert cli.cmd_schedule_at(_args()) == 2
    assert "nothing to run" in capsys.readouterr().out


def test_cli_strips_the_double_dash_separator(units, tmp_path, capsys):
    assert cli.cmd_schedule_at(_args(run_args=["--", "prompt", "--card", "x"])) == 0
    assert schedule.load_all()[0].command[-3:] == ("prompt", "--card", "x")


def test_cli_passes_the_run_surface_through_untouched(units, tmp_path):
    """The scheduler re-implements none of `horus run` — that is the whole design."""
    passed = ["prompt", "--unattended", "--envelope", "trip", "--card", "c", "--account", "personal"]
    cli.cmd_schedule_at(_args(run_args=["--", *passed]))
    command = schedule.load_all()[0].command
    assert command[1:4] == ("-m", "horus", "run")
    assert list(command[4:]) == passed


def test_cli_describes_a_dispatch_by_its_card(units, tmp_path):
    cli.cmd_schedule_at(_args(run_args=["--", "p", "--card", "my-card"]))
    assert schedule.load_all()[0].description == "card my-card"


def test_the_parser_does_not_leak_its_own_flags_into_the_run(units, tmp_path):
    """`--at` must stay a FLAG. With a positional WHEN, argparse.REMAINDER starts
    capturing at the next argument and swallows this command's own options into the
    pass-through — observed live: `--describe` reached `horus run`, which refused it,
    and the scheduled dispatch fired into an argparse error instead of a worker.
    """
    parser = cli.build_parser()
    args = parser.parse_args([
        "schedule", "run", "--at", "+2h", "--describe", "my label",
        "--", "the prompt", "--agent", "fake", "--account", "personal",
    ])
    assert args.at == "+2h"
    assert args.describe == "my label"          # NOT swallowed into run_args
    assert args.run_args == ["--", "the prompt", "--agent", "fake", "--account", "personal"]

    cli.cmd_schedule_at(args)
    command = schedule.load_all()[0].command
    assert "--describe" not in command          # the run never sees the scheduler's flags
    assert list(command[4:]) == ["the prompt", "--agent", "fake", "--account", "personal"]


def test_cli_refuses_an_unparseable_time(units, capsys):
    assert cli.cmd_schedule_at(_args(at="tomorrow", run_args=["--", "p"])) == 2
    assert "could not read" in capsys.readouterr().out


def test_cli_warns_when_linger_is_off(units, monkeypatch, capsys):
    """Without linger, user timers die at logout — exactly the away-mode case."""
    monkeypatch.setattr(schedule, "linger_enabled", lambda: False)
    cli.cmd_schedule_at(_args(run_args=["--", "p"]))
    out = capsys.readouterr().out
    assert "linger is OFF" in out and "enable-linger" in out


def test_cli_refuses_where_scheduling_is_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(False, "macOS uses launchd"))
    assert cli.cmd_schedule_at(_args(run_args=["--", "p"])) == 2
    assert "macOS uses launchd" in capsys.readouterr().out


def test_list_and_cancel_are_quiet_where_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(False, "this is Windows"))
    assert cli.cmd_schedule_list(argparse.Namespace(stdout=False)) == 0
    assert "this is Windows" in capsys.readouterr().out
