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
    Elsewhere it falls back to a plain spawn attached to the current terminal.
    """
    exe = shutil.which(argv[0]) or argv[0]
    full_argv = [exe, *argv[1:]]
    full_env = {**os.environ, **(env or {})}
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if sys.platform == "win32" else 0
    proc = subprocess.Popen(  # noqa: S603 (argv built by the adapter, not shell)
        full_argv,
        cwd=str(cwd),
        env=full_env,
        creationflags=creationflags,
    )
    return proc.pid
