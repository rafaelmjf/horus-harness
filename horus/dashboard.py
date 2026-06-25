"""Read-only, local-only multi-project dashboard.

Serves an overview of every project registered in ``~/.horus/config.toml`` plus a
per-project detail view rendered from that repo's `.horus/` files. Read-only: no
prompt input, no mutation, no arbitrary file access (projects are addressed by
their index in the config list, never by a path from the request).
"""

from __future__ import annotations

import html
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from horus import codex_usage, config, frontmatter, markdown, roadmap, routines
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
        "features_body": "",
        "feature_counts": {"shipped": 0, "in_progress": 0, "planned": 0},
        "decisions_body": "",
        "history_body": "",
        "sessions": [],
        "findings": [],
        "next_step": None,
        "latest": None,
        "progress": {"done": 0, "total": 0, "pct": 0},
        "tasks": [],
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

    features_md = hdir / "features.md"
    if features_md.is_file():
        doc = frontmatter.parse(features_md.read_text(encoding="utf-8"))
        data["features_body"] = doc.body
        data["feature_counts"] = routines.feature_counts(doc.body)

    decisions_md = hdir / "decisions.md"
    if decisions_md.is_file():
        data["decisions_body"] = decisions_md.read_text(encoding="utf-8")

    history_md = hdir / "history.md"
    if history_md.is_file():
        data["history_body"] = frontmatter.parse(history_md.read_text(encoding="utf-8")).body

    for sp in recent_sessions(root, limit=12):
        doc = frontmatter.parse(sp.read_text(encoding="utf-8"))
        data["sessions"].append(
            {
                "file": sp.name,
                "date": doc.front_matter.get("date", ""),
                "agent": doc.front_matter.get("agent", ""),
                "account": doc.front_matter.get("account", ""),
                "status": doc.front_matter.get("status", ""),
                "summary": doc.front_matter.get("summary", ""),
                "mtime": sp.stat().st_mtime,
            }
        )

    # Sort newest-first by frontmatter date, then mtime, then filename, so
    # "latest" is correct even when several summaries share a date.
    data["sessions"].sort(key=lambda s: (s["date"], s["mtime"], s["file"]), reverse=True)
    data["latest"] = data["sessions"][0] if data["sessions"] else None

    tasks = roadmap.parse_tasks(data["roadmap_body"])
    ns = roadmap.next_step(tasks)
    data["next_step"] = {"text": ns.text, "section": ns.section} if ns else None
    prog = roadmap.progress(tasks)
    data["progress"] = {"done": prog.done, "total": prog.total, "pct": prog.pct}
    data["tasks"] = [{"state": t.state, "text": t.text, "section": t.section} for t in tasks]

    data["findings"] = [
        {"level": f.level, "message": f.message}
        for f in check_project(root) + codex_usage.usage_findings(root)
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
.next { background: #15281d; border: 1px solid #1f5138; border-left: 3px solid #57d39a;
        border-radius: 8px; padding: 9px 12px; margin: 10px 0; }
.next .lbl { color: #57d39a; font-weight: 600; font-size: 12px; letter-spacing: .5px; display: block; }
.next ul.steps { margin: 6px 0 0; padding-left: 20px; }
.next ul.steps li { margin: 3px 0; }
.next.done { border-left-color: #6db3f2; }
.next.done .lbl { color: #6db3f2; display: inline; }
.latest { color: #b9c2d0; font-size: 13px; margin: 8px 0; }
.latest .date { color: #8a93a6; }
.bar { height: 6px; background: #232733; border-radius: 999px; overflow: hidden; margin: 10px 0 4px; }
.bar > span { display: block; height: 100%; background: #57d39a; }
.progress-label { font-size: 12px; color: #8a93a6; }
.progress-label a { color: #8a93a6; text-decoration: underline dotted; }
details.tasks { margin: 8px 0; border: 1px solid #232733; border-radius: 8px; padding: 6px 12px; background: #12141b; }
details.tasks summary { cursor: pointer; font-size: 13px; color: #b9c2d0; }
details.tasks ul { margin: 8px 0 4px; }
details.tasks li { list-style: none; margin-left: -16px; }
.t-done { color: #8a93a6; } .t-done .mk { color: #57d39a; }
.t-todo .mk { color: #6db3f2; } .t-partial { color: #e6c35c; }
.t-sec { color: #8a93a6; font-size: 12px; }
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


def _plain(text: str) -> str:
    """Strip Markdown emphasis/code ticks for one-line display."""
    return re.sub(r"\*\*|__|`", "", text).strip()


def next_steps(p: dict[str, Any], limit: int = 3) -> list[str]:
    """A few suggested directions (not a strict order): the explicit focus banner
    first, then in-progress tasks, then open tasks."""
    steps: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        t = _plain(text)
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            steps.append(t)

    focus = p["current_focus"].strip()
    if focus and not focus.lower().startswith("describe "):
        add(focus)
    for state in ("partial", "todo"):
        for t in p["tasks"]:
            if len(steps) >= limit:
                break
            if t["state"] == state:
                add(t["text"])
    return steps[:limit]


def _next_html(p: dict[str, Any]) -> str:
    steps = next_steps(p)
    if steps:
        items = "".join(f"<li>{html.escape(s)}</li>" for s in steps)
        return f"<div class='next'><span class='lbl'>NEXT</span><ul class='steps'>{items}</ul></div>"
    if p["progress"]["total"]:
        return "<div class='next done'><span class='lbl'>NEXT</span> &#10003; roadmap complete</div>"
    return ""


def _features_badge(p: dict[str, Any]) -> str:
    fc = p["feature_counts"]
    if not any(fc.values()):
        return ""
    bits = [f"{fc['shipped']} shipped"]
    if fc["in_progress"]:
        bits.append(f"{fc['in_progress']} in progress")
    if fc["planned"]:
        bits.append(f"{fc['planned']} planned")
    return f"<span>{html.escape(', '.join(bits))}</span>"


def _latest_html(p: dict[str, Any]) -> str:
    latest = p["latest"]
    if not latest:
        return "<div class='latest muted'>no sessions yet</div>"
    summary = html.escape(latest["summary"]) or "(no summary)"
    return (
        f"<div class='latest'><span class='date'>{html.escape(latest['date'])}</span> "
        f"&middot; {summary}</div>"
    )


def _progress_html(p: dict[str, Any], href: str | None = None) -> str:
    pr = p["progress"]
    if not pr["total"]:
        return ""
    label = f"roadmap: {pr['done']}/{pr['total']} done ({pr['pct']}%)"
    if href:
        label = f"<a href='{href}'>{label}</a>"
    return (
        f"<div class='bar'><span style='width:{pr['pct']}%'></span></div>"
        f"<div class='progress-label'>{label}</div>"
    )


_TASK_MARK = {"done": "&#9745;", "todo": "&#9744;", "partial": "&#9682;"}


def _task_li(t: dict[str, Any]) -> str:
    sec = f" <span class='t-sec'>({html.escape(t['section'])})</span>" if t["section"] else ""
    return (
        f"<li class='t-{t['state']}'><span class='mk'>{_TASK_MARK.get(t['state'], '')}</span> "
        f"{html.escape(t['text'])}{sec}</li>"
    )


def _breakdown_html(p: dict[str, Any]) -> str:
    """The items behind the progress count: open/in-progress and completed, grouped."""
    tasks = p["tasks"]
    if not tasks:
        return markdown.render(p["roadmap_body"]) if p["roadmap_body"] else ""
    open_tasks = [t for t in tasks if t["state"] in ("todo", "partial")]
    done_tasks = [t for t in tasks if t["state"] == "done"]
    out = []
    if open_tasks:
        items = "".join(_task_li(t) for t in open_tasks)
        out.append(
            f"<details class='tasks' open><summary>Open &amp; in progress ({len(open_tasks)})</summary>"
            f"<ul>{items}</ul></details>"
        )
    if done_tasks:
        items = "".join(_task_li(t) for t in done_tasks)
        out.append(
            f"<details class='tasks'><summary>Completed ({len(done_tasks)})</summary>"
            f"<ul>{items}</ul></details>"
        )
    return "".join(out)


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
        status = html.escape(p["status"]) or "unknown"
        missing = "" if p["exists"] else " <span class='health-fail'>(no .horus/)</span>"
        cards.append(
            f"<div class='card'><h2><a href='/project?i={i}'>"
            f"{html.escape(p['name'])}</a>{missing}</h2>"
            f"<div class='badges'><span>status: {status}</span>"
            f"{_features_badge(p)}"
            f"<span>{len(p['sessions'])} session(s)</span> {_health_summary(p['findings'])}</div>"
            f"{_next_html(p)}"
            f"{_latest_html(p)}"
            f"{_progress_html(p, href=f'/project?i={i}#roadmap')}"
            f"<p class='muted' style='font-size:12px'>{html.escape(p['path'])}</p></div>"
        )
    return _page("Horus", "".join(cards))


def render_project(p: dict[str, Any]) -> str:
    parts = [
        "<p class='back'><a href='/'>&larr; all projects</a></p>",
        f"<h1 style='margin-top:6px'>{html.escape(p['name'])}</h1>",
        f"<div class='badges'><span>status: {html.escape(p['status']) or 'unknown'}</span>"
        f"{_health_summary(p['findings'])}</div>",
        _next_html(p),
        _latest_html(p),
        _progress_html(p, href="#roadmap"),
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

    if p["tasks"] or p["roadmap_body"]:
        pr = p["progress"]
        heading = "Roadmap"
        if pr["total"]:
            heading += f" <span class='muted' style='font-size:13px'>({pr['done']}/{pr['total']} done)</span>"
        parts.append(
            f"<div class='section' id='roadmap'><h2>{heading}</h2>{_breakdown_html(p)}</div>"
        )

    if p["features_body"]:
        fc = p["feature_counts"]
        sub = f" <span class='muted' style='font-size:13px'>({fc['shipped']} shipped)</span>" if fc["shipped"] else ""
        parts.append(
            f"<div class='section' id='features'><h2>Features{sub}</h2>"
            f"{markdown.render(p['features_body'])}</div>"
        )

    if p["sessions"]:
        srows = "".join(
            f"<tr><td>{html.escape(s['date'])}</td><td>{html.escape(s['agent'])}</td>"
            f"<td>{html.escape(s['account'])}</td>"
            f"<td>{html.escape(s['status'])}</td><td>{html.escape(s['summary'])}</td></tr>"
            for s in p["sessions"]
        )
        parts.append(
            "<div class='section'><h2>Recent sessions</h2>"
            "<table><tr><th>date</th><th>agent</th><th>account</th><th>status</th><th>summary</th></tr>"
            f"{srows}</table></div>"
        )

    if p["decisions_body"]:
        parts.append(
            f"<div class='section'><h2>Decisions</h2>{markdown.render(p['decisions_body'])}</div>"
        )

    if p["history_body"]:
        parts.append(
            "<div class='section' id='history'><h2>History</h2>"
            "<details class='tasks'><summary>bumps in the road</summary>"
            f"{markdown.render(p['history_body'])}</details></div>"
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
