"""Local-only multi-project dashboard.

Serves an overview of every project registered in ``~/.horus/config.toml`` plus a
per-project detail view rendered from that repo's `.horus/` files. Reads are
side-effect-free and never touch arbitrary files (projects are addressed by their
index in the config list, never by a path from the request).

The one mutating action is the Control tab's **launch** button (``POST /launch``):
it opens an attended agent session in its own terminal via :mod:`horus.launch` —
the same path as ``horus open``. Inputs are constrained to keep the read surface's
guarantees: projects are still addressed by index, accounts validated against the
known set, and the POST is same-origin-guarded (the server binds loopback only).
"""

from __future__ import annotations

import html
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

from horus import (
    claude_usage,
    codex_usage,
    config,
    frontmatter,
    gitstate,
    launch,
    markdown,
    registry,
    roadmap,
    routines,
)
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


def _account_usage(alias: str, cred_path: Path | None) -> dict[str, Any]:
    report = claude_usage.latest_usage(cred_path=cred_path)
    reset = report.five_hour_resets_at if report else None
    return {
        "alias": alias,
        "five_pct": report.five_hour_percent if report else None,
        "week_pct": report.seven_day_percent if report else None,
        "five_reset": claude_usage._fmt_reset(reset) if reset else None,
    }


def gather_accounts() -> list[dict[str, Any]]:
    """Every Horus-known Claude account with its live usage (best-effort, read-only).

    Reads the per-account ``CLAUDE_CONFIG_DIR`` isolation map (accounts.toml) and
    adds the ambient login if it isn't one of them. Accounts are shown by alias, not
    raw email (the alias privacy rule). Network failure / no token -> gray ring.
    """
    # ponytail: one live usage GET per account, sequential. Parallelize only if a
    # large account list ever makes the page drag — a handful is fine.
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for alias, d in sorted(config.load_account_config_dirs().items()):
        out.append(_account_usage(alias, Path(d) / ".credentials.json"))
        seen.add(alias)
    ambient_alias = config.alias_for(claude_usage.current_account())
    if ambient_alias and ambient_alias not in seen:
        out.append(_account_usage(ambient_alias, None))  # ambient credentials path
    return out


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
nav { margin-top: 10px; display: flex; gap: 18px; align-items: center; }
nav a { color: #8a93a6; font-size: 13px; padding-bottom: 4px; border-bottom: 2px solid transparent; }
nav a.active { color: #e6e6e6; border-bottom-color: #6db3f2; }
nav a:hover { text-decoration: none; color: #e6e6e6; }
nav a.live-badge { margin-left: auto; color: #57d39a; font-size: 12px; padding: 2px 11px;
                   border: 1px solid #1f5138; background: #15281d; border-radius: 999px; }
nav a.live-badge:hover { border-color: #2e7d52; }
.live-dot { animation: livepulse 1.6s ease-in-out infinite; }
@keyframes livepulse { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
.control { display: grid; grid-template-columns: 280px 1fr; gap: 18px; align-items: start; }
main.wide { max-width: none; }
.acct { display: flex; align-items: center; gap: 12px; margin: 12px 0; }
.acct .who { font-size: 14px; font-weight: 600; }
svg.ring text { font-family: -apple-system, Segoe UI, sans-serif; font-weight: 600; }
.proj-row { display: flex; justify-content: space-between; align-items: center;
            padding: 8px 0; border-bottom: 1px solid #1c1f2a; }
.proj-row:last-child { border-bottom: 0; }
details.launch > summary { list-style: none; cursor: pointer; color: #57d39a; font-size: 13px;
            padding: 2px 9px; border: 1px solid #1f5138; border-radius: 6px; background: #15281d; }
details.launch > summary::-webkit-details-marker { display: none; }
.launch-body { margin-top: 8px; }
.cmd { display: flex; align-items: center; gap: 6px; margin: 4px 0; }
.cmd code { flex: 1; font-size: 11px; white-space: pre-wrap; overflow-wrap: anywhere; }
.sessions-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); }
.scard { background: #151823; border: 1px solid #232733; border-radius: 10px; padding: 16px 18px; }
.scard-h { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.scard-t { font-size: 16px; font-weight: 600; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #232733; color: #b9c2d0; }
.usagebar { height: 14px; background: #232733; border-radius: 4px; overflow: hidden; margin: 12px 0 4px; }
.usagebar > span { display: block; height: 100%; }
form.launch-form { margin: 8px 0 4px; display: flex; flex-direction: column; gap: 8px; }
form.launch-form label { font-size: 12px; color: #b9c2d0; }
form.launch-form select { background: #0b0d12; color: #e6e6e6; border: 1px solid #284058;
            border-radius: 6px; padding: 3px 6px; font-size: 12px; margin-left: 4px; }
form.launch-form .modes { display: flex; flex-direction: column; gap: 3px; }
form.launch-form .modes label { display: flex; align-items: center; gap: 6px; }
button.start { font: inherit; cursor: pointer; }
form.acct-launch { margin-left: auto; }
.or-cmds { margin-top: 6px; }
.or-cmds > summary { cursor: pointer; font-size: 11px; color: #8a93a6; list-style: none; }
.or-cmds > summary::-webkit-details-marker { display: none; }
.banner { border-radius: 8px; padding: 9px 13px; margin: 0 0 16px; font-size: 13px; }
.banner.ok { background: #15281d; border: 1px solid #1f5138; color: #aee9c8; }
.banner.err { background: #2e1b1b; border: 1px solid #5c2a2a; color: #f0b3b3; }
"""

_LEVEL_CLASS = {"ok": "health-ok", "warn": "health-warn", "fail": "health-fail"}


def _live_count(records: list[registry.SessionRecord]) -> int:
    """Native agent sessions currently running (a live process)."""
    return sum(1 for r in records if r.status == "running")


def _nav(active: str, live: int = 0) -> str:
    links = [("/", "Projects", "projects"), ("/control", "Control", "control")]
    items = "".join(
        f"<a href='{href}'{' class=\"active\"' if key == active else ''}>{label}</a>"
        for href, label, key in links
    )
    badge = ""
    if live:
        s = "" if live == 1 else "s"
        badge = (
            f"<a href='/control' class='live-badge' title='{live} live native session{s} running'>"
            f"<span class='live-dot'>&#9679;</span> {live} live</a>"
        )
    return f"<nav>{items}{badge}</nav>"


def _page(title: str, body: str, active: str = "projects", wide: bool = False, live: int = 0) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style></head><body>"
        "<header><h1>Horus</h1>"
        "<div class='sub'>project continuity &amp; control panel</div>"
        f"{_nav(active, live)}</header>"
        f"<main{' class=\"wide\"' if wide else ''}>{body}</main>"
        "<script>"
        "function horusCopy(btn){"
        "var t=btn.closest('.resume').querySelector('.resume-text').textContent;"
        "navigator.clipboard.writeText(t).then(function(){"
        "var o=btn.textContent;btn.textContent='Copied';"
        "setTimeout(function(){btn.textContent=o;},1200);});}"
        "function horusCopyPrev(btn){"
        "navigator.clipboard.writeText(btn.previousElementSibling.textContent).then(function(){"
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


_SESSION_STATUS_CLASS = {
    "running": "health-ok",
    "failed": "health-fail",
    "orphaned": "health-warn",
    "exited": "muted",
}


def gather_sessions() -> list[registry.SessionRecord]:
    """Reconcile the registry against live PIDs, then return records newest-first."""
    reg = registry.Registry.default()
    reg.reconcile()  # correct records left "running" by a crashed/closed run
    return sorted(reg.all(), key=lambda r: r.updated_at, reverse=True)


def render_sessions_card(records: list[registry.SessionRecord]) -> str:
    if not records:
        return (
            "<div class='card'><h2>Live sessions</h2>"
            "<p class='muted'>No tracked agent sessions yet. They appear here once "
            "Horus spawns or resumes one.</p></div>"
        )
    rows = []
    for r in records:
        cls = _SESSION_STATUS_CLASS.get(r.status, "muted")
        rc = "" if r.returncode is None else f" ({r.returncode})"
        rows.append(
            f"<tr><td><span class='{cls}'>&#9679;</span> {html.escape(r.status)}{html.escape(rc)}</td>"
            f"<td>{html.escape(r.agent)}</td>"
            f"<td>{html.escape(r.account or '-')}</td>"
            f"<td>{html.escape(Path(r.project).name)}</td>"
            f"<td>{r.pid if r.pid is not None else '-'}</td>"
            f"<td><code>{html.escape(r.session_id[:8])}</code></td>"
            f"<td class='muted'>{html.escape(r.updated_at)}</td></tr>"
        )
    body = "".join(rows)
    return (
        "<div class='card'><h2>Live sessions</h2>"
        "<table><tr><th>status</th><th>agent</th><th>account</th><th>project</th>"
        "<th>pid</th><th>session</th><th>updated</th></tr>"
        f"{body}</table></div>"
    )


def render_index(projects: list[dict[str, Any]], sessions: list[registry.SessionRecord] | None = None) -> str:
    records = sessions or []
    live = _live_count(records)
    sessions_card = render_sessions_card(records)
    if not projects:
        body = (
            sessions_card
            + "<div class='card'><h2>No projects registered</h2>"
            "<p class='muted'>Run <code>horus init</code> inside a project to "
            "register it here.</p></div>"
        )
        return _page("Horus", body, live=live)
    cols = "".join(_project_column(p, i) for i, p in enumerate(projects))
    return _page("Horus", f"{sessions_card}<div class='columns'>{cols}</div>", live=live)


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

    return _page(f"Horus - {p['name']}", "".join(parts), live=_live_count(gather_sessions()))


# --------------------------------------------------------------------------- #
# Control panel — accounts (usage rings) + projects (launch) + live sessions
# --------------------------------------------------------------------------- #

def _usage_color(pct: float) -> str:
    return "#f08a8a" if pct >= 90 else "#e6c35c" if pct >= 70 else "#57d39a"


def _ring(pct: float | None) -> str:
    """Small donut showing a usage percent; gray when unknown (offline/no token)."""
    if pct is None:
        color, dash, txt = "#3a4151", 0.0, "--"
    else:
        v = max(0.0, min(100.0, pct))
        color, dash, txt = _usage_color(v), v, f"{v:.0f}%"
    return (
        "<svg class='ring' viewBox='0 0 40 40' width='42' height='42'>"
        "<circle cx='20' cy='20' r='16' fill='none' stroke='#232733' stroke-width='4'/>"
        f"<circle cx='20' cy='20' r='16' fill='none' stroke='{color}' stroke-width='4' "
        f"pathLength='100' stroke-dasharray='{dash:.0f} 100' stroke-linecap='round' "
        "transform='rotate(-90 20 20)'/>"
        f"<text x='20' y='24' text-anchor='middle' font-size='11' fill='#e6e6e6'>{txt}</text>"
        "</svg>"
    )


def _usage_bar(pct: float | None, label: str) -> str:
    fill = ""
    if pct is not None:
        v = max(0.0, min(100.0, pct))
        fill = f"<span style='width:{v:.0f}%;background:{_usage_color(v)}'></span>"
    return f"<div class='usagebar'>{fill}</div><div class='progress-label'>{html.escape(label)}</div>"


def _accounts_panel(accounts: list[dict[str, Any]]) -> str:
    if not accounts:
        return (
            "<div class='card'><h2>Accounts</h2>"
            "<p class='muted' style='font-size:13px'>No Claude login detected. Run "
            "<code>claude</code> to sign in, or map isolated accounts with "
            "<code>horus account --set-dir</code>.</p></div>"
        )
    rows = []
    for a in accounts:
        reset = (
            f"<div class='muted' style='font-size:11px'>5h resets {html.escape(a['five_reset'])}</div>"
            if a.get("five_reset")
            else ""
        )
        week = (
            f"<div class='muted' style='font-size:11px'>weekly {a['week_pct']:.0f}%</div>"
            if a.get("week_pct") is not None
            else ""
        )
        rows.append(
            f"<div class='acct'>{_ring(a['five_pct'])}"
            f"<div><div class='who'>{html.escape(a['alias'])}</div>{reset}{week}</div>"
            f"{_account_launch_form(a['alias'])}</div>"
        )
    return f"<div class='card'><h2>Accounts</h2>{''.join(rows)}</div>"


def _account_launch_form(alias: str) -> str:
    """A one-click "fresh session as this account" button (opens in your home dir)."""
    return (
        "<form class='acct-launch' method='post' action='/launch'>"
        f"<input type='hidden' name='account' value='{html.escape(alias, quote=True)}'>"
        "<input type='hidden' name='mode' value='fresh'>"
        "<button class='start' type='submit' title='Open a fresh session as this account'>"
        "+ session</button></form>"
    )


def _launch_cmds(project_path: str, accounts: list[dict[str, Any]]) -> str:
    """Copyable real launch commands: ambient first, then one per known account."""
    cmds = [f'horus open "{project_path}"']
    cmds += [f'horus open "{project_path}" --account {a["alias"]}' for a in accounts]
    return "".join(
        f"<div class='cmd'><code>{html.escape(c)}</code>"
        "<button class='copy' type='button' onclick='horusCopyPrev(this)'>Copy</button></div>"
        for c in cmds
    )


def _project_launch_form(i: int, project: dict[str, Any], accounts: list[dict[str, Any]]) -> str:
    """Pick an account + fresh-or-resume, then launch (POST). Mirrors the sketch's
    "select acc and select fresh session or resume" flow on the project play button."""
    opts = "<option value=''>ambient (logged-in)</option>" + "".join(
        f"<option value='{html.escape(a['alias'], quote=True)}'>{html.escape(a['alias'])}</option>"
        for a in accounts
    )
    return (
        "<form class='launch-form' method='post' action='/launch'>"
        f"<input type='hidden' name='project' value='{i}'>"
        f"<label>Account <select name='account'>{opts}</select></label>"
        "<div class='modes'>"
        "<label><input type='radio' name='mode' value='fresh' checked> Fresh session</label>"
        "<label><input type='radio' name='mode' value='resume'> Resume (inject continuity prompt)</label>"
        "</div>"
        "<button class='start' type='submit'>Launch &#9654;</button>"
        "</form>"
        "<details class='or-cmds'><summary>&#8230; or run it in your own terminal</summary>"
        f"<div class='launch-body'>{_launch_cmds(project['path'], accounts)}</div></details>"
    )


def _projects_panel(projects: list[dict[str, Any]], accounts: list[dict[str, Any]]) -> str:
    if not projects:
        return "<div class='card'><h2>Projects</h2><p class='muted'>None registered.</p></div>"
    rows = []
    for i, p in enumerate(projects):
        rows.append(
            f"<div class='proj-row'><a href='/project?i={i}'>{html.escape(p['name'])}</a>"
            "<details class='launch'><summary title='Launch a session'>&#9654;</summary>"
            f"<div class='launch-body'>{_project_launch_form(i, p, accounts)}</div></details></div>"
        )
    return f"<div class='card'><h2>Projects</h2>{''.join(rows)}</div>"


def _control_session_card(rec: registry.SessionRecord, accounts: list[dict[str, Any]]) -> str:
    """A live-session column: status, account usage bar, and (Codex) context window."""
    acct = next((a for a in accounts if a["alias"] == rec.account), None)
    pct = acct["five_pct"] if acct else None
    label_bits = []

    context_line = ""
    if rec.agent == "codex":
        cu = codex_usage.latest_usage(Path(rec.project))
        if cu:
            context_line = (
                "<div class='progress-label'>context "
                f"{cu.context_tokens // 1000}K / {cu.context_window // 1000}K "
                f"({cu.context_percent:.0f}%)</div>"
            )
            if pct is None and cu.primary_percent is not None:
                pct = cu.primary_percent

    label_bits.append(f"5h limit {pct:.0f}%" if pct is not None else "usage unknown")
    if acct and acct.get("five_reset"):
        label_bits.append(f"resets {acct['five_reset']}")

    dot_cls = _SESSION_STATUS_CLASS.get(rec.status, "muted")
    meta = (
        f"<div class='muted' style='font-size:12px'><span class='{dot_cls}'>&#9679;</span> "
        f"{html.escape(rec.status)} &middot; {html.escape(rec.agent)} &middot; "
        f"pid {rec.pid if rec.pid is not None else '-'}</div>"
    )
    return (
        f"<div class='scard'><div class='scard-h'>"
        f"<span class='scard-t'>{html.escape(Path(rec.project).name)}</span>"
        f"<span class='pill'>{html.escape(rec.account or 'ambient')}</span></div>"
        f"{meta}{_usage_bar(pct, ' · '.join(label_bits))}{context_line}"
        f"{_reopen_html(rec)}"
        f"<div class='muted' style='font-size:11px;margin-top:8px'>session "
        f"<code>{html.escape(rec.session_id[:8])}</code> &middot; updated {html.escape(rec.updated_at)}</div>"
        "</div>"
    )


def _reopen_html(rec: registry.SessionRecord) -> str:
    """Copyable commands to jump to this session's native window.

    The dashboard is read-only and a browser can't raise a desktop window, so the
    shortcut is the exact command to run: `horus focus` raises the *running* window;
    `claude --resume` opens a fresh view (Claude-only resume-by-id today).
    """
    focus = f"horus focus {rec.session_id[:8]}"
    block = (
        "<div class='cmd' style='margin-top:8px'>"
        f"<code>{html.escape(focus)}</code>"
        "<button class='copy' type='button' onclick='horusCopyPrev(this)'>Copy</button></div>"
        "<div class='muted' style='font-size:11px'>raise the running window</div>"
    )
    if rec.agent == "claude":
        reopen = f'cd "{rec.project}"\nclaude --resume {rec.session_id}'
        block += (
            "<div class='cmd' style='margin-top:6px'>"
            f"<code>{html.escape(reopen)}</code>"
            "<button class='copy' type='button' onclick='horusCopyPrev(this)'>Copy</button></div>"
            "<div class='muted' style='font-size:11px'>or reopen in a new window</div>"
        )
    return block


def _launch_notice(params: dict[str, list[str]]) -> str:
    """Banner shown after a launch POST redirects back to /control."""
    if "launched" in params:
        sid = html.escape(params["launched"][0])
        return (
            f"<div class='banner ok'>Launched session <code>{sid}</code> in a new "
            "terminal &mdash; it appears below once its process is up.</div>"
        )
    if "error" in params:
        return f"<div class='banner err'>Launch failed: {html.escape(params['error'][0])}</div>"
    return ""


def render_control(
    projects: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    sessions: list[registry.SessionRecord],
    notice: str = "",
) -> str:
    # Live processes only (per the design): a session is "live" while its process runs.
    live = [s for s in sessions if s.status == "running"]
    cards = "".join(_control_session_card(s, accounts) for s in live) or (
        "<p class='muted'>No live sessions. Launch one from an account or project on "
        "the left; it appears here while its process runs.</p>"
    )
    body = (
        f"{notice}<div class='control'><div class='sidebar'>"
        f"{_accounts_panel(accounts)}{_projects_panel(projects, accounts)}</div>"
        f"<div class='sessions-grid'>{cards}</div></div>"
    )
    return _page("Horus - Control", body, active="control", wide=True, live=len(live))


# --------------------------------------------------------------------------- #
# Launch (the one mutating action): POST /launch -> horus.launch
# --------------------------------------------------------------------------- #

def _known_aliases() -> set[str]:
    """Account aliases the dashboard will accept on a launch POST — the isolated
    config-dir map plus the ambient login. No network (unlike ``gather_accounts``)."""
    aliases = set(config.load_account_config_dirs())
    ambient = config.alias_for(claude_usage.current_account())
    if ambient:
        aliases.add(ambient)
    return aliases


def process_launch(
    form: dict[str, str],
    *,
    projects: list[str] | None = None,
    known_aliases: set[str] | None = None,
) -> str:
    """Handle a Control-tab launch request; return the query string to redirect
    ``/control`` to (``launched=<id8>`` or ``error=<reason>``).

    Safety mirrors the read surface: a project is addressed by its **index** into
    the registered list (never an arbitrary path), and an account must be in the
    **known** set. An empty project means an account-only quick session, opened in
    the user's home directory.
    """
    projects = config.load_projects() if projects is None else projects
    known = _known_aliases() if known_aliases is None else known_aliases

    account = (form.get("account") or "").strip() or None
    if account is not None and account not in known:
        return "error=" + quote_plus("unknown account")

    mode = (form.get("mode") or "fresh").strip()
    agent = (form.get("agent") or "claude").strip()
    raw_project = (form.get("project") or "").strip()

    prompt = ""
    if raw_project == "":
        project_dir: Path = Path.home()  # account-only quick session
    else:
        try:
            project_dir = Path(projects[int(raw_project)])
        except (ValueError, IndexError):
            return "error=" + quote_plus("unknown project")
        if mode == "resume":
            prompt = _resume_prompt_text(load_project(str(project_dir)))

    result = launch.launch_interactive(
        agent=agent, project_dir=project_dir, account=account, prompt=prompt,
    )
    if not result.ok:
        return "error=" + quote_plus(result.error or "launch failed")
    return f"launched={result.session_id[:8]}"


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
            self._send(render_index(gather_projects(), gather_sessions()))
            return
        if parsed.path == "/sessions":
            recs = gather_sessions()
            self._send(_page("Horus — sessions", render_sessions_card(recs), live=_live_count(recs)))
            return
        if parsed.path == "/control":
            notice = _launch_notice(parse_qs(parsed.query))
            self._send(render_control(gather_projects(), gather_accounts(), gather_sessions(), notice))
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

    def _same_origin(self) -> bool:
        """Reject cross-origin POSTs (CSRF guard for the loopback server).

        A browser sends ``Origin`` on cross-site form/fetch POSTs; if present it must
        match our ``Host``. Absent ``Origin`` means a non-browser client (e.g. curl)
        on loopback, which is allowed — the server binds 127.0.0.1 only.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        host = self.headers.get("Host", "")
        return origin in (f"http://{host}", f"https://{host}")

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        if parsed.path != "/launch":
            self._send(_page("Not found", "<p>Not found.</p>"), 404)
            return
        if not self._same_origin():
            self._send(_page("Forbidden", "<p>Cross-origin request refused.</p>"), 403)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        form = {k: v[0] for k, v in parse_qs(raw).items()}
        query = process_launch(form)
        # 303 -> GET /control so a refresh doesn't re-submit the launch (PRG pattern).
        self.send_response(303)
        self.send_header("Location", f"/control?{query}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args: Any) -> None:  # silence default stderr logging
        pass


class _SingleInstanceServer(ThreadingHTTPServer):
    # One dashboard per port. ``ThreadingHTTPServer`` defaults ``allow_reuse_address``
    # to True; on Windows SO_REUSEADDR lets *multiple* sockets bind the same port at
    # once, so every ``horus dashboard`` invocation used to bind 8765 and the OS routed
    # requests to an arbitrary (often stale) one — which left the UI showing an old
    # in-memory build. False makes a second bind fail fast, so a duplicate launch
    # refuses instead of piling up.
    allow_reuse_address = False


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    try:
        server = _SingleInstanceServer((host, port), _Handler)
    except OSError:
        print(f"Horus dashboard already running at http://{host}:{port}; not starting another.")
        return
    count = len(config.load_projects())
    print(f"Horus dashboard: http://{host}:{port}  ({count} project(s))")
    print("Read-only. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
