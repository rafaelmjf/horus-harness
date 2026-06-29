"""Open an interactive agent session in its own terminal window.

This is the *attended* counterpart to the headless ``-p`` flow: it launches the
real CLI's TUI in a fresh console the user can type into, and returns the child's
PID so the registry can track it as a live ``running`` session (it dies when the
user exits, which ``Registry.reconcile()`` then notices).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def open_terminal(argv: list[str], cwd: Path | str, env: dict[str, str] | None = None) -> int:
    """Launch ``argv`` in its own terminal window; return the child PID.

    On Windows uses ``CREATE_NEW_CONSOLE`` so the child gets a real console window
    (the returned PID is the child's, not a launcher's, so liveness tracking works).
    On POSIX, require a graphical session and a terminal emulator; otherwise fail
    clearly instead of pretending a non-TTY child is an attended session.
    """
    exe = shutil.which(argv[0]) or argv[0]
    full_argv = [exe, *argv[1:]]
    full_env = {**os.environ, **(env or {})}
    if sys.platform == "win32":
        proc = subprocess.Popen(  # noqa: S603 (argv built by the adapter, not shell)
            full_argv,
            cwd=str(cwd),
            env=full_env,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return proc.pid

    terminal_argv = _posix_terminal_argv(full_argv, cwd=Path(cwd))
    proc = subprocess.Popen(terminal_argv, cwd=str(cwd), env=full_env)  # noqa: S603
    return proc.pid


def _posix_terminal_argv(argv: list[str], *, cwd: Path) -> list[str]:
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise OSError(
            "no graphical display detected; run `horus open` from a desktop session "
            "or use the dashboard in-app terminal"
        )

    command = " ".join(shlex_quote(part) for part in argv)
    candidates = (
        ("x-terminal-emulator", ["x-terminal-emulator", "-e", "sh", "-lc", command]),
        ("gnome-terminal", ["gnome-terminal", f"--working-directory={cwd}", "--", *argv]),
        ("kgx", ["kgx", "--working-directory", str(cwd), "-e", *argv]),
        ("konsole", ["konsole", "--workdir", str(cwd), "-e", *argv]),
        ("xfce4-terminal", ["xfce4-terminal", "--working-directory", str(cwd), "-e", command]),
        ("xterm", ["xterm", "-e", command]),
        ("alacritty", ["alacritty", "--working-directory", str(cwd), "-e", *argv]),
        ("kitty", ["kitty", "--directory", str(cwd), *argv]),
    )
    for name, term_argv in candidates:
        exe = shutil.which(name)
        if exe:
            return [exe, *term_argv[1:]]
    raise OSError("no supported terminal emulator found for `horus open`; use the dashboard in-app terminal")


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


def login_argv_env(agent: str, config_dir_path: str) -> tuple[list[str], dict[str, str]]:
    """Native-CLI command + env that runs an interactive login isolated to
    ``config_dir_path``.

    Claude prompts for sign-in automatically when its config dir holds no credentials,
    so launching ``claude`` in a fresh ``CLAUDE_CONFIG_DIR`` lands the user in the login
    flow; Codex has an explicit ``codex login`` driven by ``CODEX_HOME``."""
    if agent == "claude":
        return ["claude"], {"CLAUDE_CONFIG_DIR": config_dir_path}
    if agent == "codex":
        return ["codex", "login"], {"CODEX_HOME": config_dir_path}
    raise ValueError(f"unknown agent: {agent}")


def _descendant_pids(pid: int) -> set[int]:
    """The pid and all its descendants (Windows, via a Toolhelp snapshot).

    A `CREATE_NEW_CONSOLE` window is usually owned by a child (classic `conhost.exe`
    is a child of the console process), so a plain pid match misses it — we match the
    whole subtree instead.
    """
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID = ctypes.c_void_p(-1).value

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    # Declare signatures so 64-bit HANDLEs aren't truncated to int (ctypes' default).
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32First.restype = wintypes.BOOL
    kernel32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.Process32Next.restype = wintypes.BOOL
    kernel32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID:
        return {pid}
    children: dict[int, list[int]] = {}
    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        ok = kernel32.Process32First(snap, ctypes.byref(entry))
        while ok:
            children.setdefault(entry.th32ParentProcessID, []).append(entry.th32ProcessID)
            ok = kernel32.Process32Next(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)

    seen: set[int] = set()
    stack = [pid]
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        seen.add(p)
        stack.extend(children.get(p, []))
    return seen


def focus_window_for_pid(pid: int | None) -> bool:
    """Bring the (console) window owned by ``pid`` (or a descendant) to the front.

    Best-effort and Windows-only: returns False on other platforms, when no PID was
    tracked, or when no visible top-level window maps to the process subtree (e.g. the
    session is hosted in a shared Windows Terminal process, whose window isn't a child
    of the tracked PID). ``SetForegroundWindow`` itself is subject to the OS foreground
    lock, so even a found window may only flash in the taskbar.
    """
    if sys.platform != "win32" or not pid or pid <= 0:
        return False
    import ctypes
    from ctypes import wintypes

    # Declare signatures so 64-bit HWNDs survive the round trip (see _descendant_pids).
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    targets = _descendant_pids(pid)
    found: list[int] = []

    @WNDENUMPROC
    def _cb(hwnd, _lparam):  # noqa: ANN001 (ctypes callback)
        if not user32.IsWindowVisible(hwnd):
            return True
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value in targets:
            found.append(hwnd)
            return False  # stop enumerating
        return True

    user32.EnumWindows(_cb, 0)
    if not found:
        return False
    hwnd = found[0]
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)  # un-minimize if needed
    user32.BringWindowToTop(hwnd)
    return bool(user32.SetForegroundWindow(hwnd))
