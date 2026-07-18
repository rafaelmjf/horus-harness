"""Schedule a `horus run` to fire later on THIS machine, via systemd --user timers.

The 2026-07-17 dogfood scheduled its worker with a hand-rolled crontab wrapper that
hard-coded account/model/worktree/log paths and had to delete its own cron line after
firing. This replaces that with a verb.

**Deliberately wrapper-thin.** The 2026-07-17 market scan found scheduling itself is
commoditized (native scheduled tasks, cloud routines, agent-native cron): anything
here that is "just scheduling" gets subsumed. What is NOT commoditized — and what
this exists to reach — is `horus run`'s isolated-account routing, its delivery
receipts and datums, and the attachable + worktree-isolated posture. So this module
owns no scheduling logic of its own: it writes systemd units and reads them back.

**systemd owns the state.** There is no parallel registry to drift out of sync with
the timers that actually fire; the unit files under ``~/.config/systemd/user`` ARE the
record, and `list` reads them plus systemd's own view of when each fires next.

**Unit files on disk, not ``systemd-run``.** Transient units live in
``/run/user/<uid>/systemd/transient`` — RAM. They fire and self-clean neatly, but a
reboot erases every pending dispatch silently, which over a six-day trip is one
kernel update away. On-disk units survive, and ``Persistent=true`` additionally
catches up a slot missed while the machine was suspended or off.

Linux-only by capability, not by assumption: `availability()` reports why, and every
caller refuses with that reason rather than pretending to schedule something.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from horus import notify

UNIT_PREFIX = "horus-sched-"
# systemd's default AccuracySec is 1 minute, so a timer may fire up to a minute late
# (observed: an 11s delay on a 25s probe). Dispatch does not need the jitter.
ACCURACY = "1s"

_RELATIVE_RE = re.compile(r"^\+\s*(\d+)\s*([smhd])$", re.IGNORECASE)
_RELATIVE_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


class ScheduleError(Exception):
    """A schedule could not be created/read — carries a user-facing message."""


@dataclass(frozen=True)
class Availability:
    ok: bool
    reason: str


@dataclass(frozen=True)
class Schedule:
    """One scheduled dispatch, as reconstructed from its systemd units."""

    id: str
    description: str
    when: str                  # the OnCalendar stamp, "YYYY-MM-DD HH:MM:SS"
    command: tuple[str, ...]
    next_run: str | None = None   # systemd's view; None once it has elapsed
    fired: bool = False
    # Andon: a supervisor escalation halts scheduled dispatches whose card
    # (transitively) depends on the failed one. The timer is disabled so it can
    # never fire on a red base, but the units are KEPT so the halt stays visible
    # in `horus schedule list` with its reason.
    halted: bool = False
    halt_reason: str | None = None

    @property
    def unit(self) -> str:
        return f"{UNIT_PREFIX}{self.id}"


def availability() -> Availability:
    """Whether this machine can schedule, and why not when it cannot."""
    if sys.platform == "win32":
        return Availability(False, "scheduling needs systemd --user timers; this is Windows")
    if sys.platform == "darwin":
        return Availability(False, "scheduling needs systemd --user timers; macOS uses launchd")
    if not shutil.which("systemctl"):
        return Availability(False, "systemctl is not on PATH — no systemd --user timers here")
    try:
        probe = subprocess.run(
            ["systemctl", "--user", "is-system-running"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Availability(False, f"could not reach the systemd user manager: {exc}")
    # `degraded` still schedules fine — some unrelated unit failed.
    state = (probe.stdout or probe.stderr).strip()
    if state in {"running", "degraded", "starting"}:
        return Availability(True, f"systemd --user timers ({state})")
    return Availability(False, f"the systemd user manager is not running (is-system-running: {state or 'unknown'})")


def linger_enabled(user: str | None = None) -> bool | None:
    """Whether user services keep running with nobody logged in.

    Without linger, every scheduled dispatch silently dies at logout — the exact
    condition an away-mode schedule runs under. ``None`` when it cannot be read.
    """
    if not shutil.which("loginctl"):
        return None
    try:
        probe = subprocess.run(
            ["loginctl", "show-user", user or os.environ.get("USER", ""), "-p", "Linger"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if probe.returncode != 0:
        return None
    return probe.stdout.strip().endswith("=yes")


def parse_when(text: str, *, now: datetime | None = None) -> datetime:
    """A target time from ``+90m`` / ``+2h`` or an absolute ``2026-07-22 09:00``.

    Absolute forms go through ``datetime.fromisoformat``, which takes both
    ``YYYY-MM-DD HH:MM[:SS]`` and RFC3339. Deliberately no natural language: a
    misread "5:30 tomorrow" fires a real worker at the wrong hour, and the parser
    that guesses is the one that guesses wrong unattended.
    """
    now = now or datetime.now().astimezone()
    raw = (text or "").strip()
    if not raw:
        raise ScheduleError("no time given: pass --at '+2h' or --at '2026-07-22 09:00'")

    relative = _RELATIVE_RE.match(raw)
    if relative:
        amount, unit = int(relative.group(1)), relative.group(2).lower()
        if amount <= 0:
            raise ScheduleError(f"--at {raw!r} must be a positive offset")
        return now + timedelta(**{_RELATIVE_UNITS[unit]: amount})

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ScheduleError(
            f"could not read --at {raw!r}. Use an offset (+30m, +2h, +1d) or an "
            "absolute time (2026-07-22 09:00, or RFC3339)."
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    if parsed <= now:
        raise ScheduleError(f"--at {raw!r} is in the past ({parsed:%Y-%m-%d %H:%M}); nothing would fire")
    return parsed


def unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def _systemctl(*args: str, timeout: float = 20.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["systemctl", "--user", *args], capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ScheduleError(f"systemctl failed: {exc}") from exc


def _escape(value: str) -> str:
    """systemd unit values are newline-delimited; a newline would inject a directive."""
    return value.replace("\n", " ").replace("\r", " ").strip()


def _service_unit(
    *, description: str, command: tuple[str, ...], cwd: Path, on_failure: str | None = None,
) -> str:
    # PATH is carried in explicitly: a systemd user unit starts with a minimal
    # environment, and the worker this launches has to find the `claude`/`codex`
    # binary. Without this the dispatch fires and fails at the last inch.
    unit_section = [
        "[Unit]",
        f"Description=Horus scheduled dispatch: {_escape(description)}",
    ]
    if on_failure:
        # ANY non-zero launch exit escalates, uniformly. This lives at the unit level
        # on purpose: an argparse error (`unrecognized arguments`) exits 2 BEFORE the
        # Python handler runs, so an in-handler try/except cannot catch it. `OnFailure=`
        # fires the escalation unit on the service entering `failed`, whatever the cause.
        unit_section.append(f"OnFailure={on_failure}")
    return "\n".join([
        *unit_section,
        "",
        "[Service]",
        "Type=oneshot",
        f"WorkingDirectory={cwd}",
        f"Environment=PATH={_escape(os.environ.get('PATH', ''))}",
        "ExecStart=" + " ".join(_quote(part) for part in command),
        "",
    ])


def _notify_unit(*, description: str, command: tuple[str, ...], cwd: Path) -> str:
    """The `OnFailure=` handler that escalates a pre-launch dispatch death.

    A plain oneshot that runs `horus notify escalate` — which is best-effort and never
    raises, so with no sink configured it is a silent no-op and the failed dispatch
    behaves exactly as it does today.
    """
    return "\n".join([
        "[Unit]",
        f"Description=Horus scheduled dispatch launch-failure escalation: {_escape(description)}",
        "",
        "[Service]",
        "Type=oneshot",
        f"WorkingDirectory={cwd}",
        f"Environment=PATH={_escape(os.environ.get('PATH', ''))}",
        "ExecStart=" + " ".join(_quote(part) for part in command),
        "",
    ])


def _timer_unit(*, description: str, when: datetime) -> str:
    return "\n".join([
        "[Unit]",
        f"Description=Horus scheduled dispatch timer: {_escape(description)}",
        "",
        "[Timer]",
        f"OnCalendar={when:%Y-%m-%d %H:%M:%S}",
        f"AccuracySec={ACCURACY}",
        # Fire a slot missed while the machine was suspended or powered off, rather
        # than silently skipping the whole dispatch.
        "Persistent=true",
        # One-shot: a card is done once. The timer deactivates after it elapses.
        "RemainAfterElapse=no",
        "",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ])


def _quote(part: str) -> str:
    """Quote one ExecStart argument for systemd's own parser."""
    if part and not re.search(r"[\s\"'\\$%]", part):
        return part
    return '"' + part.replace("\\", "\\\\").replace('"', '\\"') + '"'


def create(
    *,
    when: datetime,
    command: tuple[str, ...],
    description: str,
    cwd: Path | None = None,
    card: str | None = None,
    launcher: tuple[str, ...] = (sys.executable, "-m", "horus"),
) -> Schedule:
    """Write and enable a one-shot timer for ``command``. Raises ``ScheduleError``.

    Every generated dispatch also gets an ``OnFailure=`` escalation unit: any non-zero
    launch exit (including an argparse error that never reaches the Python handler)
    fires ``horus notify escalate`` so a pre-launch death cannot die silently in the
    journal. With no sink configured that escalation is a best-effort no-op.
    """
    ready = availability()
    if not ready.ok:
        raise ScheduleError(f"cannot schedule here: {ready.reason}")
    if not command:
        raise ScheduleError("nothing to schedule: no command given")

    ident = uuid.uuid4().hex[:8]
    directory = unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    resolved_cwd = cwd or Path.cwd()
    service = directory / f"{UNIT_PREFIX}{ident}.service"
    timer = directory / f"{UNIT_PREFIX}{ident}.timer"
    notify_unit_name = f"{UNIT_PREFIX}{ident}-notify.service"
    notify_service = directory / notify_unit_name

    escalate_command = (
        *launcher, "notify", "escalate",
        "--event", notify.DISPATCH_LAUNCH_FAILED,
        "--unit", f"{UNIT_PREFIX}{ident}.service",
    )
    if card:
        escalate_command += ("--card", card)

    service.write_text(
        _service_unit(
            description=description, command=command, cwd=resolved_cwd,
            on_failure=notify_unit_name,
        ),
        encoding="utf-8",
    )
    notify_service.write_text(
        _notify_unit(description=description, command=escalate_command, cwd=resolved_cwd),
        encoding="utf-8",
    )
    timer.write_text(_timer_unit(description=description, when=when), encoding="utf-8")

    reload_result = _systemctl("daemon-reload")
    if reload_result.returncode != 0:
        _remove_units(ident)
        raise ScheduleError(f"systemd rejected the new units: {_stderr(reload_result)}")
    # `enable` (not just start) so the timer is re-armed after a reboot.
    enable = _systemctl("enable", "--now", timer.name)
    if enable.returncode != 0:
        _remove_units(ident)
        _systemctl("daemon-reload")
        raise ScheduleError(f"could not arm the timer: {_stderr(enable)}")
    return Schedule(
        id=ident,
        description=description,
        when=f"{when:%Y-%m-%d %H:%M:%S}",
        command=tuple(command),
        next_run=f"{when:%Y-%m-%d %H:%M:%S}",
    )


def _stderr(result: subprocess.CompletedProcess) -> str:
    return (result.stderr or result.stdout or "").strip() or "no detail given"


def _remove_units(ident: str) -> None:
    for suffix in (".service", ".timer", ".halt", "-notify.service"):
        (unit_dir() / f"{UNIT_PREFIX}{ident}{suffix}").unlink(missing_ok=True)
    # Drop Persistent's stamp too: it outlives the units, and a recycled id would
    # otherwise read as already-fired.
    stamp_path(f"{UNIT_PREFIX}{ident}").unlink(missing_ok=True)


def _unquote_exec(raw: str) -> tuple[str, ...]:
    parts, current, quoted, escape = [], "", False, False
    for char in raw:
        if escape:
            current += char
            escape = False
        elif char == "\\":
            escape = True
        elif char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            if current:
                parts.append(current)
                current = ""
        else:
            current += char
    if current:
        parts.append(current)
    return tuple(parts)


def _read_directive(text: str, key: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            return stripped[len(key) + 1:].strip()
    return ""


def load_all() -> list[Schedule]:
    """Every Horus schedule this machine knows about, soonest first.

    Reconstructed from the unit files (which systemd reads too — one source of
    truth), enriched with systemd's live view of what has fired.
    """
    directory = unit_dir()
    if not directory.is_dir():
        return []
    schedules: list[Schedule] = []
    for timer_path in sorted(directory.glob(f"{UNIT_PREFIX}*.timer")):
        ident = timer_path.stem[len(UNIT_PREFIX):]
        service_path = directory / f"{UNIT_PREFIX}{ident}.service"
        try:
            timer_text = timer_path.read_text(encoding="utf-8")
            service_text = service_path.read_text(encoding="utf-8") if service_path.exists() else ""
        except OSError:
            continue
        description = _read_directive(timer_text, "Description")
        description = description.split(": ", 1)[-1] if ": " in description else description
        when = _read_directive(timer_text, "OnCalendar")
        halt_reason = _read_halt(ident)
        if halt_reason is not None:
            # A halted timer is disabled, so its live NextElapse is gone — reporting
            # it through _live_state would mislabel it "fired". Present it as halted.
            live = {"next_run": None, "fired": False}
        else:
            live = _live_state(f"{UNIT_PREFIX}{ident}", when)
        schedules.append(Schedule(
            id=ident,
            description=description,
            when=when,
            command=_unquote_exec(_read_directive(service_text, "ExecStart")),
            halted=halt_reason is not None,
            halt_reason=halt_reason,
            **live,
        ))
    return sorted(schedules, key=lambda s: (s.fired, s.when))


def _halt_marker(ident: str) -> Path:
    return unit_dir() / f"{UNIT_PREFIX}{ident}.halt"


def _read_halt(ident: str) -> str | None:
    """The halt reason for ``ident``, or ``None`` when it is not halted."""
    marker = _halt_marker(ident)
    if not marker.exists():
        return None
    try:
        return marker.read_text(encoding="utf-8").strip() or "halted"
    except OSError:
        return "halted"


def halt(ident: str, reason: str) -> Schedule | None:
    """Andon: disarm a pending scheduled dispatch so it cannot fire, but keep its
    units so the halt stays visible in `horus schedule list`. Idempotent; ``None``
    when no such (unique) schedule exists. Only touches ``horus-sched-`` units.
    """
    matches = [s for s in load_all() if s.id == ident or s.id.startswith(ident)]
    if len(matches) != 1:
        return None
    found = matches[0]
    # `disable --now` stops the running timer AND removes it from timers.target.wants,
    # so it also stays disarmed across a reboot — the safety-critical part.
    _systemctl("disable", "--now", f"{found.unit}.timer")
    _halt_marker(found.id).write_text(reason.strip() or "halted", encoding="utf-8")
    _systemctl("daemon-reload")
    return Schedule(
        id=found.id, description=found.description, when=found.when,
        command=found.command, next_run=None, fired=False,
        halted=True, halt_reason=reason.strip() or "halted",
    )


def release(ident: str) -> Schedule | None:
    """Andon inverse: re-arm a halted dispatch once its base is fixed.

    The exact undo of :func:`halt` — clears the ``.halt`` marker and re-enables
    the timer so it fires again on its original ``OnCalendar``. Returns ``None``
    when no such (unique) schedule exists OR when it is not halted (a cancelled
    dispatch has no units left to match, and a fired/pending one has nothing to
    release — only an andon-halted dispatch is releasable, mirroring the card's
    contract). Only touches ``horus-sched-`` units.
    """
    matches = [s for s in load_all() if s.id == ident or s.id.startswith(ident)]
    if len(matches) != 1:
        return None
    found = matches[0]
    if not found.halted:
        return None
    # `enable --now` re-arms the timer AND restores it to timers.target.wants, so
    # it survives a reboot again — the exact inverse of halt's `disable --now`.
    _systemctl("enable", "--now", f"{found.unit}.timer")
    try:
        _halt_marker(found.id).unlink()
    except OSError:
        pass
    _systemctl("daemon-reload")
    live = _live_state(found.unit, found.when)
    return Schedule(
        id=found.id, description=found.description, when=found.when,
        command=found.command, halted=False, halt_reason=None, **live,
    )


def stamp_path(unit: str) -> Path:
    """Where ``Persistent=true`` records that a timer last fired.

    This is systemd's own durable record — the thing it consults to decide whether to
    catch up a slot missed while the machine was off — so it is also the honest answer
    to "has this one-shot run yet?".
    """
    return Path.home() / ".local" / "share" / "systemd" / "timers" / f"stamp-{unit}.timer"


def _live_state(unit_stem: str, when: str) -> dict:
    """When a timer fires next, and whether it already has.

    Every obvious signal here is a trap, each verified live on 2026-07-17:

    - the timer's ``LastTriggerUSecRealtime`` reads EMPTY once a one-shot elapses
      (systemd drops the runtime state), and ``ActiveState`` still reads ``active``
      right after firing — a list built on either calls a fired dispatch "pending";
    - the Persistent stamp file EXISTS from the moment the timer is enabled, so its
      presence proves nothing. Its **mtime** is the real signal: systemd advances it
      to the trigger time, and unlike the service's runtime record it survives a
      reboot.

    So: a next elapse means pending. Otherwise it fired if the stamp has advanced to
    the scheduled time, or the service still remembers running.
    """
    next_run = None
    result = _systemctl("show", f"{unit_stem}.timer", "-p", "NextElapseUSecRealtime")
    if result.returncode == 0:
        next_run = result.stdout.split("=", 1)[-1].strip() or None
    if next_run:
        return {"next_run": next_run, "fired": False}

    stamp = stamp_path(unit_stem)
    if stamp.exists() and when:
        try:
            scheduled = datetime.strptime(when, "%Y-%m-%d %H:%M:%S")
            if datetime.fromtimestamp(stamp.stat().st_mtime) >= scheduled:
                return {"next_run": None, "fired": True}
        except (ValueError, OSError):
            pass
    service = _systemctl("show", f"{unit_stem}.service", "-p", "ExecMainStartTimestamp")
    fired = service.returncode == 0 and bool(service.stdout.split("=", 1)[-1].strip())
    return {"next_run": None, "fired": fired}


def unit_exit_detail(unit: str) -> str:
    """A short human reason ``unit`` failed: its exit status and systemd result.

    Read from systemd's retained record of the failed unit (kept in the ``failed``
    state until reset), so the escalation can name the exit code even for an argparse
    error that exited before any Python handler ran. Best-effort — never raises.
    """
    try:
        result = _systemctl("show", unit, "-p", "ExecMainStatus", "-p", "Result")
    except ScheduleError:
        return "exit status unavailable"
    if result.returncode != 0:
        return "exit status unavailable"
    fields: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    parts = []
    status = fields.get("ExecMainStatus", "")
    if status:
        parts.append(f"exit status {status}")
    outcome = fields.get("Result", "")
    if outcome and outcome != "success":
        parts.append(f"result: {outcome}")
    return ", ".join(parts) or "exit status unavailable"


def cancel(ident: str) -> Schedule | None:
    """Disarm and delete a schedule. ``None`` when no such schedule exists.

    Only ever touches units this module created (the ``horus-sched-`` prefix), so a
    mistyped id can never disable an unrelated user timer.
    """
    matches = [s for s in load_all() if s.id == ident or s.id.startswith(ident)]
    if len(matches) != 1:
        return None
    found = matches[0]
    _systemctl("disable", "--now", f"{found.unit}.timer")
    _remove_units(found.id)
    _systemctl("daemon-reload")
    return found


# --------------------------------------------------------------------------- #
# Persistent steering listener — a long-running `horus notify listen` service.
#
# The scheduler above installs one-shot TIMERS; this installs one long-running
# SERVICE (the inbound Telegram poller) with the SAME systemd --user posture, so
# the steering channel survives a terminal close and — under linger — a reboot,
# which is the trip-mode requirement (`horus notify listen --for`/interactive
# dies with its terminal). getUpdates is single-consumer, so there is exactly ONE
# such unit per machine: a second install is refused with the live one named.
# --------------------------------------------------------------------------- #

LISTEN_UNIT = "horus-notify-listen"


def _listen_service_unit(*, command: tuple[str, ...], cwd: Path) -> str:
    return "\n".join([
        "[Unit]",
        "Description=Horus notify listen — inbound Telegram steering channel",
        "",
        "[Service]",
        "Type=simple",
        f"WorkingDirectory={cwd}",
        f"Environment=PATH={_escape(os.environ.get('PATH', ''))}",
        # Unbuffered so the poller's status/errors reach the journal live — this is a
        # 24/7 service the owner debugs remotely (`journalctl --user -u …`).
        "Environment=PYTHONUNBUFFERED=1",
        "ExecStart=" + " ".join(_quote(part) for part in command),
        # The poller is best-effort and self-heals a transport blip; a crash should
        # bring it back, not leave the owner steering-blind for the rest of the trip.
        "Restart=always",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])


def listen_service_installed() -> bool:
    """Whether the persistent listen unit file exists on disk."""
    return (unit_dir() / f"{LISTEN_UNIT}.service").exists()


# systemd states that mean a poller is (or is about to be) consuming getUpdates.
# "activating" matters: a Type=simple unit sits there for the first moment after
# `enable --now`, and a second install racing that window would still be a rival
# consumer — so it must be refused too (observed live 2026-07-18).
_LISTEN_LIVE_STATES = frozenset({"active", "activating", "reloading"})


def listen_service_active() -> bool:
    """Whether the persistent listen service is running or coming up."""
    if not listen_service_installed():
        return False
    try:
        state = _systemctl("is-active", f"{LISTEN_UNIT}.service")
    except ScheduleError:
        return False
    return state.stdout.strip() in _LISTEN_LIVE_STATES


def _absolute_exec(command: tuple[str, ...]) -> tuple[str, ...]:
    """Resolve the command's executable to an ABSOLUTE path.

    systemd resolves a bare ``ExecStart`` name against the manager's own
    compiled-in PATH (system bin dirs only) — NOT the unit's ``Environment=PATH``
    — so ``ExecStart=horus …`` fails ``203/EXEC`` wherever ``horus`` lives in
    ``~/.local/bin`` (the normal `uv tool install` location). Bake the absolute
    path so the unit runs regardless (observed live 2026-07-18; escaped in
    v0.0.62 because unit tests stub systemctl and never exec the unit)."""
    resolved = shutil.which(command[0])
    return (resolved, *command[1:]) if resolved else command


def install_listen_service(*, command: tuple[str, ...], cwd: Path) -> None:
    """Write and enable the persistent listen service. Refuses a second one.

    getUpdates is single-consumer: a second poller fights the first for every
    update (Telegram 409s one of them), so an already-active service is named and
    the install refused rather than starting a rival. Raises ``ScheduleError`` on
    an unavailable systemd or a failed start."""
    ready = availability()
    if not ready.ok:
        raise ScheduleError(ready.reason)
    if listen_service_active():
        raise ScheduleError(
            f"a listen service is already running ({LISTEN_UNIT}.service) — getUpdates is "
            "single-consumer; stop it first with `horus notify listen --stop`"
        )
    directory = unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{LISTEN_UNIT}.service").write_text(
        _listen_service_unit(command=_absolute_exec(command), cwd=cwd), encoding="utf-8"
    )
    _systemctl("daemon-reload")
    enable = _systemctl("enable", "--now", f"{LISTEN_UNIT}.service")
    if enable.returncode != 0:
        raise ScheduleError(f"could not start the listen service: {_stderr(enable)}")


def restart_listen_service() -> bool:
    """Restart the listen service so it picks up an upgraded pinned CLI. ``False``
    when none is installed. The service runs the pinned ``~/.local/bin/horus``, so
    after a `uv tool install --force --refresh` (or `deploy-hosted.sh`) it keeps
    running the OLD process until restarted — call this to adopt the new code."""
    if not listen_service_installed():
        return False
    _systemctl("restart", f"{LISTEN_UNIT}.service")
    return True


def remove_listen_service() -> bool:
    """Stop and remove the persistent listen service. ``False`` when none is installed."""
    if not listen_service_installed():
        return False
    _systemctl("disable", "--now", f"{LISTEN_UNIT}.service")
    try:
        (unit_dir() / f"{LISTEN_UNIT}.service").unlink()
    except OSError:
        pass
    _systemctl("daemon-reload")
    return True


# --------------------------------------------------------------------------- #
# Per-account keep-warm services — a long-running `horus warmup --keep` loop.
#
# Same persistent systemd --user posture as the listener, but there is ONE unit
# PER ACCOUNT (the loop keeps a single Claude account's 5h window open), so unlike
# the single-consumer listener a second install for a DIFFERENT account is allowed
# — the unit name carries the account alias. Claude-only (Codex has no 5h window).
# --------------------------------------------------------------------------- #

KEEPWARM_PREFIX = "horus-keepwarm-"
_UNIT_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]")


def keepwarm_unit(account: str) -> str:
    """The unit basename for an account's keep-warm service. The alias is
    sanitised to systemd's allowed unit-name character set so an odd alias can
    never produce an unwritable (or ambiguous) unit path."""
    return f"{KEEPWARM_PREFIX}{_UNIT_SAFE_RE.sub('-', account)}"


def _keepwarm_service_unit(*, account: str, command: tuple[str, ...], cwd: Path) -> str:
    return "\n".join([
        "[Unit]",
        f"Description=Horus keep-warm — Claude account {_escape(account)} 5h window",
        "",
        "[Service]",
        "Type=simple",
        f"WorkingDirectory={cwd}",
        f"Environment=PATH={_escape(os.environ.get('PATH', ''))}",
        # Unbuffered so each warm cycle reaches the journal live (same 24/7 remote-
        # debug reason as the listener).
        "Environment=PYTHONUNBUFFERED=1",
        "ExecStart=" + " ".join(_quote(part) for part in command),
        # The loop sleeps ~5h between warms; a crash should bring it back rather than
        # silently leave the window to lapse.
        "Restart=always",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])


def keepwarm_service_installed(account: str) -> bool:
    """Whether a keep-warm unit for ``account`` exists on disk."""
    return (unit_dir() / f"{keepwarm_unit(account)}.service").exists()


def keepwarm_service_active(account: str) -> bool:
    """Whether ``account``'s keep-warm service is running or coming up."""
    if not keepwarm_service_installed(account):
        return False
    try:
        state = _systemctl("is-active", f"{keepwarm_unit(account)}.service")
    except ScheduleError:
        return False
    return state.stdout.strip() in _LISTEN_LIVE_STATES


def install_keepwarm_service(*, account: str, command: tuple[str, ...], cwd: Path) -> None:
    """Write and enable ``account``'s keep-warm service. Idempotent re-install is
    fine (one unit per account). Raises ``ScheduleError`` on an unavailable systemd
    or a failed start."""
    ready = availability()
    if not ready.ok:
        raise ScheduleError(ready.reason)
    directory = unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{keepwarm_unit(account)}.service").write_text(
        _keepwarm_service_unit(account=account, command=_absolute_exec(command), cwd=cwd),
        encoding="utf-8",
    )
    _systemctl("daemon-reload")
    enable = _systemctl("enable", "--now", f"{keepwarm_unit(account)}.service")
    if enable.returncode != 0:
        raise ScheduleError(f"could not start the keep-warm service: {_stderr(enable)}")


def restart_keepwarm_service(account: str) -> bool:
    """Restart ``account``'s keep-warm service so it adopts an upgraded pinned CLI.
    ``False`` when none is installed."""
    if not keepwarm_service_installed(account):
        return False
    _systemctl("restart", f"{keepwarm_unit(account)}.service")
    return True


def remove_keepwarm_service(account: str) -> bool:
    """Stop and remove ``account``'s keep-warm service. ``False`` when none is installed."""
    if not keepwarm_service_installed(account):
        return False
    _systemctl("disable", "--now", f"{keepwarm_unit(account)}.service")
    try:
        (unit_dir() / f"{keepwarm_unit(account)}.service").unlink()
    except OSError:
        pass
    _systemctl("daemon-reload")
    return True


def keepwarm_active_accounts() -> dict[str, bool]:
    """Every account with a keep-warm unit on disk → whether it is currently active.
    Backs the Control pane's per-account ``[x]/[ ]`` toggles."""
    result: dict[str, bool] = {}
    for path in sorted(unit_dir().glob(f"{KEEPWARM_PREFIX}*.service")):
        alias = path.stem[len(KEEPWARM_PREFIX):]
        result[alias] = keepwarm_service_active(alias)
    return result


# --------------------------------------------------------------------------- #
# CLIProxyAPI service (vision-branch-x4 stage 1) — a long-running Docker proxy.
#
# Same persistent systemd --user posture as the listener, but the ExecStart runs a
# `docker run` (Horus owns no runtime — it orchestrates an external proxy). One unit
# per machine. `ExecStartPre` force-removes a stale same-named container so a crash
# without cleanup never blocks the restart.
# --------------------------------------------------------------------------- #

PROXY_UNIT = "horus-cliproxy"


def _proxy_service_unit(*, command: tuple[str, ...], docker: str) -> str:
    return "\n".join([
        "[Unit]",
        "Description=Horus CLIProxyAPI — local model/harness proxy (optional integration)",
        "",
        "[Service]",
        "Type=simple",
        f"Environment=PATH={_escape(os.environ.get('PATH', ''))}",
        "Environment=PYTHONUNBUFFERED=1",
        # Clear a stale same-named container left by an unclean stop (leading `-` =
        # ignore failure when none exists), so the restart never fails "name in use".
        f"ExecStartPre=-{docker} rm -f {PROXY_UNIT}",
        "ExecStart=" + " ".join(_quote(part) for part in command),
        # `systemctl stop` kills the `docker run` client but the daemon can keep the
        # --rm container alive; force-remove it on stop so teardown is real.
        f"ExecStopPost=-{docker} rm -f {PROXY_UNIT}",
        "Restart=always",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])


def proxy_service_installed() -> bool:
    return (unit_dir() / f"{PROXY_UNIT}.service").exists()


def proxy_service_active() -> bool:
    if not proxy_service_installed():
        return False
    try:
        state = _systemctl("is-active", f"{PROXY_UNIT}.service")
    except ScheduleError:
        return False
    return state.stdout.strip() in _LISTEN_LIVE_STATES


def install_proxy_service(*, command: tuple[str, ...]) -> None:
    """Write and enable the proxy service. ``command`` is the full ``docker run …``
    argv; its executable is resolved to an absolute path (the #322 203/EXEC lesson).
    Raises ``ScheduleError`` on unavailable systemd or a failed start."""
    ready = availability()
    if not ready.ok:
        raise ScheduleError(ready.reason)
    resolved = _absolute_exec(command)
    docker = resolved[0]
    directory = unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{PROXY_UNIT}.service").write_text(
        _proxy_service_unit(command=resolved, docker=docker), encoding="utf-8"
    )
    _systemctl("daemon-reload")
    enable = _systemctl("enable", "--now", f"{PROXY_UNIT}.service")
    if enable.returncode != 0:
        raise ScheduleError(f"could not start the proxy service: {_stderr(enable)}")


def remove_proxy_service() -> bool:
    """Stop and remove the proxy service. ``False`` when none is installed."""
    if not proxy_service_installed():
        return False
    _systemctl("disable", "--now", f"{PROXY_UNIT}.service")
    try:
        (unit_dir() / f"{PROXY_UNIT}.service").unlink()
    except OSError:
        pass
    _systemctl("daemon-reload")
    return True
