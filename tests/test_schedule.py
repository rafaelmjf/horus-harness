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

from horus import cli, notify_listen, schedule

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

    class _Active:
        returncode = 0
        stdout = "active"
        stderr = ""

    def _fake(*args, **kwargs):
        calls.append(args)
        # Self-verify polls `is-active` after every `enable --now`; report the
        # freshly-installed unit as up so existing install tests stay fast and only
        # the dedicated self-verify tests exercise the polling/failure path.
        if args and args[0] == "is-active":
            return _Active()
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


# --- pre-launch death escalates, not dies in the journal ---------------------


def test_create_writes_an_onfailure_escalation_unit(units, tmp_path):
    """ANY non-zero launch exit must escalate — including an argparse error that exits
    before the Python handler runs. That is why it lives at the unit level."""
    created = _create(tmp_path, card="my-card")
    directory = schedule.unit_dir()
    notify_unit = directory / f"horus-sched-{created.id}-notify.service"
    assert notify_unit.exists()
    service = (directory / f"horus-sched-{created.id}.service").read_text()
    assert f"OnFailure=horus-sched-{created.id}-notify.service" in service


def test_the_escalation_unit_calls_notify_escalate_with_card_and_unit(units, tmp_path):
    created = _create(tmp_path, card="my-card")
    escalate = (schedule.unit_dir() / f"horus-sched-{created.id}-notify.service").read_text()
    exec_line = next(l for l in escalate.splitlines() if l.startswith("ExecStart="))
    assert "notify escalate" in exec_line
    assert "--event dispatch-launch-failed" in exec_line
    assert f"--unit horus-sched-{created.id}.service" in exec_line
    assert "--card my-card" in exec_line
    # oneshot, so a dead escalation never lingers as an active unit
    assert "Type=oneshot" in escalate


def test_the_escalation_unit_omits_card_when_there_is_none(units, tmp_path):
    created = _create(tmp_path, card=None)
    escalate = (schedule.unit_dir() / f"horus-sched-{created.id}-notify.service").read_text()
    assert "--card" not in escalate
    assert "--event dispatch-launch-failed" in escalate


def test_cancel_removes_the_escalation_unit(units, tmp_path):
    created = _create(tmp_path, card="x")
    notify_unit = schedule.unit_dir() / f"horus-sched-{created.id}-notify.service"
    assert notify_unit.exists()
    schedule.cancel(created.id)
    assert not notify_unit.exists()


def test_a_rejected_unit_leaves_no_escalation_unit_behind(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule, "unit_dir", lambda: tmp_path / "u")
    monkeypatch.setattr(schedule, "availability", lambda: schedule.Availability(True, "ok"))
    monkeypatch.setattr(schedule, "_live_state", lambda unit, when: {"next_run": None, "fired": False})

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "bad unit"

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _Fail())
    with pytest.raises(schedule.ScheduleError):
        _create(tmp_path, card="x")
    assert not list((tmp_path / "u").glob("*-notify.service"))


def test_the_escalation_unit_is_not_read_back_as_a_schedule(units, tmp_path):
    """It has no timer, so `schedule list` must never surface it as a dispatch."""
    _create(tmp_path, card="x")
    assert len(schedule.load_all()) == 1


def test_unit_exit_detail_reads_the_failed_units_exit_code(monkeypatch):
    class _Show:
        returncode = 0
        stdout = "ExecMainStatus=2\nResult=exit-code\n"
        stderr = ""

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _Show())
    detail = schedule.unit_exit_detail("horus-sched-abc.service")
    assert "exit status 2" in detail
    assert "exit-code" in detail


def test_unit_exit_detail_is_best_effort_when_systemd_is_unreadable(monkeypatch):
    def _boom(*a, **k):
        raise schedule.ScheduleError("systemctl failed")

    monkeypatch.setattr(schedule, "_systemctl", _boom)
    assert schedule.unit_exit_detail("x.service") == "exit status unavailable"


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


def test_cli_schedules_a_supervise_verbatim(units, tmp_path):
    """The autonomous loop arms its INDEPENDENT supervisor with `-- supervise <id>`.
    That must schedule `horus supervise <id>`, NOT `horus run supervise <id>` (which
    would fire a worker with prompt 'supervise' — the #338-era blocking defect)."""
    parser = cli.build_parser()
    args = parser.parse_args(
        ["schedule", "run", "--at", "+10m", "--", "supervise", "abc123"]
    )
    assert cli.cmd_schedule_at(args) == 0
    command = schedule.load_all()[0].command
    assert command[1:] == ("-m", "horus", "supervise", "abc123")
    assert "run" not in command  # never `horus run supervise …`


def test_cli_schedules_warmup_verbatim(units, tmp_path):
    """The documented `schedule run … -- warmup` must schedule `horus warmup`."""
    parser = cli.build_parser()
    args = parser.parse_args(["schedule", "run", "--at", "+1h", "--", "warmup"])
    assert cli.cmd_schedule_at(args) == 0
    assert schedule.load_all()[0].command[1:] == ("-m", "horus", "warmup")


def test_cli_still_prepends_run_for_a_prompt(units, tmp_path):
    """A leading token that is NOT a horus subcommand is a `run` prompt — the primary
    form stays backward-compatible even with the live command set present."""
    parser = cli.build_parser()
    args = parser.parse_args(
        ["schedule", "run", "--at", "+2h", "--", "do the thing", "--unattended", "--card", "c"]
    )
    assert cli.cmd_schedule_at(args) == 0
    command = schedule.load_all()[0].command
    assert command[1:4] == ("-m", "horus", "run")
    assert list(command[4:]) == ["do the thing", "--unattended", "--card", "c"]


def test_cli_describes_a_scheduled_subcommand(units, tmp_path):
    """A subcommand dispatch labels itself by its command + args, not a card."""
    parser = cli.build_parser()
    args = parser.parse_args(["schedule", "run", "--at", "+10m", "--", "supervise", "abc123"])
    cli.cmd_schedule_at(args)
    assert schedule.load_all()[0].description == "supervise abc123"


def test_cli_describes_a_dispatch_by_its_card(units, tmp_path):
    cli.cmd_schedule_at(_args(run_args=["--", "p", "--card", "my-card"]))
    assert schedule.load_all()[0].description == "card my-card"


def test_cli_wires_the_card_into_the_escalation_unit(units, tmp_path):
    """A pre-launch death should name the card that failed, not just an exit code."""
    cli.cmd_schedule_at(_args(run_args=["--", "p", "--card", "my-card"]))
    created = schedule.load_all()[0]
    escalate = (schedule.unit_dir() / f"horus-sched-{created.id}-notify.service").read_text()
    assert "--card my-card" in escalate


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


# --- andon: halt a pending dispatch but keep it visible ----------------------


def test_halt_disarms_the_timer_and_records_the_reason(units, tmp_path):
    created = _create(tmp_path)
    halted = schedule.halt(created.id, "blocked: depends on failed card foo")
    assert halted is not None and halted.halted and "depends on failed card foo" in halted.halt_reason
    # the timer was disabled (disarmed) so it can never fire on a red base
    assert any(call and call[0] == "disable" for call in units)
    # and the marker persists so the halt stays visible
    assert (schedule.unit_dir() / f"horus-sched-{created.id}.halt").exists()


def test_load_all_surfaces_a_halted_dispatch_with_its_reason(units, tmp_path):
    created = _create(tmp_path)
    schedule.halt(created.id, "blocked: depends on failed card foo")
    listed = [s for s in schedule.load_all() if s.id == created.id]
    assert listed and listed[0].halted
    assert listed[0].halt_reason and "foo" in listed[0].halt_reason
    assert listed[0].fired is False  # halted, not fired


def test_cancel_clears_the_halt_marker(units, tmp_path):
    created = _create(tmp_path)
    schedule.halt(created.id, "blocked")
    assert (schedule.unit_dir() / f"horus-sched-{created.id}.halt").exists()
    schedule.cancel(created.id)
    assert not (schedule.unit_dir() / f"horus-sched-{created.id}.halt").exists()


def test_halt_is_none_for_an_unknown_id(units, tmp_path):
    _create(tmp_path)
    assert schedule.halt("nonexistent", "reason") is None


# --- andon inverse: release re-arms a halted dispatch ------------------------


def test_release_rearms_a_halted_dispatch(units, tmp_path):
    created = _create(tmp_path)
    schedule.halt(created.id, "blocked: depends on failed card foo")
    assert (schedule.unit_dir() / f"horus-sched-{created.id}.halt").exists()
    released = schedule.release(created.id)
    assert released is not None and released.halted is False and released.halt_reason is None
    # the marker is cleared and the timer re-enabled (inverse of halt's disable)
    assert not (schedule.unit_dir() / f"horus-sched-{created.id}.halt").exists()
    assert any(call and call[0] == "enable" for call in units)


def test_release_refuses_a_dispatch_that_is_not_halted(units, tmp_path):
    created = _create(tmp_path)  # pending, never halted
    assert schedule.release(created.id) is None


def test_release_is_none_for_an_unknown_id(units, tmp_path):
    _create(tmp_path)
    assert schedule.release("nonexistent") is None


def test_release_round_trips_visible_in_load_all(units, tmp_path):
    created = _create(tmp_path)
    schedule.halt(created.id, "blocked")
    assert [s for s in schedule.load_all() if s.id == created.id][0].halted
    schedule.release(created.id)
    listed = [s for s in schedule.load_all() if s.id == created.id][0]
    assert listed.halted is False  # pending again


# --- persistent steering listener (trip-mode service) ------------------------


def test_install_listen_service_writes_and_enables_a_unit(units, tmp_path):
    schedule.install_listen_service(
        command=("horus", "notify", "listen"), cwd=Path("/repo"),
    )
    unit = schedule.unit_dir() / f"{schedule.LISTEN_UNIT}.service"
    assert unit.exists()
    text = unit.read_text()
    assert "Restart=always" in text and "notify" in text
    assert any(call and call[0] == "enable" for call in units)


def test_install_listen_service_refuses_a_second_listener(units, tmp_path, monkeypatch):
    schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))
    # Simulate the first one being active so the second install is refused by name.
    monkeypatch.setattr(schedule, "listen_service_active", lambda: True)
    with pytest.raises(schedule.ScheduleError, match="already running"):
        schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))


@pytest.mark.parametrize("state,live", [
    ("active", True), ("activating", True), ("reloading", True),
    ("inactive", False), ("failed", False), ("", False),
])
def test_listen_service_active_treats_startup_as_live(units, tmp_path, monkeypatch, state, live):
    """A Type=simple unit sits in 'activating' right after enable --now; a second
    install racing that window must still be refused (observed live 2026-07-18)."""
    schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))

    class _State:
        returncode = 0
        stdout = state
        stderr = ""

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _State())
    assert schedule.listen_service_active() is live


def test_remove_listen_service_tears_it_down(units, tmp_path):
    schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))
    assert schedule.remove_listen_service() is True
    assert not (schedule.unit_dir() / f"{schedule.LISTEN_UNIT}.service").exists()


def test_remove_listen_service_is_false_when_none_installed(units, tmp_path):
    assert schedule.remove_listen_service() is False


def test_install_listen_service_bakes_an_absolute_execstart(units, tmp_path, monkeypatch):
    """systemd resolves a bare ExecStart name against its own PATH (system bins),
    NOT Environment=PATH — so a bare `horus` fails 203/EXEC in ~/.local/bin. The
    unit must carry an ABSOLUTE path (regression for the v0.0.62 crash-loop)."""
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "/home/rafa/.local/bin/horus")
    schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))
    execstart = next(
        line for line in (schedule.unit_dir() / f"{schedule.LISTEN_UNIT}.service").read_text().splitlines()
        if line.startswith("ExecStart=")
    )
    assert execstart == "ExecStart=/home/rafa/.local/bin/horus notify listen"
    assert "ExecStart=horus " not in execstart  # never the bare name


def test_absolute_exec_falls_back_when_unresolved(monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: None)
    assert schedule._absolute_exec(("horus", "notify", "listen")) == ("horus", "notify", "listen")


def test_install_listen_service_rolls_back_on_a_crash_loop(units, tmp_path, monkeypatch):
    """`enable --now` returning 0 is not proof of life: a unit that immediately
    203/EXECs still reports success there (#322). Self-verify must catch it and
    leave NO unit behind rather than reporting a dead service installed."""

    class _Failed:
        returncode = 0
        stdout = "failed"
        stderr = ""

    class _Ok:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake(*args, **kwargs):
        units.append(args)
        return _Failed() if args and args[0] == "is-active" else _Ok()

    monkeypatch.setattr(schedule, "_systemctl", _fake)
    monkeypatch.setattr(
        schedule, "_journal_tail", lambda unit, lines=20: "Main process exited, code=exited, status=203/EXEC"
    )
    with pytest.raises(schedule.ScheduleError, match="203/EXEC"):
        schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))
    assert not (schedule.unit_dir() / f"{schedule.LISTEN_UNIT}.service").exists()
    assert any(call and call[0] == "disable" for call in units)


def test_await_active_times_out_when_stuck_activating(units, tmp_path, monkeypatch):
    """A unit that never leaves 'activating' (rather than failing outright) must
    still time out — the bounded window is the safety net, not just `failed`."""

    class _Activating:
        returncode = 0
        stdout = "activating"
        stderr = ""

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _Activating())
    monkeypatch.setattr(schedule, "_journal_tail", lambda unit, lines=20: "still starting up")
    with pytest.raises(schedule.ScheduleError, match="did not reach 'active'"):
        schedule._await_active("some.service", timeout=0.05, interval=0.01)


def test_await_active_returns_once_active(units, tmp_path, monkeypatch):
    class _Active:
        returncode = 0
        stdout = "active"
        stderr = ""

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _Active())
    schedule._await_active("some.service", timeout=0.05, interval=0.01)  # does not raise


def test_restart_listen_service_restarts_when_installed(units, tmp_path, monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "/abs/horus")
    schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))
    units.clear()
    assert schedule.restart_listen_service() is True
    assert any(call and call[0] == "restart" for call in units)


def test_restart_listen_service_is_false_when_none_installed(units, tmp_path):
    assert schedule.restart_listen_service() is False


def test_cli_notify_listen_restart(units, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "/abs/horus")
    schedule.install_listen_service(command=("horus", "notify", "listen"), cwd=Path("/repo"))
    ns = argparse.Namespace(path=None, service=False, stop=False, restart=True, for_=None)
    assert cli.cmd_notify_listen(ns) == 0
    assert "Restarted the persistent listen service" in capsys.readouterr().out


# --- CLI wiring: release + listen service ------------------------------------


def test_cli_release_rearms_a_halted_dispatch(units, tmp_path, capsys):
    created = _create(tmp_path)
    schedule.halt(created.id, "blocked")
    assert cli.cmd_schedule_release(argparse.Namespace(id=created.id)) == 0
    assert "Released" in capsys.readouterr().out
    assert not (schedule.unit_dir() / f"horus-sched-{created.id}.halt").exists()


def test_cli_release_refuses_a_pending_dispatch_with_a_clear_reason(units, tmp_path, capsys):
    created = _create(tmp_path)  # pending, not halted
    assert cli.cmd_schedule_release(argparse.Namespace(id=created.id)) == 1
    assert "not halted" in capsys.readouterr().out


def test_cli_notify_listen_service_installs_then_stops(units, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(notify_listen, "validate_config", lambda: None)
    monkeypatch.setattr(schedule, "linger_enabled", lambda: True)
    ns = argparse.Namespace(path=None, service=True, stop=False, for_=None)
    assert cli.cmd_notify_listen(ns) == 0
    assert "Installed persistent listen service" in capsys.readouterr().out
    stop = argparse.Namespace(path=None, service=False, stop=True, for_=None)
    assert cli.cmd_notify_listen(stop) == 0
    assert "Stopped and removed" in capsys.readouterr().out


def test_cli_notify_listen_service_refused_on_bad_config(units, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(notify_listen, "validate_config", lambda: (2, "telegram sink needs both token and chat_id in [notify]."))
    ns = argparse.Namespace(path=None, service=True, stop=False, for_=None)
    assert cli.cmd_notify_listen(ns) == 2
    assert "token and chat_id" in capsys.readouterr().out


# --- keep-warm services: one persistent unit PER ACCOUNT ---------------------

def test_keepwarm_unit_sanitises_the_alias():
    assert schedule.keepwarm_unit("claude-personal") == "horus-keepwarm-claude-personal"
    # An alias with odd characters can never produce an unwritable unit path.
    assert schedule.keepwarm_unit("weird/../name") == "horus-keepwarm-weird-..-name"


def test_install_keepwarm_service_writes_an_absolute_execstart(units, tmp_path, monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: "/home/rafa/.local/bin/horus")
    schedule.install_keepwarm_service(
        account="claude-personal",
        command=("horus", "warmup", "--keep", "--account", "claude-personal"),
        cwd=Path("/repo"),
    )
    unit = schedule.unit_dir() / "horus-keepwarm-claude-personal.service"
    text = unit.read_text()
    execstart = next(l for l in text.splitlines() if l.startswith("ExecStart="))
    assert execstart == "ExecStart=/home/rafa/.local/bin/horus warmup --keep --account claude-personal"
    assert "ExecStart=horus " not in execstart  # never the bare name (203/EXEC regression)
    assert "Restart=always" in text
    assert any(call and call[0] == "enable" for call in units)


def test_keepwarm_allows_a_second_account_unlike_the_single_listener(units, tmp_path):
    for alias in ("claude-personal", "claude-work"):
        schedule.install_keepwarm_service(
            account=alias, command=("horus", "warmup", "--keep", "--account", alias), cwd=Path("/repo"),
        )
    assert (schedule.unit_dir() / "horus-keepwarm-claude-personal.service").exists()
    assert (schedule.unit_dir() / "horus-keepwarm-claude-work.service").exists()


@pytest.mark.parametrize("state,live", [("active", True), ("activating", True), ("inactive", False), ("", False)])
def test_keepwarm_service_active_reads_systemd_state(units, tmp_path, monkeypatch, state, live):
    schedule.install_keepwarm_service(
        account="claude-work", command=("horus", "warmup", "--keep", "--account", "claude-work"), cwd=Path("/repo"),
    )

    class _State:
        returncode = 0
        stdout = state
        stderr = ""

    monkeypatch.setattr(schedule, "_systemctl", lambda *a, **k: _State())
    assert schedule.keepwarm_service_active("claude-work") is live


def test_keepwarm_active_accounts_maps_each_installed_unit(units, tmp_path, monkeypatch):
    schedule.install_keepwarm_service(
        account="claude-personal", command=("horus", "warmup"), cwd=Path("/repo"),
    )
    monkeypatch.setattr(schedule, "keepwarm_service_active", lambda alias: alias == "claude-personal")
    assert schedule.keepwarm_active_accounts() == {"claude-personal": True}


def test_remove_keepwarm_service_tears_down_only_that_account(units, tmp_path):
    schedule.install_keepwarm_service(account="claude-work", command=("horus", "warmup"), cwd=Path("/repo"))
    assert schedule.remove_keepwarm_service("claude-work") is True
    assert not (schedule.unit_dir() / "horus-keepwarm-claude-work.service").exists()
    assert schedule.remove_keepwarm_service("claude-work") is False


def _warmup_ns(**over):
    base = dict(account=None, model="haiku", keep=False, service=False, stop=False, restart=False, status=False)
    base.update(over)
    return argparse.Namespace(**base)


def test_cli_warmup_keep_service_installs_then_stops(units, tmp_path, capsys, monkeypatch):
    from horus import warmup
    monkeypatch.setattr(warmup, "claude_accounts", lambda: ["claude-personal"])
    monkeypatch.setattr(schedule, "linger_enabled", lambda: True)
    assert cli.cmd_warmup(_warmup_ns(account="claude-personal", service=True)) == 0
    assert "Installed keep-warm service" in capsys.readouterr().out
    assert cli.cmd_warmup(_warmup_ns(account="claude-personal", stop=True)) == 0
    assert "Stopped and removed" in capsys.readouterr().out


def test_cli_warmup_keep_refuses_an_unknown_account(units, tmp_path, capsys, monkeypatch):
    from horus import warmup
    monkeypatch.setattr(warmup, "claude_accounts", lambda: ["claude-personal"])
    assert cli.cmd_warmup(_warmup_ns(account="nope", service=True)) == 1
    assert "No isolated Claude account" in capsys.readouterr().out


def test_cli_warmup_keep_status_lists_services(units, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(schedule, "keepwarm_active_accounts", lambda: {"claude-personal": True, "claude-work": False})
    assert cli.cmd_warmup(_warmup_ns(status=True)) == 0
    out = capsys.readouterr().out
    assert "claude-personal: active" in out and "claude-work: installed (not running)" in out


# --- proxy service: a Docker-backed persistent unit -----------------------------

def test_install_proxy_service_writes_docker_unit_with_absolute_execstart(units, tmp_path, monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: f"/usr/bin/{name}")
    cmd = ("docker", "run", "--rm", "--name", "horus-cliproxy", "-p", "127.0.0.1:8317:8317",
           "eceasy/cli-proxy-api:latest", "/CLIProxyAPI/CLIProxyAPI")
    schedule.install_proxy_service(command=cmd)
    text = (schedule.unit_dir() / f"{schedule.PROXY_UNIT}.service").read_text()
    execstart = next(l for l in text.splitlines() if l.startswith("ExecStart="))
    assert execstart.startswith("ExecStart=/usr/bin/docker run")   # absolute (203/EXEC lesson)
    assert "Restart=always" in text
    assert f"ExecStartPre=-/usr/bin/docker rm -f {schedule.PROXY_UNIT}" in text  # clears a stale container
    # bug #3: stop must force-remove the --rm container systemd's stop can leave alive
    assert f"ExecStopPost=-/usr/bin/docker rm -f {schedule.PROXY_UNIT}" in text
    assert any(call and call[0] == "enable" for call in units)


def test_remove_proxy_service_tears_it_down(units, tmp_path, monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda name: f"/usr/bin/{name}")
    schedule.install_proxy_service(command=("docker", "run", "eceasy/cli-proxy-api:latest"))
    assert schedule.remove_proxy_service() is True
    assert not (schedule.unit_dir() / f"{schedule.PROXY_UNIT}.service").exists()
    assert schedule.remove_proxy_service() is False
