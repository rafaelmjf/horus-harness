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

from horus import codex_usage, config, frontmatter, gitstate, markdown, roadmap, routines
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
        "next_prompt": "",
        "tagline": "",
        "project_body": "",
        "roadmap_body": "",
        "features_body": "",
        "feature_counts": {"shipped": 0, "in_progress": 0, "planned": 0},
        "feature_items": {"shipped": [], "in_progress": [], "planned": []},
        "decisions_body": "",
        "history_body": "",
        "sessions": [],
        "findings": [],
        "next_action": "",
        "latest": None,
        "latest_body": "",
        "progress": {"done": 0, "total": 0, "pct": 0},
        "tasks": [],
        "git": gitstate.git_state(root),
    }
    if not hdir.is_dir():
        return data

    project_md = hdir / "project.md"
    if project_md.is_file():
        doc = frontmatter.parse(project_md.read_text(encoding="utf-8"))
        data["status"] = doc.front_matter.get("status", "")
        data["current_focus"] = doc.front_matter.get("current_focus", "")
        data["project_body"] = doc.body
        data["tagline"] = _first_paragraph(doc.body)

    roadmap_md = hdir / "roadmap.md"
    if roadmap_md.is_file():
        doc = frontmatter.parse(roadmap_md.read_text(encoding="utf-8"))
        if not data["current_focus"]:
            data["current_focus"] = doc.front_matter.get("current_focus", "")
        data["next_prompt"] = doc.front_matter.get("next_prompt", "")
        data["next_action"] = doc.front_matter.get("next_action", "")
        data["roadmap_body"] = doc.body

    features_md = hdir / "features.md"
    if features_md.is_file():
        doc = frontmatter.parse(features_md.read_text(encoding="utf-8"))
        data["features_body"] = doc.body
        data["feature_items"] = routines.feature_items(doc.body)
        data["feature_counts"] = {k: len(v) for k, v in data["feature_items"].items()}

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
                "_path": str(sp),
                "_body": doc.body,
            }
        )

    # Sort newest-first by frontmatter date, then mtime, then filename, so
    # "latest" is correct even when several summaries share a date.
    data["sessions"].sort(key=lambda s: (s["date"], s["mtime"], s["file"]), reverse=True)
    data["latest"] = data["sessions"][0] if data["sessions"] else None
    if data["latest"]:
        data["latest_body"] = data["latest"]["_body"]

    # The single best next step is agent-authored (roadmap.md `next_action`), not
    # inferred here. We still parse the checkbox list for the progress bar and the
    # "remaining items" display — that renders what the agent literally wrote.
    tasks = roadmap.parse_tasks(data["roadmap_body"])
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
main { padding: 24px 28px; max-width: 1320px; }
.columns { display: flex; gap: 16px; align-items: flex-start; overflow-x: auto; padding-bottom: 12px; }
.col { flex: 0 0 360px; max-width: 360px; background: #151823; border: 1px solid #232733;
       border-radius: 12px; padding: 14px 16px; }
.col h2 { font-size: 17px; margin: 0 0 2px; }
.col .why { color: #8a93a6; font-size: 13px; font-style: italic; margin: 0 0 10px; }
.box { background: #12141b; border: 1px solid #232733; border-radius: 8px; padding: 8px 12px; margin: 10px 0; }
.box .lbl { display: block; font-size: 11px; letter-spacing: .5px; text-transform: uppercase;
            color: #8a93a6; margin-bottom: 5px; }
.box.inner { margin: 8px 0 2px; background: #0f1115; }
.start { display: inline-block; margin: 6px 0 2px; font-size: 12px; color: #57d39a;
         border: 1px solid #1f5138; background: #15281d; border-radius: 6px; padding: 3px 8px; }
.feat-buckets { display: flex; gap: 10px; }
.feat-buckets > div { flex: 1 1 0; min-width: 0; }
.feat-buckets h4 { margin: 0 0 4px; font-size: 12px; color: #8a93a6; font-weight: 600; }
.feat-buckets ul { list-style: none; padding: 0; margin: 0; }
.feat-buckets li { font-size: 12px; margin: 2px 0; overflow-wrap: anywhere; }
.feat-buckets .idea li { color: #b9a6e0; } .feat-buckets .prog li { color: #e6c35c; }
.feat-buckets .ship li { color: #57d39a; }
.next-one { font-size: 14px; margin: 5px 0 7px; color: #eaf6ee; }
.checklist { list-style: none; padding-left: 0; margin: 4px 0 2px; }
.checklist li { font-size: 12px; margin: 3px 0; color: #b9c2d0; overflow-wrap: anywhere; }
.summary-scroll { max-height: 200px; overflow: auto; margin-top: 4px; font-size: 13px; }
.summary-scroll p, .summary-scroll li { margin: 4px 0; }
.resume { margin-top: 8px; }
.resume-head { display: flex; align-items: center; justify-content: space-between; }
.resume-text { font-size: 12px; color: #cdd6e4; background: #0b0d12; border: 1px solid #232733;
               border-radius: 6px; padding: 7px 9px; margin-top: 4px; white-space: pre-wrap; overflow-wrap: anywhere; }
.copy { font-size: 11px; color: #6db3f2; background: #0b0d12; border: 1px solid #284058;
        border-radius: 6px; padding: 2px 9px; cursor: pointer; }
.copy:hover { background: #16202b; }
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
.git { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px !important; }
.git.stale { background: #2e2718 !important; color: #e6c35c; }
.session-body { background: #12141b; border: 1px solid #232733; border-left: 3px solid #6db3f2;
                border-radius: 8px; padding: 4px 16px; }
.session-body .meta { color: #8a93a6; font-size: 12px; }
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
        f"<main>{body}</main>"
        "<script>"
        "function horusCopy(btn){"
        "var t=btn.closest('.resume').querySelector('.resume-text').textContent;"
        "navigator.clipboard.writeText(t).then(function(){"
        "var o=btn.textContent;btn.textContent='Copied';"
        "setTimeout(function(){btn.textContent=o;},1200);});}"
        "</script>"
        "</body></html>"
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


def _first_paragraph(body: str) -> str:
    """First real paragraph of a doc body — the project's 'why this exists' one-liner."""
    for raw in body.splitlines():
        line = raw.strip()
        if line and not line.startswith(("#", "-", "*", ">", "|", "```")):
            return _plain(line)
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
    # Fall back to a title derived from the filename when frontmatter has no summary.
    fallback = re.sub(r"^\d{4}-\d{2}-\d{2}(-\d{6})?-|\.md$", "", latest["file"]).replace("-", " ")
    summary = html.escape(latest["summary"] or fallback) or "(no summary)"
    return (
        f"<div class='latest'><span class='date'>{html.escape(latest['date'])}</span> "
        f"&middot; {summary}</div>"
    )


def _git_badge(p: dict[str, Any]) -> str:
    """Compact git freshness chip for the overview card."""
    g = p.get("git")
    if not g:
        return ""
    bits = [html.escape(g["branch"])]
    if g["commit"].get("rel"):
        bits.append(html.escape(g["commit"]["rel"]))
    stale = False
    if g["upstream"] is None:
        bits.append("no upstream")
    else:
        if g["behind"]:
            bits.append(f"&#8595;{g['behind']}")  # behind origin
            stale = True
        if g["ahead"]:
            bits.append(f"&#8593;{g['ahead']}")  # ahead of origin
    if g["dirty"]:
        bits.append("uncommitted")
        stale = True
    cls = "git stale" if stale else "git"
    return f"<span class='{cls}'>{' &middot; '.join(bits)}</span>"


def _git_html(p: dict[str, Any]) -> str:
    """Full git block for the project detail view."""
    g = p.get("git")
    if not g:
        return ""
    c = g["commit"]
    rows = [f"<strong>branch:</strong> {html.escape(g['branch'])}"]
    if c.get("hash"):
        rows.append(
            f"<strong>last commit:</strong> {html.escape(c['hash'])} "
            f"&middot; {html.escape(c.get('rel', ''))} &middot; {html.escape(c.get('subject', ''))}"
        )
    if g["upstream"] is None:
        rows.append("<span class='health-warn'>no upstream tracking branch</span>")
    elif g["behind"] or g["ahead"]:
        sync = []
        if g["behind"]:
            sync.append(f"behind origin by {g['behind']} &mdash; <code>git pull --ff-only</code>")
        if g["ahead"]:
            sync.append(f"ahead by {g['ahead']}")
        rows.append("<span class='health-warn'>" + "; ".join(sync) + "</span>")
    else:
        rows.append("<span class='health-ok'>up to date with origin</span>")
    if g["dirty"]:
        rows.append("<span class='health-warn'>uncommitted changes in the working tree</span>")
    if g["remote_url"]:
        rows.append(f"<span class='muted'>{html.escape(g['remote_url'])}</span>")
    body = "<br>".join(rows)
    return f"<div class='card'><h2 style='font-size:14px'>Git</h2>{body}</div>"


def _latest_session_card(p: dict[str, Any]) -> str:
    """The most recent session summary, rendered in full."""
    latest = p.get("latest")
    body = p.get("latest_body", "")
    if not latest or not body.strip():
        return ""
    meta = " &middot; ".join(
        html.escape(latest[k]) for k in ("date", "agent", "account") if latest.get(k)
    )
    return (
        "<div class='section'><h2>Latest session</h2>"
        f"<div class='session-body'><p class='meta'>{meta}</p>"
        f"{markdown.render(body)}</div></div>"
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


def _best_next_text(p: dict[str, Any]) -> str:
    """The single best next step — agent-authored in roadmap.md `next_action`.

    Not inferred from the checkbox list: the agent records it at closure. Empty
    until then (the dashboard shows a prompt to author it)."""
    return (p.get("next_action") or "").strip()


def _single_next_html(p: dict[str, Any]) -> str:
    """Highlight the ONE authored next action (roadmap.md next_action)."""
    text = _best_next_text(p)
    if text:
        return (
            "<div class='next'><span class='lbl'>NEXT</span>"
            f"<div class='next-one'>{html.escape(_plain(text))}</div></div>"
        )
    if p["progress"]["total"] and p["progress"]["done"] == p["progress"]["total"]:
        return "<div class='next done'><span class='lbl'>NEXT</span> &#10003; roadmap complete</div>"
    return "<div class='next'><span class='lbl'>NEXT</span><div class='next-one muted'>not set — author <code>next_action</code> in roadmap.md at closure</div></div>"


def _resume_prompt_text(p: dict[str, Any]) -> str:
    """The natural-language prompt to resume this project in a fresh Claude/Codex session.

    Authored by the closure skill into roadmap.md `next_prompt`. When absent, fall back
    to a generic paste-able prompt built from the next step (display convenience only).
    """
    written = (p.get("next_prompt") or "").strip()
    if written:
        return written
    nxt = _best_next_text(p)
    base = (
        f"Continue work on the {p['name']} project. First read .horus/ for context "
        f"(project.md, roadmap.md, decisions.md, and the latest .horus/sessions/ summary)."
    )
    return f"{base} Then start on the next step: {nxt}" if nxt else base


def _resume_html(p: dict[str, Any]) -> str:
    """Paste-into-Claude/Codex resume prompt with a copy button."""
    prompt = _resume_prompt_text(p)
    if not prompt:
        return ""
    return (
        "<div class='resume'><div class='resume-head'><span class='lbl'>Resume prompt</span>"
        "<button class='copy' type='button' onclick='horusCopy(this)'>Copy</button></div>"
        f"<div class='resume-text'>{html.escape(prompt)}</div></div>"
    )


def _remaining_items_html(p: dict[str, Any], limit: int = 8) -> str:
    """The rest of the open roadmap items as a plain empty-checkbox list."""
    open_tasks = [t for t in p["tasks"] if t["state"] in ("todo", "partial")]
    highlighted = _best_next_text(p).lower()
    rest = [t for t in open_tasks if _plain(t["text"]).lower() != highlighted]
    if not rest:
        return ""
    items = "".join(f"<li>&#9744; {html.escape(_plain(t['text']))}</li>" for t in rest[:limit])
    return f"<div class='box inner'><span class='lbl'>Remaining roadmap items</span><ul class='checklist'>{items}</ul></div>"


def _session_summary_excerpt(body: str) -> str:
    """The agent's written summary of the latest session: the `## Summary` section
    if present, else the prose after the leading title."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("##") and "summary" in s.lower():
            out = []
            for nxt in lines[i + 1:]:
                if nxt.strip().startswith("#"):
                    break
                out.append(nxt)
            text = "\n".join(out).strip()
            if text:
                return text
    body = body.strip()
    if body.startswith("#"):  # drop the leading H1 title
        nl = body.find("\n")
        body = body[nl + 1:].strip() if nl != -1 else ""
    return body


def _last_session_summary_html(p: dict[str, Any]) -> str:
    """The verbose summary the agent wrote, not just the date."""
    latest = p.get("latest")
    if not latest:
        return "<div class='latest muted'>no sessions yet</div>"
    date = html.escape(latest.get("date", ""))
    datetag = f"<span class='date'>{date}</span>" if date else ""
    text = _session_summary_excerpt(p.get("latest_body", ""))
    if text:
        return f"{datetag}<div class='summary-scroll'>{markdown.render(text)}</div>"
    one = html.escape(latest.get("summary", "")) or "(no summary)"
    return f"{datetag}<p class='latest'>{one}</p>"


def _features_buckets_html(p: dict[str, Any]) -> str:
    fi = p["feature_items"]
    if not any(fi.values()):
        return ""

    def bucket(label: str, key: str, cls: str) -> str:
        lis = "".join(f"<li>{html.escape(n)}</li>" for n in fi[key][:8]) or "<li class='muted'>—</li>"
        return f"<div class='{cls}'><h4>{html.escape(label)}</h4><ul>{lis}</ul></div>"

    return (
        "<div class='box'><span class='lbl'>Main features</span><div class='feat-buckets'>"
        + bucket("Idea", "planned", "idea")
        + bucket("In progress", "in_progress", "prog")
        + bucket("Shipped", "shipped", "ship")
        + "</div></div>"
    )


def _project_column(p: dict[str, Any], i: int) -> str:
    missing = "" if p["exists"] else " <span class='health-fail'>(no .horus/)</span>"
    why = f"<p class='why'>{html.escape(p['tagline'])}</p>" if p["tagline"] else ""
    pills = (
        f"<div class='badges'><span>status: {html.escape(p['status']) or 'unknown'}</span>"
        f"<span>{len(p['sessions'])} session(s)</span> {_git_badge(p)} {_health_summary(p['findings'])}</div>"
    )
    last = f"<div class='box'><span class='lbl'>Last session summary</span>{_last_session_summary_html(p)}</div>"
    roadmap = (
        "<div class='box'><span class='lbl'>Roadmap</span>"
        f"{_single_next_html(p)}{_resume_html(p)}"
        f"{_progress_html(p, href=f'/project?i={i}#roadmap')}"
        f"{_remaining_items_html(p)}</div>"
    )
    return (
        f"<div class='col'><h2><a href='/project?i={i}'>{html.escape(p['name'])}</a>{missing}</h2>"
        f"{why}{pills}{last}{roadmap}{_features_buckets_html(p)}</div>"
    )


def render_index(projects: list[dict[str, Any]]) -> str:
    if not projects:
        body = (
            "<div class='card'><h2>No projects registered</h2>"
            "<p class='muted'>Run <code>horus init</code> inside a project to "
            "register it here.</p></div>"
        )
        return _page("Horus", body)
    cols = "".join(_project_column(p, i) for i, p in enumerate(projects))
    return _page("Horus", f"<div class='columns'>{cols}</div>")


def render_project(p: dict[str, Any]) -> str:
    parts = [
        "<p class='back'><a href='/'>&larr; all projects</a></p>",
        f"<h1 style='margin-top:6px'>{html.escape(p['name'])}</h1>",
        f"<div class='badges'><span>status: {html.escape(p['status']) or 'unknown'}</span>"
        f"{_health_summary(p['findings'])}</div>",
        _single_next_html(p),
        _resume_html(p),
        _latest_html(p),
        _progress_html(p, href="#roadmap"),
    ]

    if p["current_focus"]:
        parts.append(
            f"<div class='card'><strong>Current focus:</strong> "
            f"{html.escape(p['current_focus'])}</div>"
        )

    parts.append(_git_html(p))
    parts.append(_latest_session_card(p))

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
