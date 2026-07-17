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


def _service_unit(*, description: str, command: tuple[str, ...], cwd: Path) -> str:
    # PATH is carried in explicitly: a systemd user unit starts with a minimal
    # environment, and the worker this launches has to find the `claude`/`codex`
    # binary. Without this the dispatch fires and fails at the last inch.
    return "\n".join([
        "[Unit]",
        f"Description=Horus scheduled dispatch: {_escape(description)}",
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
) -> Schedule:
    """Write and enable a one-shot timer for ``command``. Raises ``ScheduleError``."""
    ready = availability()
    if not ready.ok:
        raise ScheduleError(f"cannot schedule here: {ready.reason}")
    if not command:
        raise ScheduleError("nothing to schedule: no command given")

    ident = uuid.uuid4().hex[:8]
    directory = unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    service = directory / f"{UNIT_PREFIX}{ident}.service"
    timer = directory / f"{UNIT_PREFIX}{ident}.timer"
    service.write_text(
        _service_unit(description=description, command=command, cwd=cwd or Path.cwd()),
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
    for suffix in (".service", ".timer", ".halt"):
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
