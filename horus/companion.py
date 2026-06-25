"""Tiny native companion window for Horus."""

from __future__ import annotations

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


def mascot_asset_path() -> Path:
    return Path(str(resources.files("horus").joinpath("assets", "mascot.png")))


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
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    root.configure(bg="#ffffff")

    full_img = tk.PhotoImage(file=str(mascot_asset_path()))
    scale = max(1, full_img.height() // 180)
    mascot_img = full_img.subsample(scale, scale)
    width = mascot_img.width()
    height = mascot_img.height()
    root.geometry(f"{width}x{height}+80+80")

    canvas = tk.Canvas(root, width=width, height=height, bg="#ffffff", highlightthickness=0, bd=0)
    canvas.pack()

    menu = tk.Menu(root, tearoff=0)
    mascot_item = canvas.create_image(width // 2, height // 2, image=mascot_img)
    wing_item = canvas.create_polygon(0, 0, 1, 0, 1, 1, fill="#6db85f", outline="#2f6d39")
    blink_item = canvas.create_rectangle(0, 0, 0, 0, fill="#143b74", outline="#143b74", state="hidden")
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

    def animate() -> None:
        n = frame["n"]
        bob = 1 if n % 24 in range(6, 12) else -1 if n % 24 in range(18, 24) else 0
        canvas.coords(mascot_item, width // 2, height // 2 + bob)

        flap = -3 if n % 28 < 14 else 2
        x0, y0 = int(width * 0.61), int(height * 0.49) + flap
        x1, y1 = int(width * 0.91), int(height * 0.65) + flap
        x2, y2 = int(width * 0.75), int(height * 0.77) + flap
        canvas.coords(wing_item, x0, y0, x1, y1, x2, y2, int(width * 0.66), int(height * 0.66) + flap)

        blink_on = n % 96 in (0, 1, 2)
        if blink_on:
            canvas.coords(
                blink_item,
                int(width * 0.27),
                int(height * 0.32) + bob,
                int(width * 0.39),
                int(height * 0.36) + bob,
            )
            canvas.itemconfigure(blink_item, state="normal")
        else:
            canvas.itemconfigure(blink_item, state="hidden")

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
    root.mainloop()
    return 0
