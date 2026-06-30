"""Tiny native companion window for Horus."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from importlib import resources
from pathlib import Path, PureWindowsPath
from typing import Any, NamedTuple
from urllib.error import URLError
from urllib.request import urlopen


class DashboardProcess(NamedTuple):
    url: str
    started: bool
    process: subprocess.Popen[str] | None


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


def ensure_dashboard(host: str = "127.0.0.1", port: int = 8765, *, start: bool = True) -> DashboardProcess:
    url = dashboard_url(host, port)
    if dashboard_is_live(url) or not start:
        return DashboardProcess(url, False, None)

    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "text": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    process = subprocess.Popen(
        [sys.executable, "-m", "horus", "dashboard", "--host", host, "--port", str(port)],
        **kwargs,
    )
    _wait_dashboard_live(url, process)
    return DashboardProcess(url, True, process)


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
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print("Tkinter is not available; the Horus companion needs a desktop Python with Tk.")
        return 2
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("No graphical display detected; run `horus app` from a Linux desktop session with DISPLAY or WAYLAND_DISPLAY set.")
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

    def ensure_open(open_browser: bool) -> None:
        """Spawn/locate the dashboard and optionally open (or raise) its window.
        Idempotent and safe from the pre-warm thread or the mascot click."""
        with state_lock:
            dash = state["dashboard"] or ensure_dashboard(host, port, start=start_dashboard)
            if open_browser:
                dash = ensure_dashboard_for_open(dash, host=host, port=port, start=start_dashboard)
                state["browser_proc"] = reuse_or_open_dashboard(
                    dash.url, state["browser_proc"], app_window=owned
                )
            state["dashboard"] = dash

    # Pre-warm off the critical path: the mascot window appears immediately instead
    # of blocking on the dashboard coming live and (when pre-warming) the browser's
    # cold launch. The click handler reuses whatever this set up.
    threading.Thread(target=lambda: ensure_open(open_browser=open_on_start), daemon=True).start()

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

    def quit_action() -> None:
        root.destroy()

    def show_menu(event: tk.Event) -> None:
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

        frame["n"] = n + 1
        root.after(120, animate)

    menu.add_command(label="Open Dashboard", command=open_action)
    menu.add_command(label="Run Close Check", command=close_check_action)
    menu.add_separator()
    menu.add_command(label="Quit", command=quit_action)

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", motion)
    canvas.bind("<ButtonRelease-1>", release)
    canvas.bind("<Button-3>", show_menu)

    animate()
    try:
        root.mainloop()
    finally:
        # Don't leave the dashboard server — or our owned dashboard window — running
        # once the mascot is gone. (Owned-window close is safe: dedicated profile.)
        with state_lock:
            stop_browser(state["browser_proc"])
            stop_dashboard(state["dashboard"])
    return 0
