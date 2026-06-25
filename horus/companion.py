"""Tiny native companion window for Horus."""

from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import NamedTuple
from urllib.error import URLError
from urllib.request import urlopen


class DashboardProcess(NamedTuple):
    url: str
    started: bool
    process: subprocess.Popen[str] | None


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


def open_dashboard(url: str) -> None:
    webbrowser.open(url, new=2)


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

    dashboard = ensure_dashboard(host, port, start=start_dashboard)
    if open_on_start:
        open_dashboard(dashboard.url)

    root = tk.Tk()
    root.title("Horus")
    root.geometry("96x112+80+80")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#101319")

    status = tk.StringVar(value="active")
    canvas = tk.Canvas(root, width=96, height=88, bg="#101319", highlightthickness=0)
    canvas.pack()
    label = tk.Label(root, textvariable=status, bg="#101319", fg="#d7e0ef", font=("Segoe UI", 8))
    label.pack(fill="x")

    menu = tk.Menu(root, tearoff=0)

    def draw(color: str = "#57d39a") -> None:
        canvas.delete("all")
        # Flat pixel mascot: simple eye/sun motif inspired by Horus without assets.
        canvas.create_rectangle(0, 0, 96, 88, fill="#101319", outline="#101319")
        canvas.create_rectangle(28, 18, 68, 58, fill="#d7b95b", outline="#d7b95b")
        canvas.create_rectangle(20, 30, 76, 46, fill="#d7b95b", outline="#d7b95b")
        canvas.create_rectangle(36, 26, 60, 50, fill="#101319", outline="#101319")
        canvas.create_rectangle(42, 32, 54, 44, fill="#e8f0ff", outline="#e8f0ff")
        canvas.create_rectangle(46, 34, 52, 42, fill="#101319", outline="#101319")
        canvas.create_rectangle(12, 66, 84, 72, fill=color, outline=color)
        canvas.create_rectangle(44, 62, 52, 80, fill=color, outline=color)

    def open_action(_event: object | None = None) -> None:
        open_dashboard(dashboard.url)

    def close_check_action() -> None:
        level, message = run_close_check(project_root, threshold=usage_threshold)
        status.set(message)
        draw({"ok": "#57d39a", "warn": "#e6c35c", "fail": "#f08a8a"}.get(level, "#57d39a"))
        if level != "ok":
            messagebox.showwarning("Horus", message)

    def quit_action() -> None:
        root.destroy()

    def show_menu(event: tk.Event) -> None:
        menu.tk_popup(event.x_root, event.y_root)

    menu.add_command(label="Open Dashboard", command=open_action)
    menu.add_command(label="Run Close Check", command=close_check_action)
    menu.add_separator()
    menu.add_command(label="Quit", command=quit_action)

    canvas.bind("<Button-1>", open_action)
    canvas.bind("<Button-3>", show_menu)
    label.bind("<Button-1>", open_action)
    label.bind("<Button-3>", show_menu)

    draw()
    root.mainloop()
    return 0
