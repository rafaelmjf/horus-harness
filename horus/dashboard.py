"""Read-only, local-only multi-project dashboard.

Serves an overview of every project registered in ``~/.horus/config.toml`` plus a
per-project detail view rendered from that repo's `.horus/` files. Read-only: no
prompt input, no mutation, no arbitrary file access (projects are addressed by
their index in the config list, never by a path from the request).
"""

from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from horus import config, frontmatter, markdown
from horus.continuity import HORUS_DIR, check_project, horus_dir, recent_sessions


def load_project(path_str: str) -> dict[str, Any]:
    """Collect everything the dashboard shows for one project (read fresh)."""
    root = Path(path_str)
    hdir = horus_dir(root)
    data: dict[str, Any] = {
        "path": str(root),
        "name": root.name,
        "exists": hdir.is_dir(),
        "title": root.name,
        "status": "",
        "current_focus": "",
        "project_body": "",
        "roadmap_body": "",
        "decisions_body": "",
        "sessions": [],
        "findings": [],
    }
    if not hdir.is_dir():
        return data

    project_md = hdir / "project.md"
    if project_md.is_file():
        doc = frontmatter.parse(project_md.read_text(encoding="utf-8"))
        data["status"] = doc.front_matter.get("status", "")
        data["current_focus"] = doc.front_matter.get("current_focus", "")
        data["project_body"] = doc.body

    roadmap_md = hdir / "roadmap.md"
    if roadmap_md.is_file():
        doc = frontmatter.parse(roadmap_md.read_text(encoding="utf-8"))
        if not data["current_focus"]:
            data["current_focus"] = doc.front_matter.get("current_focus", "")
        data["roadmap_body"] = doc.body

    decisions_md = hdir / "decisions.md"
    if decisions_md.is_file():
        data["decisions_body"] = decisions_md.read_text(encoding="utf-8")

    for sp in recent_sessions(root):
        doc = frontmatter.parse(sp.read_text(encoding="utf-8"))
        data["sessions"].append(
            {
                "file": sp.name,
                "date": doc.front_matter.get("date", ""),
                "agent": doc.front_matter.get("agent", ""),
                "status": doc.front_matter.get("status", ""),
                "summary": doc.front_matter.get("summary", ""),
            }
        )

    data["findings"] = [
        {"level": f.level, "message": f.message} for f in check_project(root)
    ]
    return data


def gather_projects() -> list[dict[str, Any]]:
    return [load_project(p) for p in config.load_projects()]


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #

_STYLE = """
* { box-sizing: border-box; }
body { font: 15px/1.5 -apple-system, Segoe UI, Roboto, sans-serif;
       margin: 0; background: #0f1115; color: #e6e6e6; }
a { color: #6db3f2; text-decoration: none; }
a:hover { text-decoration: underline; }
header { padding: 18px 28px; border-bottom: 1px solid #232733; background: #151823; }
header h1 { margin: 0; font-size: 18px; letter-spacing: .3px; }
header .sub { color: #8a93a6; font-size: 13px; }
main { padding: 24px 28px; max-width: 980px; }
.card { background: #151823; border: 1px solid #232733; border-radius: 10px;
        padding: 16px 18px; margin: 0 0 14px; }
.card h2 { margin: 0 0 4px; font-size: 16px; }
.muted { color: #8a93a6; }
.badges span { display: inline-block; font-size: 12px; padding: 2px 8px;
               border-radius: 999px; margin-right: 6px; background: #232733; }
.health-ok { color: #57d39a; } .health-warn { color: #e6c35c; }
.health-fail { color: #f08a8a; }
ul { padding-left: 22px; } li.task { list-style: none; margin-left: -16px; }
li.done { color: #8a93a6; } li.partial { color: #e6c35c; }
pre { background: #0b0d12; padding: 12px; border-radius: 8px; overflow-x: auto; }
code { background: #0b0d12; padding: 1px 5px; border-radius: 4px; }
.section { margin-top: 26px; }
.back { font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
td, th { text-align: left; padding: 6px 10px; border-bottom: 1px solid #232733; }
"""

_LEVEL_CLASS = {"ok": "health-ok", "warn": "health-warn", "fail": "health-fail"}


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style></head><body>"
        "<header><h1>Horus</h1>"
        "<div class='sub'>project continuity &amp; control panel</div></header>"
        f"<main>{body}</main></body></html>"
    )


def _health_summary(findings: list[dict[str, Any]]) -> str:
    fails = sum(1 for f in findings if f["level"] == "fail")
    warns = sum(1 for f in findings if f["level"] == "warn")
    if fails:
        return f"<span class='health-fail'>&#9679; {fails} issue(s)</span>"
    if warns:
        return f"<span class='health-warn'>&#9679; {warns} warning(s)</span>"
    return "<span class='health-ok'>&#9679; healthy</span>"


def render_index(projects: list[dict[str, Any]]) -> str:
    if not projects:
        body = (
            "<div class='card'><h2>No projects registered</h2>"
            "<p class='muted'>Run <code>horus init</code> inside a project to "
            "register it here.</p></div>"
        )
        return _page("Horus", body)

    cards = []
    for i, p in enumerate(projects):
        focus = html.escape(p["current_focus"]) or "<span class='muted'>no current focus</span>"
        status = html.escape(p["status"]) or "unknown"
        missing = "" if p["exists"] else " <span class='health-fail'>(no .horus/)</span>"
        cards.append(
            f"<div class='card'><h2><a href='/project?i={i}'>"
            f"{html.escape(p['name'])}</a>{missing}</h2>"
            f"<div class='badges'><span>status: {status}</span>"
            f"<span>{len(p['sessions'])} session(s)</span> {_health_summary(p['findings'])}</div>"
            f"<p>{focus}</p>"
            f"<p class='muted' style='font-size:12px'>{html.escape(p['path'])}</p></div>"
        )
    return _page("Horus", "".join(cards))


def render_project(p: dict[str, Any]) -> str:
    parts = [
        "<p class='back'><a href='/'>&larr; all projects</a></p>",
        f"<h1 style='margin-top:6px'>{html.escape(p['name'])}</h1>",
        f"<div class='badges'><span>status: {html.escape(p['status']) or 'unknown'}</span>"
        f"{_health_summary(p['findings'])}</div>",
    ]

    if p["current_focus"]:
        parts.append(
            f"<div class='card'><strong>Current focus:</strong> "
            f"{html.escape(p['current_focus'])}</div>"
        )

    # Continuity health
    rows = "".join(
        f"<tr><td class='{_LEVEL_CLASS.get(f['level'], '')}'>{f['level']}</td>"
        f"<td>{html.escape(f['message'])}</td></tr>"
        for f in p["findings"]
    )
    parts.append(
        f"<div class='section'><h2>Continuity health</h2><table>{rows}</table></div>"
    )

    if p["roadmap_body"]:
        parts.append(
            f"<div class='section'><h2>Roadmap</h2>{markdown.render(p['roadmap_body'])}</div>"
        )

    if p["sessions"]:
        srows = "".join(
            f"<tr><td>{html.escape(s['date'])}</td><td>{html.escape(s['agent'])}</td>"
            f"<td>{html.escape(s['status'])}</td><td>{html.escape(s['summary'])}</td></tr>"
            for s in p["sessions"]
        )
        parts.append(
            "<div class='section'><h2>Recent sessions</h2>"
            "<table><tr><th>date</th><th>agent</th><th>status</th><th>summary</th></tr>"
            f"{srows}</table></div>"
        )

    if p["decisions_body"]:
        parts.append(
            f"<div class='section'><h2>Decisions</h2>{markdown.render(p['decisions_body'])}</div>"
        )

    if p["project_body"]:
        parts.append(
            f"<div class='section'><h2>Project brief</h2>{markdown.render(p['project_body'])}</div>"
        )

    return _page(f"Horus - {p['name']}", "".join(parts))


# --------------------------------------------------------------------------- #
# Server
# --------------------------------------------------------------------------- #

class _Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(render_index(gather_projects()))
            return
        if parsed.path == "/project":
            projects = gather_projects()
            try:
                idx = int(parse_qs(parsed.query).get("i", ["?"])[0])
                project = projects[idx]
            except (ValueError, IndexError):
                self._send(_page("Not found", "<p>Unknown project.</p>"), 404)
                return
            self._send(render_project(project))
            return
        self._send(_page("Not found", "<p>Not found.</p>"), 404)

    def log_message(self, *args: Any) -> None:  # silence default stderr logging
        pass


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), _Handler)
    count = len(config.load_projects())
    print(f"Horus dashboard: http://{host}:{port}  ({count} project(s))")
    print("Read-only. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
