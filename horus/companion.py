"""Tiny native companion window for Horus."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import webbrowser
from importlib import resources
from pathlib import Path
from typing import NamedTuple
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
    return DashboardProcess(url, True, process)


def stop_dashboard(dashboard: DashboardProcess) -> None:
    """Terminate a dashboard server *this* companion spawned, so it doesn't outlive
    the mascot and pile up as an orphan. No-op when the dashboard was reused (an
    existing one was already live) or none was started."""
    if dashboard.started and dashboard.process is not None:
        try:
            dashboard.process.terminate()
        except OSError:
            pass


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
    executable = Path(sys.executable)
    if executable.name.lower() != "python.exe":
        # Already pythonw.exe (no console) or an unusual launcher — run inline.
        return False
    pythonw = executable.with_name("pythonw.exe")
    if not pythonw.is_file():
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


# Chromium app-mode (`--app=`) gives a chromeless standalone window — no tabs, no
# address bar — so the dashboard reads as a companion app, not a browser tab. Edge
# ships on Windows 11; Chrome is the fallback. PySide/pywebview is the upgrade path
# if we later want a true native window + taskbar identity.
def _app_browser() -> str | None:
    for candidate in (
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def open_dashboard(url: str, *, app_window: bool = True) -> None:
    """Open the dashboard. Prefers a chromeless app-mode window; falls back to a tab."""
    exe = _app_browser() if app_window else None
    if exe:
        kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        try:
            subprocess.Popen([exe, f"--app={url}", "--window-size=1200,760"], **kwargs)
            return
        except OSError:
            pass
    webbrowser.open(url, new=2)


def mascot_asset_path() -> Path:
    return Path(str(resources.files("horus").joinpath("assets", "mascot.png")))


def mascot_frame_paths() -> list[Path]:
    names = ["mascot_idle_0.png", "mascot_idle_1.png", "mascot_idle_2.png", "mascot_blink.png"]
    return [Path(str(resources.files("horus").joinpath("assets", name))) for name in names]


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
    usage_threshold: float = 90.0,
) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print("Tkinter is not available; the Horus companion needs a desktop Python with Tk.")
        return 2

    lock = acquire_singleton_lock()
    if lock is None:
        print("Horus companion already running; not starting another.")
        return 0

    dashboard = ensure_dashboard(host, port, start=start_dashboard)
    if open_on_start:
        open_dashboard(dashboard.url)

    root = tk.Tk()
    root.title("Horus")
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    transparent = "#ff00ff"
    root.configure(bg=transparent)
    try:
        root.attributes("-transparentcolor", transparent)
    except tk.TclError:
        pass

    full_frames = [tk.PhotoImage(file=str(path)) for path in mascot_frame_paths()]
    scale = max(1, max(frame.height() for frame in full_frames) // 180)
    mascot_frames = [frame.subsample(scale, scale) for frame in full_frames]
    width = max(frame.width() for frame in mascot_frames)
    height = max(frame.height() for frame in mascot_frames)
    root.geometry(f"{width}x{height}+80+80")

    canvas = tk.Canvas(root, width=width, height=height, bg=transparent, highlightthickness=0, bd=0)
    canvas.pack()

    menu = tk.Menu(root, tearoff=0)
    mascot_item = canvas.create_image(width // 2, height // 2, image=mascot_frames[0])
    status_item = canvas.create_rectangle(width - 18, height - 18, width - 8, height - 8, fill="#57d39a", outline="#ffffff")
    canvas.create_text(width - 13, height - 13, text="", fill="#ffffff")

    drag: dict[str, int | bool] = {"x": 0, "y": 0, "root_x": 80, "root_y": 80, "moved": False}
    frame = {"n": 0}

    def set_status(color: str) -> None:
        canvas.itemconfigure(status_item, fill=color)

    def open_action(_event: object | None = None) -> None:
        open_dashboard(dashboard.url)

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
        # Don't leave the dashboard server running once the mascot is gone.
        stop_dashboard(dashboard)
    return 0
