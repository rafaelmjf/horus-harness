"""Cross-platform pseudo-terminal (PTY) spawning — the foundation for real TUIs.

A real agent TUI (``claude``/``codex``) needs a pseudo-terminal, not a piped
subprocess: it uses the alternate screen, colors, cursor movement and raw input.
This module hides the platform split behind one small byte-oriented handle:

- **Windows**: ConPTY via :mod:`pywinpty` (no stdlib binding exists there).
- **macOS/Linux**: the stdlib :mod:`pty` module — no third-party dependency.

The handle is intentionally minimal — ``read``/``write``/``resize``/``isalive``/
``terminate`` — so the session-host can run a reader thread over it and stream the
bytes to a browser ``xterm.js`` terminal. Bytes in, bytes out; UTF-8 is handled at
the edges (the agent's escape sequences are ASCII, so a split multibyte char at a
chunk boundary is the only lossy case, tolerated for now).
"""

from __future__ import annotations

import sys
from pathlib import Path


class PtySession:
    """A running process attached to a pseudo-terminal. Byte-oriented + platform-agnostic."""

    pid: int

    def read(self) -> bytes:
        """Block until output is available; return it. Raise ``EOFError`` at end."""
        raise NotImplementedError

    def write(self, data: bytes) -> None:
        """Forward keystrokes/control bytes to the terminal."""
        raise NotImplementedError

    def resize(self, cols: int, rows: int) -> None:
        """Tell the terminal its new window size (so the TUI reflows)."""
        raise NotImplementedError

    def isalive(self) -> bool:
        raise NotImplementedError

    def terminate(self) -> None:
        raise NotImplementedError


class _WinPty(PtySession):
    def __init__(self, argv: list[str], cwd: str, env: dict[str, str], cols: int, rows: int) -> None:
        import winpty  # Windows-only dep, imported lazily

        # winpty takes dimensions as (rows, cols) and speaks str.
        self._p = winpty.PtyProcess.spawn(argv, cwd=cwd, env=env, dimensions=(rows, cols))
        self.pid = self._p.pid

    def read(self) -> bytes:
        try:
            return self._p.read(65536).encode("utf-8", "replace")
        except EOFError:
            raise
        except OSError as exc:  # pragma: no cover - process vanished mid-read
            raise EOFError from exc

    def write(self, data: bytes) -> None:
        self._p.write(data.decode("utf-8", "replace"))

    def resize(self, cols: int, rows: int) -> None:
        self._p.setwinsize(rows, cols)

    def isalive(self) -> bool:
        return self._p.isalive()

    def terminate(self) -> None:
        try:
            self._p.terminate(force=True)
        except Exception:  # noqa: BLE001 - best-effort kill
            pass


class _UnixPty(PtySession):
    def __init__(self, argv: list[str], cwd: str, env: dict[str, str], cols: int, rows: int) -> None:
        import os
        import pty
        import subprocess

        self._os = os
        master, slave = pty.openpty()
        self._master = master
        self.resize(cols, rows)
        self._proc = subprocess.Popen(  # noqa: S603 - argv built by the adapter, not a shell
            argv, cwd=cwd, env=env,
            stdin=slave, stdout=slave, stderr=slave,
            start_new_session=True, close_fds=True,
        )
        os.close(slave)
        self.pid = self._proc.pid

    def read(self) -> bytes:
        try:
            data = self._os.read(self._master, 65536)
        except OSError as exc:  # slave closed -> EIO on Linux
            raise EOFError from exc
        if not data:
            raise EOFError
        return data

    def write(self, data: bytes) -> None:
        self._os.write(self._master, data)

    def resize(self, cols: int, rows: int) -> None:
        import fcntl
        import struct
        import termios

        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._master, termios.TIOCSWINSZ, winsize)

    def isalive(self) -> bool:
        return self._proc.poll() is None

    def terminate(self) -> None:
        try:
            self._proc.terminate()
        except ProcessLookupError:  # pragma: no cover
            pass


def spawn_pty(
    argv: list[str], *, cwd: Path | str, env: dict[str, str] | None = None,
    cols: int = 80, rows: int = 24,
) -> PtySession:
    """Spawn ``argv`` attached to a fresh pseudo-terminal of size ``cols``x``rows``."""
    import os

    full_env = {**os.environ, **(env or {})}
    impl = _WinPty if sys.platform == "win32" else _UnixPty
    return impl(list(argv), str(cwd), full_env, cols, rows)
