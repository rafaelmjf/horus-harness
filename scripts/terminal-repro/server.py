"""Stub HTTP server for the terminal CDP repro harness.

Serves the REAL terminal markup/CSS/JS straight from horus.dashboard
(_STYLE, _terminal_panel, _XTERM_ATTACH_JS, _TERMINAL_JS) plus the vendored
xterm assets, backed by a stub /pty/* that logs posted resizes instead of
touching a real PTY. The FitAddon computes cols/rows purely from the host
element's box, so the sizing/lifecycle behavior under test reproduces
faithfully without real PTY bytes or a real agent process — see
docs/terminal-mobile-desktop-diagnosis.md Sec 2.

Not part of the pytest/CI gate (it needs a local Chromium/chrome-headless-shell
binary this repo doesn't install in CI). Run directly:

    python3 scripts/terminal-repro/server.py [port]

then drive it with scripts/terminal-repro/repro.mjs, or open it in a real
browser and resize the window by hand.
"""

from __future__ import annotations

import base64
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from horus import dashboard, pty_host  # noqa: E402

ASSETS = ROOT / "horus" / "assets" / "vendor" / "xterm"

_lock = threading.Lock()
_resizes: list[dict] = []
_closed: set[str] = set()
_redraws: list[str] = []
_subscribers: dict[str, list[queue.Queue[tuple[str, bytes]]]] = {}

TERMINALS = [
    pty_host.PtyTerminal(term_id="pty-1", agent="claude", project_dir=ROOT, title="alpha"),
    pty_host.PtyTerminal(term_id="pty-2", agent="claude", project_dir=ROOT, title="beta"),
]


def _page() -> str:
    panel = dashboard._terminal_panel(TERMINALS)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>terminal-repro</title><style>{dashboard._STYLE}</style>"
        f"{dashboard._TERMINAL_HEAD}"
        "</head><body><div class='wrap' style='margin:0 auto;padding:16px;'>"
        # .control is a 2-col grid (sidebar 280px / main 1fr) in the real page —
        # the empty sidebar keeps the panel in the 1fr column like the real DOM,
        # instead of it falling into the fixed 280px column via grid auto-placement.
        f"<div class='control'><div class='sidebar'></div><div class='control-main'>{panel}</div></div>"
        f"</div>{dashboard._XTERM_ATTACH_JS}{dashboard._TERMINAL_JS}"
        "</body></html>"
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: A003 - quiet by default
        pass

    def _send(self, body: bytes, status: int = 200, ctype: str = "text/html; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _no_content(self) -> None:
        self.send_response(204)
        self.end_headers()

    def _read_form(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        parsed = parse_qs(raw.decode("utf-8", "replace"))
        return {k: v[0] for k, v in parsed.items()}

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(_page().encode("utf-8"))
            return
        if parsed.path.startswith("/assets/xterm/"):
            name = parsed.path[len("/assets/xterm/"):]
            f = ASSETS / name
            if not f.is_file():
                self._send(b"not found", 404, "text/plain")
                return
            ctype = "text/css" if name.endswith(".css") else "application/javascript"
            self._send(f.read_bytes(), 200, ctype)
            return
        if parsed.path == "/pty/stream":
            tid = parse_qs(parsed.query).get("id", [""])[0]
            output: queue.Queue[tuple[str, bytes]] = queue.Queue()
            with _lock:
                _subscribers.setdefault(tid, []).append(output)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                # Deliberately announce a grid that differs from the fitted
                # browser box, then replay old-grid bytes. This exercises the
                # geometry-epoch redraw path rather than merely the fit path.
                replay = base64.b64encode(f"OLD-{tid}".encode())
                self.wfile.write(b"event: geometry\ndata: 80x24\n\n")
                self.wfile.write(b"event: status\ndata: live\n\n")
                self.wfile.write(b"event: output\ndata: " + replay + b"\n\n")
                self.wfile.flush()
                while True:
                    try:
                        kind, chunk = output.get(timeout=1.0)
                        if kind == "reset":
                            self.wfile.write(b"event: reset\ndata: " + chunk + b"\n\n")
                        else:
                            encoded = base64.b64encode(chunk)
                            self.wfile.write(b"event: output\ndata: " + encoded + b"\n\n")
                    except queue.Empty:
                        self.wfile.write(b": hb\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with _lock:
                    listeners = _subscribers.get(tid, [])
                    if output in listeners:
                        listeners.remove(output)
            return
        if parsed.path == "/__state":
            import json

            with _lock:
                body = json.dumps({
                    "resizes": _resizes,
                    "closed": sorted(_closed),
                    "redraws": _redraws,
                }).encode("utf-8")
            self._send(body, 200, "application/json")
            return
        self._send(b"not found", 404, "text/plain")

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/pty/resize":
            form = self._read_form()
            with _lock:
                _resizes.append({
                    "id": form.get("id", ""),
                    "cols": int(form.get("cols", 0) or 0),
                    "rows": int(form.get("rows", 0) or 0),
                })
            self._no_content()
            return
        if parsed.path == "/pty/input":
            self._no_content()
            return
        if parsed.path == "/pty/release":
            self._no_content()
            return
        if parsed.path == "/pty/redraw":
            form = self._read_form()
            tid = form.get("id", "")
            token = form.get("reset", "").encode()
            with _lock:
                _redraws.append(tid)
                listeners = list(_subscribers.get(tid, []))
            # Reproduce the real race: the ordered reset marker and repaint can
            # both beat the redraw POST response on the independent SSE stream.
            for listener in listeners:
                listener.put(("reset", token))
                listener.put(("output", f"FRESH-{tid}".encode()))
            time.sleep(0.15)
            self._no_content()
            return
        if parsed.path == "/__emit":
            form = self._read_form()
            tid = form.get("id", "")
            data = form.get("data", "").encode()
            with _lock:
                listeners = list(_subscribers.get(tid, []))
            for listener in listeners:
                listener.put(("output", data))
            self._no_content()
            return
        if parsed.path == "/pty/close":
            form = self._read_form()
            with _lock:
                _closed.add(form.get("id", ""))
            self._no_content()
            return
        self._send(b"not found", 404, "text/plain")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8999
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"terminal-repro server on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
