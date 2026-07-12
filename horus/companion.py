"""Tiny native companion window for Horus."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path, PureWindowsPath
from typing import Any, NamedTuple
from urllib.error import URLError
from urllib.request import urlopen

from horus import __version__
from horus import config as _config


class DashboardProcess(NamedTuple):
    url: str
    started: bool
    process: subprocess.Popen[str] | None
    error: str | None = None  # definite startup failure (child died before /health)


def _dashboard_command(host: str, port: int, *, exposed: bool = False) -> list[str]:
    """Command for a fresh dashboard process from this installed CLI."""
    command = [sys.executable, "-m", "horus", "dashboard", "--host", host, "--port", str(port)]
    if exposed:
        command.append("--exposed")
    return command


# --------------------------------------------------------------------------- #
# Startup logs — the app's GUI processes run windowless (pythonw / DEVNULL), so
# a startup crash used to vanish. Child output and companion events land in
# ~/.horus/logs/ and failures point the user at `horus doctor`.
# --------------------------------------------------------------------------- #

_LOG_MAX_BYTES = 512 * 1024


def startup_log_path(name: str) -> Path:
    return _config.config_dir() / "logs" / f"{name}.log"


def _open_startup_log(name: str):
    """Append handle to ``~/.horus/logs/<name>.log`` (rotated once when oversized),
    or None when the filesystem refuses — logging must never block startup."""
    try:
        path = startup_log_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > _LOG_MAX_BYTES:
            path.replace(path.with_name(f"{name}.log.1"))
        return path.open("a", encoding="utf-8")
    except OSError:
        return None


def _log_line(name: str, message: str) -> None:
    log = _open_startup_log(name)
    if log is None:
        return
    with log:
        log.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} [horus {__version__}] {message}\n")


def log_companion_event(message: str) -> None:
    """Record a companion lifecycle event/failure (visible even under pythonw)."""
    _log_line("companion", message)


# Single-instance lock. Binding a fixed localhost port is a cross-platform mutex
# the OS releases on process death (no stale-PID files to reap).
# ponytail: if some unrelated process grabs this port, we'd wrongly think a
# companion is running — picked an uncommon port to make that unlikely.
SINGLETON_PORT = 8764
MASCOT_TARGET_HEIGHT = 120


def acquire_singleton_lock(port: int = SINGLETON_PORT) -> socket.socket | None:
    """Hold a process-lifetime lock, or None if another companion already holds it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
    except OSError:
        sock.close()
        return None
    return sock


def dashboard_url(host: str = "127.0.0.1", port: int = 8765) -> str:
    return f"http://{host}:{port}"


def dashboard_is_live(url: str, *, timeout: float = 0.25) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, TimeoutError, URLError, ValueError):
        return False


def _wait_dashboard_live(url: str, process: subprocess.Popen[str], *, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if dashboard_is_live(url):
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.05)
    return dashboard_is_live(url)


def dashboard_identity(url: str, *, timeout: float = 0.5) -> dict[str, Any] | None:
    """The `/health` identity of a live server, or None (pre-/health build, foreign
    server, or unreachable)."""
    try:
        with urlopen(url.rstrip("/") + "/health", timeout=timeout) as response:
            data = json.load(response)
    except (OSError, TimeoutError, URLError, ValueError):
        return None
    if isinstance(data, dict) and data.get("app") == "horus-dashboard":
        return data
    return None


def _looks_like_horus_dashboard(url: str, *, timeout: float = 0.5) -> bool:
    """Heuristic for builds that predate `/health`: the index page brands itself."""
    try:
        with urlopen(url, timeout=timeout) as response:
            return b"Horus" in response.read(4096)
    except (OSError, TimeoutError, URLError, ValueError):
        return False


def _pid_listening_on(port: int) -> int | None:
    """Owning PID of the listener on ``port`` (Windows only — where the legacy
    orphan problem was observed; other platforms return None and skip the reap)."""
    if sys.platform != "win32":
        return None
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "TCP" and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
            try:
                return int(parts[4])
            except ValueError:
                continue
    return None


def _kill_pid_tree(pid: int, *, timeout: float = 3.0) -> None:
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=timeout, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        return
    try:
        os.kill(pid, 15)
    except OSError:
        pass


def _replace_stale_dashboard(url: str, port: int, *, timeout: float = 3.0) -> bool:
    """Terminate a *stale* Horus dashboard occupying the port; True when it did.

    A live server on the port used to be adopted unconditionally, so an orphan from
    an old launch kept serving its old in-memory build forever (observed: a 3-day-old
    PID surviving many quit/reopen cycles). Only a server that identifies as a Horus
    dashboard with a different ``__version__`` — or brands itself as Horus but
    predates ``/health`` — is killed; a foreign server is never touched."""
    identity = dashboard_identity(url)
    if identity is not None:
        if identity.get("version") == __version__:
            return False  # current build — adopting it is fine
        pid = identity.get("pid")
    elif _looks_like_horus_dashboard(url):
        pid = _pid_listening_on(port)  # legacy Horus build with no /health
    else:
        return False  # not a Horus dashboard — never kill a foreign server
    if not isinstance(pid, int) or pid <= 0:
        return False
    _kill_pid_tree(pid)
    deadline = time.monotonic() + timeout
    while dashboard_is_live(url) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not dashboard_is_live(url)


def ensure_dashboard(
    host: str = "127.0.0.1", port: int = 8765, *, start: bool = True, exposed: bool = False,
) -> DashboardProcess:
    url = dashboard_url(host, port)
    if not start:
        return DashboardProcess(url, False, None)
    if dashboard_is_live(url) and not _replace_stale_dashboard(url, port):
        return DashboardProcess(url, False, None)

    # Child output goes to the startup log, not DEVNULL: when the dashboard dies
    # on startup (import error, port conflict, …) its traceback is the diagnosis.
    log = _open_startup_log("dashboard")
    if log is not None:
        log.write(
            f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} [horus {__version__}] "
            f"spawning dashboard on {host}:{port}\n"
        )
        log.flush()
    kwargs = {
        "stdout": log if log is not None else subprocess.DEVNULL,
        "stderr": subprocess.STDOUT if log is not None else subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "text": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    process = subprocess.Popen(
        _dashboard_command(host, port, exposed=exposed),
        **kwargs,
    )
    if log is not None:
        log.close()  # the child holds its own descriptor from here
    live = _wait_dashboard_live(url, process)
    error = None
    if not live and process.poll() is not None:
        # Definite failure: the child died before answering. (Not-live-but-running
        # is left alone — a slow start comes up late and the click path re-checks.)
        error = (
            f"Dashboard failed to start (exit code {process.returncode}).\n"
            f"Run `horus doctor machine`.\nDetails: {startup_log_path('dashboard')}"
        )
        _log_line("dashboard", f"dashboard exited with code {process.returncode} before answering /health")
    return DashboardProcess(url, True, process, error)


def reload_dashboard(host: str = "127.0.0.1", port: int = 8765, *, timeout: float = 3.0) -> tuple[bool, str]:
    """Replace one identified dashboard with a fresh process from this install.

    ``/health`` stays public even for an exposed dashboard, so this can preserve
    its launch property without touching the tunnel that points at its port.
    Foreign listeners are never stopped.
    """
    url = dashboard_url(host, port)
    identity = dashboard_identity(url)
    if identity is None or identity.get("app") != "horus-dashboard":
        return False, f"No Horus dashboard found at {url}."
    old_pid = identity.get("pid")
    if not isinstance(old_pid, int) or old_pid <= 0:
        return False, f"Dashboard at {url} did not provide a usable PID."
    exposed = identity.get("exposed") is True
    _kill_pid_tree(old_pid, timeout=timeout)

    # An app supervisor may already have replaced its child. In that case it is
    # the correct fresh process, and starting another one would only race it.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = dashboard_identity(url)
        if current is None:
            break
        if current.get("pid") != old_pid:
            return True, f"Dashboard reloaded at {url} (pid {old_pid} -> {current.get('pid')})."
        time.sleep(0.05)

    fresh = ensure_dashboard(host, port, exposed=exposed)
    if fresh.error:
        return False, fresh.error
    current = dashboard_identity(url)
    if current is None or current.get("pid") == old_pid:
        return False, f"Dashboard at {url} did not come back after reload."
    return True, f"Dashboard reloaded at {url} (pid {old_pid} -> {current.get('pid')})."


def respawn_dashboard_if_needed(
    dashboard: DashboardProcess | None, *, host: str, port: int,
) -> DashboardProcess | None:
    """Replace a dead child owned by ``horus app``; adopted servers stay untouched."""
    if dashboard is None or not dashboard.started or dashboard.process is None:
        return dashboard
    if dashboard.process.poll() is None:
        return dashboard
    return ensure_dashboard(host, port)


def ensure_dashboard_for_open(
    current: DashboardProcess,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    start: bool = True,
) -> DashboardProcess:
    """Return a live dashboard before opening the browser.

    The companion can outlive the dashboard child it spawned. A click/open should
    repair that state instead of sending the browser to a dead localhost URL.
    """
    if dashboard_is_live(current.url) or not start:
        return current
    stop_dashboard(current)
    return ensure_dashboard(host, port, start=start)


def _terminate_process_tree(process: subprocess.Popen[str], *, timeout: float = 2.0) -> None:
    """Terminate ``process`` and any children it spawned.

    Windows virtualenv launchers can leave the real ``pythonw.exe`` child alive if
    only the immediate ``Popen`` handle is terminated. ``taskkill /T`` is the
    platform tool that reaps that whole tree; other platforms keep the previous
    direct terminate/kill behavior.
    """
    if sys.platform == "win32" and getattr(process, "pid", None):
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
            try:
                process.wait(timeout=timeout)
            except (OSError, subprocess.TimeoutExpired):
                pass
            return
        except (OSError, subprocess.TimeoutExpired):
            pass

    try:
        process.terminate()
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            pass
    except OSError:
        pass


def stop_dashboard(dashboard: DashboardProcess, *, timeout: float = 2.0) -> None:
    """Terminate a dashboard server *this* companion spawned, so it doesn't outlive
    the mascot and pile up as an orphan. No-op when the dashboard was reused (an
    existing one was already live) or none was started."""
    if dashboard.started and dashboard.process is not None:
        _terminate_process_tree(dashboard.process, timeout=timeout)


def relaunch_without_console() -> bool:
    """On Windows, re-exec the current ``horus`` invocation under ``pythonw.exe`` so
    the always-on-top companion runs with no console window attached.

    ``horus app`` normally runs under console-subsystem ``python.exe``; because the
    Tk ``mainloop`` blocks for the whole session, that console window lingers for as
    long as the mascot is up. Spawning a detached ``pythonw.exe`` child and exiting
    the parent frees the launching terminal immediately.

    Returns ``True`` when a detached child was spawned (the caller should exit), and
    ``False`` when nothing was done and the companion should run inline.
    """
    if sys.platform != "win32":
        return False
    if os.environ.get("HORUS_DETACHED") == "1":
        # We are the detached child (or the user opted to keep the console).
        return False
    executable_name = PureWindowsPath(sys.executable).name
    if executable_name.lower() != "python.exe":
        # Already pythonw.exe (no console) or an unusual launcher — run inline.
        return False
    pythonw = PureWindowsPath(sys.executable).with_name("pythonw.exe")
    if not Path(str(pythonw)).is_file():
        return False

    env = dict(os.environ)
    env["HORUS_DETACHED"] = "1"
    # DETACHED_PROCESS exists only on the Windows subprocess module; resolve it
    # defensively so the call is exercisable under tests on other platforms.
    detached = getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        [str(pythonw), "-m", "horus", *sys.argv[1:]],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=detached,
        close_fds=True,
    )
    return True


# Chromium app-mode (`--app=`) remains available as an explicit opt-in. The
# lightweight default is a normal browser tab, because Chrome/Edge app windows still
# own the taskbar identity. PySide/pywebview/native shells are the upgrade path if
# we later want a true native window + taskbar icon.
def _flatpak_app(app_id: str) -> list[str] | None:
    flatpak = shutil.which("flatpak")
    if not flatpak:
        return None
    try:
        result = subprocess.run(
            [flatpak, "info", app_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    if result.returncode == 0:
        return [flatpak, "run", app_id]
    return None


def _app_browser() -> list[str] | None:
    for app_id in (
        "com.google.Chrome",
        "com.microsoft.Edge",
        "org.chromium.Chromium",
        "com.brave.Browser",
    ):
        argv = _flatpak_app(app_id)
        if argv:
            return argv
    for candidate in (
        shutil.which("msedge"),
        shutil.which("microsoft-edge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("brave-browser"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if candidate and Path(candidate).is_file():
            return [candidate]
    return None


def dashboard_profile_dir() -> Path:
    """Dedicated Chromium profile for the owned dashboard window.

    A separate ``--user-data-dir`` gives Horus its *own* browser instance: a window
    we can track by PID and reuse/raise on the next click instead of spawning a fresh
    tab in the user's everyday browser each time — and one we can close on quit without
    touching their main browser."""
    return Path.home() / ".horus" / "dashboard-profile"


def _app_window_argv(browser: list[str], url: str) -> list[str]:
    return [
        *browser,
        f"--app={url}",
        f"--user-data-dir={dashboard_profile_dir()}",
        "--window-size=1200,760",
    ]


def resolve_open_mode(*, app_window: bool = False, tab: bool = False, platform: str | None = None) -> str:
    """How the companion opens the dashboard: ``"owned"`` (dedicated app window we
    reuse) or ``"tab"`` (a normal browser tab).

    Owned is the default *only where we can reliably bring the window back to the
    front* on a later click — Windows, via ``launcher.focus_window_for_pid``. Off
    Windows there's no dependable cross-desktop raise (Wayland has no API), so the
    plain tab stays the default there. Explicit flags win: ``--tab`` forces a tab,
    ``--app-window`` forces owned."""
    if tab:
        return "tab"
    if app_window:
        return "owned"
    return "owned" if (platform or sys.platform) == "win32" else "tab"


def open_dashboard(url: str, *, app_window: bool = False) -> subprocess.Popen[str] | None:
    """Open the dashboard. Owned app-window mode launches a dedicated, trackable
    Chromium instance and returns its process (so the caller can reuse/raise/close it);
    tab mode opens a normal browser tab and returns None."""
    browser = _app_browser() if app_window else None
    if browser:
        kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        try:
            return subprocess.Popen(_app_window_argv(browser, url), **kwargs)
        except OSError:
            pass
    webbrowser.open(url, new=2)
    return None


def raise_dashboard_window(process: subprocess.Popen[str] | None) -> bool:
    """Best-effort: bring the owned dashboard window to the front. Full on Windows
    (``focus_window_for_pid``); a no-op elsewhere — but even there we never spawn a
    duplicate, the existing window simply stays put."""
    if process is None or process.poll() is not None:
        return False
    from horus import launcher
    return launcher.focus_window_for_pid(process.pid)


def reuse_or_open_dashboard(
    url: str, process: subprocess.Popen[str] | None, *, app_window: bool = False
) -> subprocess.Popen[str] | None:
    """Reuse an already-open owned window (raise it) instead of opening a duplicate;
    otherwise open a fresh one. Tab mode tracks nothing, so it always opens."""
    if app_window and process is not None and process.poll() is None:
        raise_dashboard_window(process)
        return process
    return open_dashboard(url, app_window=app_window)


def stop_browser(process: subprocess.Popen[str] | None, *, timeout: float = 2.0) -> None:
    """Close the owned dashboard window when the companion quits, so it doesn't linger
    as a stale window. Safe because the dedicated profile is Horus's own instance — it
    never touches the user's everyday browser. No-op in tab mode (process is None)."""
    if process is None or process.poll() is not None:
        return
    _terminate_process_tree(process, timeout=timeout)


def mascot_asset_path() -> Path:
    return Path(str(resources.files("horus").joinpath("assets", "mascot.png")))


def mascot_background_path() -> Path:
    return Path(str(resources.files("horus").joinpath("assets", "background_egypt.png")))


def mascot_frame_paths() -> list[Path]:
    names = ["mascot_idle_0.png", "mascot_idle_1.png", "mascot_idle_2.png", "mascot_blink.png"]
    return [Path(str(resources.files("horus").joinpath("assets", name))) for name in names]


def resolve_mascot_style(style: str = "auto", *, platform: str | None = None) -> str:
    """Resolve the platform default for the companion artwork style."""
    if style not in {"auto", "foreground", "layered"}:
        raise ValueError(f"unknown mascot style: {style}")
    if style != "auto":
        return style
    actual_platform = platform or sys.platform
    return "foreground" if actual_platform == "win32" else "layered"


# Worker badge: how often the registry is re-read, and how long a finished worker
# keeps showing as "awaiting review" before it stops counting as news.
WORKER_POLL_SECONDS = 2.5
WORKER_DONE_WINDOW_MINUTES = 240

_AGENT_LABELS = {"claude": "Claude", "codex": "Codex"}


def worker_status_lines(
    records,
    *,
    now: datetime | None = None,
    done_window_minutes: int = WORKER_DONE_WINDOW_MINUTES,
) -> list[str]:
    """One badge line per agent summarizing background worker sessions.

    ``running`` records always show. Terminal records show as "awaiting review"
    (exited/orphaned: the worker finished but nobody dismissed its output) or
    "failed" — and only within ``done_window_minutes`` of their last update, so
    ancient leftovers in the registry don't pin a stale badge forever. Empty list
    means: hide the badge.
    """
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.astimezone()  # naive caller-supplied "now" is local time
    counts: dict[str, dict[str, int]] = {}
    for record in records:
        if record.status == "running":
            bucket = "running"
        elif record.status in ("exited", "orphaned", "failed"):
            try:
                updated = datetime.fromisoformat(record.updated_at)
                if updated.tzinfo is None:
                    updated = updated.astimezone()  # legacy rows: naive local time
                stale = moment - updated > timedelta(minutes=done_window_minutes)
            except (TypeError, ValueError):
                continue
            if stale:
                continue
            bucket = "failed" if record.status == "failed" else "review"
        else:
            continue
        agent = counts.setdefault(record.agent, {"running": 0, "review": 0, "failed": 0})
        agent[bucket] += 1

    lines: list[str] = []
    for agent in sorted(counts):
        c = counts[agent]
        total = c["running"] + c["review"] + c["failed"]
        parts = [
            part
            for part in (
                f"{c['running']} running" if c["running"] else "",
                f"{c['review']} awaiting review" if c["review"] else "",
                f"{c['failed']} failed" if c["failed"] else "",
            )
            if part
        ]
        label = _AGENT_LABELS.get(agent, agent)
        if total == 1:
            lines.append(f"{label} — {parts[0]}")
        else:
            lines.append(f"{label} — {total} agents: {', '.join(parts)}")
    return lines


def run_close_check(project_root: Path, *, threshold: float = 90.0) -> tuple[str, str]:
    from horus import closure

    findings = closure.closure_status(project_root, usage_threshold=threshold)
    failing = [f for f in findings if f.level == "fail"]
    warnings = [f for f in findings if f.level == "warn"]
    if failing:
        return "fail", f"{len(failing)} issue(s), {len(warnings)} warning(s)"
    if warnings:
        return "warn", f"{len(warnings)} warning(s)"
    return "ok", "healthy"


def run_companion(
    project_root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    start_dashboard: bool = True,
    open_on_start: bool = False,
    open_mode: str = "tab",
    mascot_style: str = "auto",
    usage_threshold: float = 90.0,
) -> int:
    # These refusals also land in the companion log: under pythonw / a desktop
    # launcher there is no console, so a print alone is "the app won't open".
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        message = "Tkinter is not available; the Horus companion needs a desktop Python with Tk. Run `horus doctor machine`."
        print(message)
        log_companion_event(f"refusing to start: {message}")
        return 2
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        message = "No graphical display detected; run `horus app` from a Linux desktop session with DISPLAY or WAYLAND_DISPLAY set."
        print(message)
        log_companion_event(f"refusing to start: {message}")
        return 2

    lock = acquire_singleton_lock()
    if lock is None:
        print("Horus companion already running; not starting another.")
        return 0

    owned = open_mode == "owned"
    # Lock-guarded shared handles so the background pre-warm thread, the mascot
    # click, and the shutdown path agree on the dashboard process + browser window.
    state: dict[str, Any] = {"dashboard": None, "browser_proc": None}
    state_lock = threading.Lock()
    closing = threading.Event()
    # Startup-failure notice slot: written by ensure_open (any thread), drained by
    # the main-thread animate loop — Tk must never be touched off the main thread,
    # and animate must not contend on state_lock (a spawn holds it for seconds).
    notice: dict[str, str] = {}

    def ensure_open(open_browser: bool) -> None:
        """Spawn/locate the dashboard and optionally open (or raise) its window.
        Idempotent and safe from the pre-warm thread or the mascot click."""
        with state_lock:
            dash = state["dashboard"] or ensure_dashboard(host, port, start=start_dashboard)
            if open_browser:
                dash = ensure_dashboard_for_open(dash, host=host, port=port, start=start_dashboard)
                if dash.error is None:
                    state["browser_proc"] = reuse_or_open_dashboard(
                        dash.url, state["browser_proc"], app_window=owned
                    )
            state["dashboard"] = dash
        if dash.error:
            log_companion_event("surfacing dashboard startup failure to the user")
            notice["msg"] = dash.error

    # Pre-warm off the critical path: the mascot window appears immediately instead
    # of blocking on the dashboard coming live and (when pre-warming) the browser's
    # cold launch. The click handler reuses whatever this set up.
    threading.Thread(target=lambda: ensure_open(open_browser=open_on_start), daemon=True).start()

    def respawn_dashboard_child() -> None:
        """Keep the backend alive if the companion-owned child dies or is killed."""
        while not closing.wait(0.5):
            with state_lock:
                state["dashboard"] = respawn_dashboard_if_needed(
                    state["dashboard"], host=host, port=port,
                )

    threading.Thread(target=respawn_dashboard_child, daemon=True).start()

    # Worker badge: registry polled off the main thread (file IO + PID liveness
    # checks), rendered by the animate loop — same main-thread-only Tk rule as
    # `notice`. A damaged registry must never kill the poller: fall back to hidden.
    workers: dict[str, Any] = {"lines": [], "as_of": ""}

    def poll_workers() -> None:
        from horus.registry import Registry
        while True:
            try:
                reg = Registry.default()
                workers["lines"] = worker_status_lines(reg.all())
                workers["as_of"] = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
            except Exception as exc:  # noqa: BLE001 (badge is best-effort by design)
                log_companion_event(f"worker badge poll failed: {exc}")
                workers["lines"] = []
                workers["as_of"] = ""
            time.sleep(WORKER_POLL_SECONDS)

    threading.Thread(target=poll_workers, daemon=True).start()

    root = tk.Tk()
    root.title("Horus")
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    style = resolve_mascot_style(mascot_style)
    transparent_background = "#ff00ff" if style == "foreground" else "#0f1115"
    background = transparent_background
    root.configure(bg=background)
    if style == "foreground":
        try:
            root.attributes("-transparentcolor", transparent_background)
        except tk.TclError:
            pass

    full_frames = [tk.PhotoImage(file=str(path)) for path in mascot_frame_paths()]
    full_background = tk.PhotoImage(file=str(mascot_background_path())) if style == "layered" else None
    scale = max(1, max(frame.height() for frame in full_frames) // MASCOT_TARGET_HEIGHT)
    mascot_frames = [frame.subsample(scale, scale) for frame in full_frames]
    mascot_background = full_background.subsample(scale, scale) if full_background is not None else None
    width = max([frame.width() for frame in mascot_frames] + ([mascot_background.width()] if mascot_background else []))
    height = max([frame.height() for frame in mascot_frames] + ([mascot_background.height()] if mascot_background else []))
    root.geometry(f"{width}x{height}+80+80")

    canvas = tk.Canvas(root, width=width, height=height, bg=background, highlightthickness=0, bd=0)
    canvas.pack()

    menu = tk.Menu(root, tearoff=0)
    if mascot_background is not None:
        canvas.create_image(width // 2, height // 2, image=mascot_background)
    mascot_item = canvas.create_image(width // 2, height // 2, image=mascot_frames[0])
    status_item = canvas.create_rectangle(width - 18, height - 18, width - 8, height - 8, fill="#57d39a", outline="#ffffff")
    canvas.create_text(width - 13, height - 13, text="", fill="#ffffff")

    # Worker badge window: a small always-on-top strip that docks under the mascot,
    # shown only while there is something to say. Clicking it opens the dashboard
    # (Live sessions card) — the "take me to the agents" affordance.
    badge = tk.Toplevel(root)
    badge.withdraw()
    badge.overrideredirect(True)
    badge.attributes("-topmost", True)
    badge_label = tk.Label(
        badge,
        text="",
        justify="left",
        anchor="w",
        bg="#0f1115",
        fg="#e8e4da",
        padx=8,
        pady=4,
        borderwidth=1,
        relief="solid",
    )
    badge_label.pack()
    badge_shown = {"text": ""}

    drag: dict[str, int | bool] = {"x": 0, "y": 0, "root_x": 80, "root_y": 80, "moved": False}
    frame = {"n": 0}

    def set_status(color: str) -> None:
        canvas.itemconfigure(status_item, fill=color)

    def open_action(_event: object | None = None) -> None:
        # Reuse the owned window (raise it) instead of stacking another tab/window;
        # ensure_open handles the not-yet-pre-warmed case too.
        ensure_open(open_browser=True)

    def close_check_action() -> None:
        level, message = run_close_check(project_root, threshold=usage_threshold)
        set_status({"ok": "#57d39a", "warn": "#e6c35c", "fail": "#f08a8a"}.get(level, "#57d39a"))
        if level != "ok":
            messagebox.showwarning("Horus", message)

    def dismiss_workers_action() -> None:
        # Drop finished/failed records (running ones are untouched) so the badge
        # stops announcing work that has been reviewed.
        from horus.registry import Registry
        try:
            reg = Registry.default()
            reg.prune()
            workers["lines"] = worker_status_lines(reg.all())
        except Exception as exc:  # noqa: BLE001 (same best-effort rule as the poller)
            log_companion_event(f"dismiss finished workers failed: {exc}")

    def quit_action() -> None:
        root.destroy()

    def show_menu(event: tk.Event) -> None:
        as_of = workers.get("as_of") or "--:--:--"
        menu.entryconfigure(0, label=f"Worker badge as of {as_of}")
        menu.tk_popup(event.x_root, event.y_root)

    def press(event: tk.Event) -> None:
        drag["x"] = event.x_root
        drag["y"] = event.y_root
        drag["root_x"] = root.winfo_x()
        drag["root_y"] = root.winfo_y()
        drag["moved"] = False

    def motion(event: tk.Event) -> None:
        dx = event.x_root - int(drag["x"])
        dy = event.y_root - int(drag["y"])
        if abs(dx) + abs(dy) > 4:
            drag["moved"] = True
        root.geometry(f"+{int(drag['root_x']) + dx}+{int(drag['root_y']) + dy}")

    def release(_event: tk.Event) -> None:
        if not drag["moved"]:
            open_action()

    # Wing breathe: rest -> small lift -> peak -> small lift -> rest. Each step
    # holds ~6 ticks so the flap reads as gentle, not mechanical.
    wing_cycle = (0, 1, 2, 1)

    def animate() -> None:
        n = frame["n"]
        bob = 1 if n % 24 in range(6, 12) else -1 if n % 24 in range(18, 24) else 0
        if n % 96 in (0, 1, 2):
            image_index = 3
        else:
            image_index = wing_cycle[(n // 6) % len(wing_cycle)]
        canvas.itemconfigure(mascot_item, image=mascot_frames[image_index])
        canvas.coords(mascot_item, width // 2, height // 2 + bob)

        # Surface a pending startup failure exactly once per occurrence (main
        # thread — the only place Tk may be touched).
        msg = notice.pop("msg", None)
        if msg:
            set_status("#f08a8a")
            messagebox.showwarning("Horus", msg)

        # Apply the latest worker summary and keep the badge docked under the
        # mascot (it follows drags because this runs every tick).
        text = "\n".join(workers["lines"])
        if text != badge_shown["text"]:
            badge_shown["text"] = text
            if text:
                badge_label.configure(text=text)
                badge.deiconify()
            else:
                badge.withdraw()
        if text:
            badge.geometry(f"+{root.winfo_x()}+{root.winfo_y() + height + 6}")

        frame["n"] = n + 1
        root.after(120, animate)

    menu.add_command(label="Worker badge as of --:--:--", state="disabled")
    menu.add_command(label="Open Dashboard", command=open_action)
    menu.add_command(label="Run Close Check", command=close_check_action)
    menu.add_command(label="Dismiss Finished Workers", command=dismiss_workers_action)
    menu.add_separator()
    menu.add_command(label="Quit", command=quit_action)

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", motion)
    canvas.bind("<ButtonRelease-1>", release)
    canvas.bind("<Button-3>", show_menu)
    badge_label.bind("<ButtonRelease-1>", open_action)
    badge_label.bind("<Button-3>", show_menu)

    animate()
    try:
        root.mainloop()
    finally:
        # Don't leave the dashboard server — or our owned dashboard window — running
        # once the mascot is gone. (Owned-window close is safe: dedicated profile.)
        with state_lock:
            closing.set()
            stop_browser(state["browser_proc"])
            stop_dashboard(state["dashboard"])
    return 0
