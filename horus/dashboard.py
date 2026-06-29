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
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

from importlib import resources

from horus import (
    __version__,
    adapters,
    cache_status,
    claude_usage,
    codex_usage,
    config,
    frontmatter,
    gitstate,
    github_catalog,
    launch,
    launcher,
    markdown,
    overhead,
    pty_host,
    registry,
    remote_start,
    roadmap,
    routines,
    upgrade,
)
from horus.continuity import HORUS_DIR, check_project, horus_dir, recent_sessions

_REMOTE_REFRESH_LOCK = threading.Lock()
_REMOTE_REFRESHING: set[str] = set()


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
        "execution_body": "",
        "execution_status": "",
        "feature_counts": {"shipped": 0, "in_progress": 0, "planned": 0},
        "feature_items": {"shipped": [], "in_progress": [], "planned": []},
        "decisions_body": "",
        "history_body": "",
        "sessions": [],
        "findings": [],
        "artifacts_stale": False,
        "artifacts_stale_count": 0,
        "next_action": "",
        "execution_recommendation": "",
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
        data["execution_recommendation"] = doc.front_matter.get("execution_recommendation", "")
        data["roadmap_body"] = doc.body

    features_md = hdir / "features.md"
    if features_md.is_file():
        doc = frontmatter.parse(features_md.read_text(encoding="utf-8"))
        data["features_body"] = doc.body
        data["feature_items"] = routines.feature_items(doc.body)
        data["feature_counts"] = {k: len(v) for k, v in data["feature_items"].items()}

    execution_md = hdir / "execution.md"
    if execution_md.is_file():
        doc = frontmatter.parse(execution_md.read_text(encoding="utf-8"))
        data["execution_body"] = doc.body
        data["execution_status"] = doc.front_matter.get("status", "")

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

    try:
        actions = upgrade.upgrade_project(root, apply=False)
        stale = [a for a in actions if a.status == "would-update"]
        data["artifacts_stale"] = bool(stale)
        data["artifacts_stale_count"] = len(stale)
    except Exception:
        # never let a projection check break the dashboard render
        data["artifacts_stale"] = False

    return data


def gather_projects() -> list[dict[str, Any]]:
    return [load_project(p) for p in config.load_projects()]


def gather_remote_projects() -> tuple[list[github_catalog.RemoteProject], list[str], list[str]]:
    projects: list[github_catalog.RemoteProject] = []
    errors: list[str] = []
    notes: list[str] = []
    local = config.load_projects()
    for owner in config.load_github_owners():
        cached = github_catalog.load_cache(owner, local_projects=local)
        if cached is not None:
            projects.extend(cached.projects)
            if cached.fetched_at:
                notes.append(f"{owner}: showing cached results from {cached.fetched_at}; refreshing in background")
            else:
                notes.append(f"{owner}: showing cached results; refreshing in background")
            if cached.error:
                when = f" at {cached.error_at}" if cached.error_at else ""
                errors.append(f"{owner}: last refresh failed{when}: {cached.error}")
            _start_remote_refresh(owner, local)
            continue
        try:
            projects.extend(github_catalog.refresh_cache(owner, local_projects=local))
        except RuntimeError as exc:
            errors.append(f"{owner}: {exc}")
    return projects, errors, notes


def force_refresh_remote(owner: str) -> tuple[list[github_catalog.RemoteProject], list[str], list[str]]:
    local = config.load_projects()
    result = github_catalog.force_refresh(owner, local_projects=local)
    notes: list[str] = []
    errors: list[str] = []
    if result.ok:
        when = f" at {result.fetched_at}" if result.fetched_at else ""
        notes.append(f"{owner}: force-refresh updated {result.count} Horus-enabled repo(s){when}")
    else:
        errors.append(f"{owner}: force-refresh failed: {result.error}")
    cached = github_catalog.load_cache(owner, local_projects=local)
    return (cached.projects if cached else [], errors, notes)


def gather_untracked_repos() -> tuple[list[github_catalog.UntrackedRepo], list[github_catalog.UntrackedRepo]]:
    """Return (visible, hidden) untracked repos from the on-disk cache for all configured owners.

    Does NOT trigger a network refresh — the existing ``gather_remote_projects`` background
    refresh already repopulates the cache (including untracked).  This reads what is already
    on disk so the render stays fast.
    """
    local = config.load_projects()
    all_untracked: list[github_catalog.UntrackedRepo] = []
    for owner in config.load_github_owners():
        cached = github_catalog.load_cache(owner, local_projects=local)
        if cached is not None:
            all_untracked.extend(cached.untracked)
    return github_catalog.filter_ignored(all_untracked)


def _start_remote_refresh(owner: str, local_projects: list[str]) -> None:
    with _REMOTE_REFRESH_LOCK:
        if owner in _REMOTE_REFRESHING:
            return
        _REMOTE_REFRESHING.add(owner)

    def refresh() -> None:
        try:
            github_catalog.refresh_cache(owner, local_projects=local_projects)
        except RuntimeError:
            pass
        finally:
            with _REMOTE_REFRESH_LOCK:
                _REMOTE_REFRESHING.discard(owner)

    threading.Thread(target=refresh, daemon=True).start()


def _account_usage(alias: str, cred_path: Path | None, *, config_dir: Path | None = None) -> dict[str, Any]:
    report = claude_usage.latest_usage(cred_path=cred_path)
    reset = report.five_hour_resets_at if report else None
    week_reset = report.seven_day_resets_at if report else None
    return {
        "agent": "claude",
        "alias": alias,
        "mapped_path": str(config_dir) if config_dir else "",
        "five_pct": report.five_hour_percent if report else None,
        "week_pct": report.seven_day_percent if report else None,
        "five_reset": claude_usage._fmt_reset(reset) if reset else None,
        "week_reset": claude_usage._fmt_reset(week_reset) if week_reset else None,
    }


def _codex_account_usage(alias: str, home: Path | None) -> dict[str, Any]:
    """A Codex account row with its 5h/weekly rate limits (best-effort, read-only).

    Codex has no live usage endpoint, so the percentages are the *last observed*
    rate-limit snapshot from this account's rollouts (account-global, only as
    fresh as the last Codex activity). ``used_percent`` semantics match the Claude
    ring (the ring fills as you consume) — note this is the inverse of the Codex
    app's "remaining" framing. No rollout reporting limits yet -> gray ring.
    """
    report = codex_usage.latest_account_usage(home=home)
    reset = report.primary_resets_at if report else None
    week_reset = report.secondary_resets_at if report else None
    return {
        "agent": "codex",
        "alias": alias,
        "mapped_path": str(home) if home else "",
        "five_pct": report.primary_percent if report else None,
        "week_pct": report.secondary_percent if report else None,
        "five_reset": codex_usage._fmt_reset(reset) if reset is not None else None,
        "week_reset": codex_usage._fmt_reset(week_reset) if week_reset is not None else None,
    }


def gather_accounts() -> list[dict[str, Any]]:
    """Every Horus-known account (Claude + Codex) with usage where available.

    Claude accounts: read ``CLAUDE_CONFIG_DIR`` isolation map + ambient login;
    usage comes from the OAuth ``/usage`` endpoint (best-effort, may be gray).
    Codex accounts: read ``CODEX_HOME`` isolation map + ambient ``~/.codex``;
    usage is the last-observed 5h/weekly rate-limit snapshot from rollouts (no
    live API), gray until a rollout has reported limits.
    Accounts are shown by alias, not raw email/id (alias privacy rule).
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # --- Claude accounts ---
    for alias, d in sorted(config.load_account_config_dirs().items()):
        cfg = Path(d)
        out.append(_account_usage(alias, cfg / ".credentials.json", config_dir=cfg))
        seen.add(alias)
    ambient_claude = config.alias_for(claude_usage.current_account())
    if ambient_claude and ambient_claude not in seen:
        out.append(_account_usage(ambient_claude, None))
        seen.add(ambient_claude)

    # --- Codex accounts ---
    codex_seen: set[str] = set()
    for alias, d in sorted(config.load_account_codex_homes().items()):
        out.append(_codex_account_usage(alias, Path(d)))
        codex_seen.add(alias)
    # Ambient Codex: show once when no explicit homes are configured and ~/.codex exists.
    if not codex_seen:
        ambient_codex_id = codex_usage.current_account()
        if ambient_codex_id:
            ambient_codex_alias = config.alias_for(ambient_codex_id)
            if ambient_codex_alias:
                out.append(_codex_account_usage(ambient_codex_alias, None))  # ambient ~/.codex

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
.remote-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.remote-card { background: #151823; border: 1px solid #232733; border-radius: 10px; padding: 13px 15px; }
.remote-card h3 { margin: 0 0 4px; font-size: 15px; }
.remote-card .next-one { font-size: 13px; }
.remote-card code { overflow-wrap: anywhere; }
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
.next-mode { margin-top: 7px; font-size: 12px; color: #cdd6e4; }
.next-mode strong { color: #57d39a; font-weight: 600; }
.next-mode .why { color: #8a93a6; }
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
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 8px 0 12px; }
.metric { background: #12141b; border: 1px solid #232733; border-radius: 8px; padding: 9px 11px; }
.metric .num { display: block; font-size: 18px; color: #eaf6ee; font-weight: 600; }
.metric .lbl { display: block; font-size: 11px; color: #8a93a6; text-transform: uppercase; letter-spacing: .4px; }
.metric .sub { display: block; font-size: 12px; color: #8a93a6; margin-top: 2px; }
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
.usagebar { height: 8px; background: #232733; border-radius: 4px; overflow: hidden; margin: 12px 0 4px; }
.usagebar > span { display: block; height: 100%; }
form.launch-form { margin: 8px 0 4px; display: flex; flex-direction: column; gap: 8px; }
form.launch-form label { font-size: 12px; color: #b9c2d0; }
form.launch-form select { background: #0b0d12; color: #e6e6e6; border: 1px solid #284058;
            border-radius: 6px; padding: 3px 6px; font-size: 12px; margin-left: 4px; }
form.launch-form .modes { display: flex; flex-direction: column; gap: 3px; }
form.launch-form .modes label { display: flex; align-items: center; gap: 6px; }
button.start { font: inherit; cursor: pointer; }
form.acct-launch { margin-left: auto; }
.acct-edit { margin-top: 4px; display: flex; gap: 5px; align-items: center; }
.acct-edit input { width: 118px; min-width: 0; background: #0b0d12; color: #e6e6e6;
                   border: 1px solid #284058; border-radius: 5px; padding: 3px 5px; font-size: 12px; }
.or-cmds { margin-top: 6px; }
.or-cmds > summary { cursor: pointer; font-size: 11px; color: #8a93a6; list-style: none; }
.or-cmds > summary::-webkit-details-marker { display: none; }
.banner { border-radius: 8px; padding: 9px 13px; margin: 0 0 16px; font-size: 13px; }
.banner.ok { background: #15281d; border: 1px solid #1f5138; color: #aee9c8; }
.banner.err { background: #2e1b1b; border: 1px solid #5c2a2a; color: #f0b3b3; }
button.start.primary { width: 100%; text-align: center; padding: 7px 10px; font-size: 13px; }
button.linkbtn { display: block; margin: 6px 0 0; padding: 0; background: none; border: none;
            color: #8a93a6; font: inherit; font-size: 11px; cursor: pointer; text-decoration: underline dotted; }
button.linkbtn:hover { color: #b9c2d0; }
.control-main { min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.termpanel { min-width: 0; }
.term-tabs { display: flex; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid #232733;
            margin: 6px 0 0; padding-bottom: 0; }
.term-tab { font: inherit; font-size: 12px; cursor: pointer; color: #b9c2d0; background: #12141b;
            border: 1px solid #232733; border-bottom: none; border-radius: 7px 7px 0 0;
            padding: 6px 12px; display: flex; align-items: center; gap: 7px; margin-bottom: -1px; }
.term-tab.active { background: #0b0d12; color: #e6e6e6; border-color: #284058; }
.tdot { width: 8px; height: 8px; border-radius: 50%; background: #3a4151; display: inline-block; }
.tdot.s-running { background: #57d39a; animation: livepulse 1.6s ease-in-out infinite; }
.tdot.s-idle { background: #6db3f2; } .tdot.s-failed { background: #f08a8a; }
.tdot.s-exited { background: #3a4151; }
.term-pane { display: none; background: #0b0d12; border: 1px solid #284058;
            border-radius: 0 8px 8px 8px; padding: 8px; }
.term-pane.active { display: block; }
.term-bar { display: flex; justify-content: space-between; align-items: center; padding: 0 4px 6px; }
.term-bar .popout { margin: 0; }
.xterm-host { height: 420px; }
.xterm-host .xterm { height: 100%; }
"""

_LEVEL_CLASS = {"ok": "health-ok", "warn": "health-warn", "fail": "health-fail"}


def _live_count(records: list[registry.SessionRecord]) -> int:
    """Native agent sessions currently running (a live process)."""
    return sum(1 for r in records if r.status == "running")


def _nav(active: str, live: int = 0) -> str:
    links = [("/", "Projects", "projects"), ("/control", "Control", "control"), ("/settings", "Settings", "settings")]
    items = "".join(
        f"<a href='{href}'{_active_class(key == active)}>{label}</a>"
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


def _active_class(active: bool) -> str:
    return ' class="active"' if active else ""


def _page(title: str, body: str, active: str = "projects", wide: bool = False, live: int = 0) -> str:
    icon_key = html.escape(__version__, quote=True)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        f"<link rel='icon' href='/favicon.ico?v={icon_key}' sizes='any'>"
        f"<link rel='icon' type='image/png' href='/assets/icon.png?v={icon_key}'>"
        f"<style>{_STYLE}</style></head><body>"
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
        "document.querySelectorAll('[data-horus-src]').forEach(function(el){"
        "fetch(el.getAttribute('data-horus-src')).then(function(r){return r.text();})"
        ".then(function(html){el.outerHTML=html;})"
        ".catch(function(){el.innerHTML=\"<div class='banner err'>GitHub catalog failed to load.</div>\";});"
        "});"
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


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _fmt_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    if total < 60:
        return f"{total}s"
    minutes = total // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    rem = minutes % 60
    return f"{hours}h {rem}m" if rem else f"{hours}h"


def _project_overhead_html(project_path: str) -> str:
    """Aggregate-only token overhead card for one project detail view."""
    root = Path(project_path).resolve()
    try:
        static_total = sum(item.estimated_tokens for item in overhead.static_footprint())
        summaries = [overhead.codex_overhead(root), overhead.claude_overhead(root)]
        reg = registry.Registry.default()
        reg.reconcile()
        records = [r for r in reg.all() if r.agent in ("claude", "codex") and Path(r.project).resolve() == root]
        session_rows = overhead.session_usages(records)
    except Exception as exc:
        return (
            "<div class='section'><h2>Token overhead</h2>"
            f"<div class='card'><span class='health-warn'>unavailable:</span> {html.escape(str(exc))}</div></div>"
        )

    observed_total = sum(s.total.total_tokens for s in summaries)
    observed_horus = sum(s.horus.total_tokens for s in summaries)
    observed_pct = (observed_horus / observed_total * 100.0) if observed_total else 0.0
    matched_sessions = [s for s in session_rows if s.matched]

    metrics = (
        "<div class='metric-grid'>"
        f"<div class='metric'><span class='num'>{_fmt_int(static_total)}</span><span class='lbl'>static tokens est.</span></div>"
        f"<div class='metric'><span class='num'>{_fmt_int(observed_horus)}</span><span class='lbl'>observed Horus-related</span></div>"
        f"<div class='metric'><span class='num'>{observed_pct:.1f}%</span><span class='lbl'>upper-bound share</span></div>"
        f"<div class='metric'><span class='num'>{len(matched_sessions)}/{len(session_rows)}</span><span class='lbl'>sessions matched</span></div>"
        "</div>"
    )

    usage_rows = "".join(
        f"<tr><td>{html.escape(s.agent)}</td><td>{s.horus_turns}/{s.turns}</td>"
        f"<td>{_fmt_int(s.horus.total_tokens)}</td><td>{_fmt_int(s.total.total_tokens)}</td></tr>"
        for s in summaries
    )
    usage_table = (
        "<table><tr><th>agent</th><th>Horus turns</th><th>Horus-related tokens</th><th>total observed</th></tr>"
        f"{usage_rows}</table>"
    )

    if session_rows:
        srows = "".join(
            f"<tr><td>{html.escape(row.agent)}</td><td><code>{html.escape(row.session_id[:8])}</code></td>"
            f"<td>{html.escape(row.status)}</td><td>{row.turns if row.matched else '-'}</td>"
            f"<td>{_fmt_int(row.total.total_tokens) if row.matched else html.escape(row.note)}</td></tr>"
            for row in session_rows[:8]
        )
        session_table = (
            "<details class='tasks'><summary>Tracked sessions</summary>"
            "<table><tr><th>agent</th><th>session</th><th>status</th><th>turns</th><th>tokens / note</th></tr>"
            f"{srows}</table></details>"
        )
    else:
        session_table = "<p class='muted'>No tracked Claude/Codex sessions for this project.</p>"

    return (
        "<div class='section' id='overhead'><h2>Token overhead</h2>"
        "<p class='muted'>Aggregate-only local estimate. Observed usage is upper-bound attribution, not a counterfactual.</p>"
        f"{metrics}{usage_table}{session_table}</div>"
    )


def _project_cache_html(project_path: str) -> str:
    """Prompt-cache freshness estimate for one project detail view."""
    try:
        statuses = cache_status.project_cache_status(Path(project_path))
    except Exception as exc:
        return (
            "<div class='section'><h2>Context cache</h2>"
            f"<div class='card'><span class='health-warn'>unavailable:</span> {html.escape(str(exc))}</div></div>"
        )

    if not statuses:
        return (
            "<div class='section'><h2>Context cache</h2>"
            "<div class='card'><p class='muted'>No local Claude/Codex cache signal for this project yet.</p></div></div>"
        )

    cards = "".join(_cache_metric(s) for s in statuses)
    return (
        "<div class='section' id='context-cache'><h2>Context cache</h2>"
        "<p class='muted'>Local estimate from native token logs. Likely cold after 5 minutes; "
        "expired after 60 minutes of no project turns.</p>"
        f"<div class='metric-grid'>{cards}</div></div>"
    )


def _cache_metric(status: cache_status.CacheStatus) -> str:
    state = status.state()
    cls = "health-ok" if state == "warm" else ("health-fail" if state == "expired" else "health-warn")
    age = _fmt_duration(status.age_seconds())
    ttl = _fmt_duration(status.seconds_until_expiry())
    cache_bits = []
    if status.cached_input_tokens:
        cache_bits.append(f"cached {_fmt_int(status.cached_input_tokens)}")
    if status.cache_read_input_tokens:
        cache_bits.append(f"read {_fmt_int(status.cache_read_input_tokens)}")
    if status.cache_creation_input_tokens:
        cache_bits.append(f"write {_fmt_int(status.cache_creation_input_tokens)}")
    cache_text = ", ".join(cache_bits) if cache_bits else "no cache tokens in last turn"
    ttl_text = "expired" if state == "expired" else f"{ttl} until 60m"
    return (
        "<div class='metric'>"
        f"<span class='lbl'>{html.escape(status.agent)}</span>"
        f"<span class='num {cls}'>{html.escape(state)}</span>"
        f"<span class='sub'>last turn {age} ago · {ttl_text}</span>"
        f"<span class='sub'>{html.escape(cache_text)} · total {_fmt_int(status.total_tokens)}</span>"
        "</div>"
    )


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
    recommendation = (p.get("execution_recommendation") or "").strip()
    rec_html = _execution_recommendation_html(recommendation)
    if text:
        return (
            "<div class='next'><span class='lbl'>NEXT</span>"
            f"<div class='next-one'>{html.escape(_plain(text))}</div>{rec_html}</div>"
        )
    if p["progress"]["total"] and p["progress"]["done"] == p["progress"]["total"]:
        return "<div class='next done'><span class='lbl'>NEXT</span> &#10003; roadmap complete</div>"
    return "<div class='next'><span class='lbl'>NEXT</span><div class='next-one muted'>not set — author <code>next_action</code> in roadmap.md at closure</div></div>"


def _execution_recommendation_html(recommendation: str) -> str:
    rec = _plain(recommendation).strip()
    if not rec:
        return ""
    low = rec.lower()
    if "plan-execution" in low:
        mode = "Craft execution.md + delegate bounded tasks"
    elif "continue-as-is" in low:
        mode = "Proceed directly with the frontier model"
    else:
        mode = "Planner should choose direct vs delegated"
    return (
        "<div class='next-mode'><strong>Recommended mode:</strong> "
        f"{html.escape(mode)}"
        f"<div class='why'>{html.escape(rec)}</div></div>"
    )


def _resume_prompt_text(p: dict[str, Any]) -> str:
    """The paste-able fresh-session handoff for this project."""
    return routines.resume_prompt(Path(p["path"]))


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
    _artifacts_pill = (
        "<span class='health-warn' title='Run: horus upgrade-project --apply'>&#9888; artifacts outdated</span>"
        if p["artifacts_stale"]
        else ""
    )
    pills = (
        f"<div class='badges'><span>status: {html.escape(p['status']) or 'unknown'}</span>"
        f"<span>{len(p['sessions'])} session(s)</span> {_git_badge(p)} {_health_summary(p['findings'])}"
        f"{_artifacts_pill}</div>"
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


def _remote_project_card(p: github_catalog.RemoteProject) -> str:
    badge_class = "health-ok" if p.is_local else "health-warn"
    badge_text = "cloned here" if p.is_local else "remote only"
    focus = f"<p class='muted'>{html.escape(p.current_focus)}</p>" if p.current_focus else ""
    next_action = (
        "<div class='next'><span class='lbl'>NEXT</span>"
        f"<div class='next-one'>{html.escape(_plain(p.next_action))}</div></div>"
        if p.next_action
        else ""
    )
    if p.local_path:
        command = f"cd {p.local_path} && horus open"
    else:
        command = f"horus start github:{p.full_name}"
    return (
        "<div class='remote-card'>"
        f"<h3><a href='{html.escape(p.url)}'>{html.escape(p.full_name)}</a></h3>"
        f"<div class='badges'><span>{html.escape(p.default_branch)}</span>"
        f"<span class='{badge_class}'>{badge_text}</span></div>"
        f"{focus}{next_action}"
        "<div class='resume'><span class='lbl'>Start here</span>"
        f"<div class='resume-text'><code>{html.escape(command)}</code></div></div>"
        "</div>"
    )


def _refresh_forms() -> str:
    owners = config.load_github_owners()
    if not owners:
        return ""
    forms = []
    for owner in owners:
        forms.append(
            "<form method='post' action='/github-refresh' style='display:inline-block;margin-right:8px'>"
            f"<input type='hidden' name='owner' value='{html.escape(owner)}'>"
            f"<button class='copy' type='submit'>Refresh {html.escape(owner)}</button>"
            "</form>"
        )
    return "<div style='margin:0 0 12px'>" + "".join(forms) + "</div>"


def _untracked_card(u: github_catalog.UntrackedRepo) -> str:
    badge_class = "health-warn" if u.is_local else "muted"
    badge_text = "cloned, not initialized" if u.is_local else "remote only"
    description = f"<p class='muted'>{html.escape(u.description)}</p>" if u.description else ""
    onboard_form = (
        "<form method='post' action='/github-onboard' style='display:inline-block;margin-right:8px'>"
        f"<input type='hidden' name='target' value='{html.escape(u.full_name)}'>"
        "<button class='copy' type='submit'>Onboard</button>"
        "</form>"
    )
    ignore_form = (
        "<form method='post' action='/github-ignore' style='display:inline-block'>"
        f"<input type='hidden' name='target' value='{html.escape(u.full_name)}'>"
        "<button class='copy' type='submit'>Ignore</button>"
        "</form>"
    )
    return (
        "<div class='remote-card'>"
        f"<h3><a href='{html.escape(u.url)}'>{html.escape(u.full_name)}</a></h3>"
        f"<div class='badges'><span>{html.escape(u.default_branch)}</span>"
        f"<span class='{badge_class}'>{badge_text}</span></div>"
        f"{description}"
        "<p class='muted' style='font-size:12px'>Onboard uses this machine's "
        "<code>gh</code> GitHub login for clone/PR; Claude/Codex account choice happens "
        "when you launch work on the project.</p>"
        f"<div style='margin-top:8px'>{onboard_form}{ignore_form}</div>"
        "</div>"
    )


def _hidden_row(u: github_catalog.UntrackedRepo) -> str:
    unignore_form = (
        "<form method='post' action='/github-unignore' style='display:inline-block;margin-left:8px'>"
        f"<input type='hidden' name='target' value='{html.escape(u.full_name)}'>"
        "<button class='copy' type='submit'>Unignore</button>"
        "</form>"
    )
    return (
        f"<div style='padding:4px 0'>{html.escape(u.full_name)}{unignore_form}</div>"
    )


def render_remote_catalog(
    projects: list[github_catalog.RemoteProject],
    errors: list[str],
    notes: list[str] | None = None,
    untracked: list[github_catalog.UntrackedRepo] | None = None,
    hidden: list[github_catalog.UntrackedRepo] | None = None,
) -> str:
    _untracked = untracked or []
    _hidden = hidden or []
    if not projects and not errors and not notes and not _untracked and not _hidden:
        # Distinguish between "no owners configured" and "owners set but nothing found".
        if not config.load_github_owners():
            return (
                "<div class='section'><h2>GitHub remote catalog</h2>"
                "<div class='card health-warn'>"
                "<p><strong>No GitHub owner configured on this machine.</strong></p>"
                "<p class='muted'>GitHub owners and workspace paths are per-machine and are not"
                " git-synced, so a fresh machine always starts empty.</p>"
                "<p class='muted'>Run <code>horus discover github &lt;owner&gt; --save</code>"
                " to add an owner and see your remote projects here.</p>"
                "</div></div>"
            )
        return (
            "<div class='section'><h2>GitHub remote catalog</h2>"
            "<div class='card'><p class='muted'>No Horus-enabled remote repos found yet.</p></div></div>"
        )
    cards = "".join(_remote_project_card(p) for p in projects)
    if not cards:
        cards = "<div class='card'><p class='muted'>No Horus-enabled remote repos found yet.</p></div>"
    if notes:
        msg = "".join(f"<li>{html.escape(n)}</li>" for n in notes)
        cards = f"<div class='banner ok'><strong>GitHub catalog cache</strong><ul>{msg}</ul></div>{cards}"
    if errors:
        err = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        cards = f"<div class='banner err'><strong>GitHub discovery issue</strong><ul>{err}</ul></div>{cards}"
    horus_grid = f"<div class='remote-grid'>{cards}</div>"

    untracked_section = ""
    if _untracked:
        untracked_cards = "".join(_untracked_card(u) for u in _untracked)
        untracked_section = (
            f"<h2>Not tracked ({len(_untracked)})</h2>"
            f"<div class='remote-grid'>{untracked_cards}</div>"
        )

    hidden_section = ""
    if _hidden:
        hidden_rows = "".join(_hidden_row(u) for u in _hidden)
        hidden_section = (
            f"<details><summary>Hidden ({len(_hidden)})</summary>"
            f"<div style='padding:8px 0'>{hidden_rows}</div>"
            "</details>"
        )

    return (
        f"<div class='section'><h2>GitHub remote catalog</h2>"
        f"{_refresh_forms()}"
        f"{horus_grid}"
        f"{untracked_section}"
        f"{hidden_section}"
        "</div>"
    )


def render_remote_catalog_placeholder() -> str:
    if not config.load_github_owners():
        return render_remote_catalog([], [])
    return (
        "<div id='github-catalog' class='section' data-horus-src='/github-catalog'>"
        "<h2>GitHub remote catalog</h2>"
        "<div class='card'><p class='muted'>Loading GitHub projects...</p></div>"
        "</div>"
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


def render_settings(policy: dict[str, str], *, saved: bool = False) -> str:
    """Return the inner body HTML for the /settings page (workflow policy editor)."""
    _labels = {"integration": "Integration", "commit": "Commit", "merge": "Merge"}
    banner = "<div class='banner ok'>Settings saved.</div>" if saved else ""
    selects = []
    for key, label in _labels.items():
        opts = "".join(
            f"<option value='{html.escape(v, quote=True)}'"
            f"{' selected' if v == policy.get(key) else ''}>{html.escape(v)}</option>"
            for v in config.WORKFLOW_CHOICES[key]
        )
        selects.append(
            f"<label>{html.escape(label)}<select name='{html.escape(key, quote=True)}'>{opts}</select></label>"
        )
    controls = "".join(selects)
    return (
        f"{banner}"
        "<div class='card'>"
        "<h2>Workflow policy</h2>"
        "<p class='muted'>Default git-integration policy for Horus-driven actions "
        "(onboard, closure commits). This setting is <strong>per-machine</strong> — "
        "it is not git-synced.</p>"
        f"<form method='post' action='/settings'>{controls}"
        "<button type='submit'>Save</button>"
        "</form></div>"
    )


def render_index(
    projects: list[dict[str, Any]],
    sessions: list[registry.SessionRecord] | None = None,
) -> str:
    records = sessions or []
    live = _live_count(records)
    sessions_card = render_sessions_card(records)
    remote = render_remote_catalog_placeholder()
    if not projects:
        body = (
            sessions_card
            + "<div class='card'><h2>No projects registered</h2>"
            "<p class='muted'>Run <code>horus init</code> inside a project to "
            "register it here.</p></div>"
            + remote
        )
        return _page("Horus", body, live=live)
    cols = "".join(_project_column(p, i) for i, p in enumerate(projects))
    return _page("Horus", f"{sessions_card}<div class='columns'>{cols}</div>{remote}", live=live)


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
    if p["artifacts_stale"]:
        _count = html.escape(str(p["artifacts_stale_count"]))
        parts.append(
            f"<div class='card'><span class='health-warn'>&#9888; Horus artifacts outdated</span>"
            f" &mdash; {_count} item(s) behind the installed CLI."
            f" Run: <code>horus upgrade-project --apply</code></div>"
        )
    parts.append(_project_cache_html(p["path"]))
    parts.append(_project_overhead_html(p["path"]))
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

    if p["execution_body"]:
        status = (
            f" <span class='muted' style='font-size:13px'>({html.escape(p['execution_status'])})</span>"
            if p["execution_status"]
            else ""
        )
        parts.append(
            f"<div class='section' id='execution'><h2>Execution plan{status}</h2>"
            f"{markdown.render(p['execution_body'])}</div>"
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
    add_form = _account_add_form()
    if not accounts:
        return (
            "<div class='card'><h2>Accounts</h2>"
            "<p class='muted' style='font-size:13px'>No Claude login detected. Run "
            "<code>claude</code> to sign in, or map isolated accounts with "
            "<code>horus account --set-dir</code>.</p>"
            f"{add_form}</div>"
        )
    rows = []
    for a in accounts:
        agent = a.get("agent", "claude")
        badge_color = "#4a9eff" if agent == "claude" else "#9b7fe8"
        badge = (
            f"<span style='font-size:10px;font-weight:600;letter-spacing:.4px;"
            f"text-transform:uppercase;color:{badge_color};margin-left:4px'>{html.escape(agent)}</span>"
        )
        reset = (
            f"<div class='muted' style='font-size:11px'>5h resets {html.escape(a['five_reset'])}</div>"
            if a.get("five_reset")
            else ""
        )
        # Weekly usage as a full-card-width bar under the row (used%, like the ring).
        week_bar = ""
        if a.get("week_pct") is not None:
            label = f"Weekly {a['week_pct']:.0f}%"
            if a.get("week_reset"):
                label += f" · resets {a['week_reset']}"
            week_bar = _usage_bar(a["week_pct"], label)
        rows.append(
            f"<div class='acct'>{_ring(a['five_pct'])}"
            f"<div><div class='who'>{html.escape(a['alias'])}{badge}</div>{reset}"
            f"{_account_alias_form(a)}</div>"
            f"{_account_launch_form(a['alias'], agent)}</div>"
            f"{week_bar}"
        )
    return f"<div class='card'><h2>Accounts</h2>{''.join(rows)}{add_form}</div>"


def _account_alias_form(account: dict[str, Any]) -> str:
    alias = account.get("alias", "")
    agent = account.get("agent", "claude")
    return (
        "<form class='acct-edit' method='post' action='/account-alias'>"
        f"<input type='hidden' name='agent' value='{html.escape(agent, quote=True)}'>"
        f"<input type='hidden' name='old_alias' value='{html.escape(alias, quote=True)}'>"
        f"<input name='alias' value='{html.escape(alias, quote=True)}' aria-label='Account alias'>"
        "<button class='copy' type='submit'>Save alias</button>"
        "</form>"
    )


def _account_add_form() -> str:
    return (
        "<details class='or-cmds'><summary>Add account</summary>"
        "<form class='launch-form' method='post' action='/account-login'>"
        "<label>Agent <select name='agent'>"
        "<option value='claude'>Claude</option><option value='codex'>Codex</option>"
        "</select></label>"
        "<label>Alias <input name='alias' placeholder='personal' required></label>"
        "<button class='start primary' type='submit'>Add &amp; sign in</button>"
        "<p class='muted' style='font-size:12px;margin:0'>Creates an isolated login directory "
        "under <code>~/.horus/accounts/</code> and opens a terminal to sign in &mdash; no path to "
        "enter. The directory is filled by the login itself.</p>"
        "</form></details>"
    )


def _account_launch_form(alias: str, agent: str = "claude") -> str:
    """A one-click "fresh session as this account" button (opens an in-app tab)."""
    return (
        "<form class='acct-launch' method='post' action='/launch'>"
        f"<input type='hidden' name='account' value='{html.escape(alias, quote=True)}'>"
        f"<input type='hidden' name='agent' value='{html.escape(agent, quote=True)}'>"
        "<input type='hidden' name='mode' value='fresh'>"
        "<button class='start' type='submit' name='target' value='app' "
        "title='Open a fresh in-app session as this account'>+ session</button></form>"
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


# Permission postures offered at launch (value = PermissionPosture value, so
# process_launch maps it straight through; the adapter turns it into Claude's
# --permission-mode). Default first. Changeable later inside the TUI (shift+tab).
_POSTURE_CHOICES = (
    ("default", "Ask (default)"),
    ("plan", "Plan only"),
    ("auto-edit", "Accept edits"),
    ("full-auto", "Bypass all prompts"),
)
_POSTURE_OPTIONS = "".join(
    f"<option value='{v}'{' selected' if v == 'default' else ''}>{html.escape(label)}</option>"
    for v, label in _POSTURE_CHOICES
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
        f"<label>Permissions <select name='posture'>{_POSTURE_OPTIONS}</select></label>"
        "<div class='modes'>"
        "<label><input type='radio' name='mode' value='fresh' checked> Fresh session</label>"
        "<label><input type='radio' name='mode' value='resume'> Resume (inject continuity prompt)</label>"
        "</div>"
        "<button class='start primary' type='submit' name='target' value='app'>"
        "&#9654; Open terminal in app</button>"
        "<button class='linkbtn' type='submit' name='target' value='window' "
        "title='Open the real claude TUI in its own OS console window'>"
        "or open in a separate OS window &#10697;</button>"
        "</form>"
        "<details class='or-cmds'><summary>&#8230; or copy a terminal command</summary>"
        f"<div class='launch-body'>{_launch_cmds(project['path'], accounts)}</div></details>"
    )


def render_onboard_handoff(
    name: str, project_index: int | None, project_path: str, accounts: list[dict[str, Any]]
) -> str:
    """Post-Onboard handoff: a start-work CTA for the just-tracked project, with an
    account-alias chooser for the first session. Bridges "repo onboarded" → "working on
    it" so the user doesn't have to hunt the new project down on the Control tab.

    ``accounts`` only needs an ``alias`` per entry (no usage rings here)."""
    if project_index is None:
        return ""  # couldn't locate the freshly-registered project; skip the CTA
    if accounts:
        body = _project_launch_form(project_index, {"name": name, "path": project_path}, accounts)
    else:
        body = (
            "<p class='muted'>No agent account is set up yet. Add one under "
            "<a href='/control'>Control &rarr; Add account</a> (it opens a sign-in terminal), "
            "then start a session here.</p>"
        )
    return (
        f"<div class='banner ok'><strong>Onboarded {html.escape(name)} &mdash; start working on it"
        f"</strong><div class='launch-body'>{body}</div></div>"
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

    cache_line = ""
    try:
        if rec.agent == "codex":
            cs = cache_status.latest_codex_cache_status(Path(rec.project))
        elif rec.agent == "claude":
            cs = cache_status.latest_claude_cache_status(Path(rec.project))
        else:
            cs = None
    except Exception:
        cs = None
    if cs is not None:
        state = cs.state()
        cls = "health-ok" if state == "warm" else ("health-fail" if state == "expired" else "health-warn")
        cache_line = (
            f"<div class='progress-label'>cache <span class='{cls}'>{html.escape(state)}</span> "
            f"&middot; last turn {_fmt_duration(cs.age_seconds())} ago "
            f"&middot; {_fmt_int(cs.cache_tokens)} cache tokens</div>"
        )

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
        f"{meta}{_usage_bar(pct, ' · '.join(label_bits))}{context_line}{cache_line}"
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
    if "tab" in params:
        return (
            "<div class='banner ok'>Session opened in the terminal panel below "
            "&mdash; type to drive it.</div>"
        )
    if "launched" in params:
        sid = html.escape(params["launched"][0])
        return (
            f"<div class='banner ok'>Launched session <code>{sid}</code> in a new "
            "window &mdash; it appears under Live sessions once its process is up.</div>"
        )
    if "error" in params:
        return f"<div class='banner err'>Launch failed: {html.escape(params['error'][0])}</div>"
    if params.get("account") == ["added"]:
        return "<div class='banner ok'>Account mapping added.</div>"
    if params.get("account") == ["alias"]:
        return "<div class='banner ok'>Account alias updated.</div>"
    if params.get("account") == ["login-started"]:
        return (
            "<div class='banner ok'>Account created &mdash; a terminal opened to sign in. "
            "Complete the login there; the account is ready to launch once it shows a usage "
            "ring.</div>"
        )
    if "login_error" in params:
        return (
            "<div class='banner err'>Account mapped, but the login terminal could not open: "
            f"{html.escape(params['login_error'][0])}. Sign in manually with the native CLI "
            "using the mapped directory.</div>"
        )
    return ""


def _terminal_panel(terminals: list[pty_host.PtyTerminal]) -> str:
    """The integrated terminal: a tab + real xterm.js terminal per PTY session.

    Each terminal is a real ``claude``/``codex`` TUI running under a pseudo-terminal
    in the session-host (:mod:`horus.pty_host`); its bytes stream here over SSE and
    keystrokes/resizes post back. Sessions persist on the host, so a tab re-attaches
    to the live screen after a reload."""
    if not terminals:
        empty = (
            "<p class='muted'>No in-app terminals yet. Use <strong>Open terminal in app</strong> "
            "on a project, or <strong>+ session</strong> on an account, and the real agent TUI "
            "opens here — you drive it like any terminal.</p>"
        )
        return f"<div class='card termpanel'><h2>Terminal</h2>{empty}</div>"

    tabs, panes = [], []
    for t in terminals:
        tid = html.escape(t.term_id, quote=True)
        title = html.escape(t.title or t.term_id)
        state = "running" if t.alive else "exited"
        tabs.append(
            f"<button class='term-tab' data-tid='{tid}'>"
            f"<span class='tdot s-{state}'></span> {title}</button>"
        )
        panes.append(
            f"<div class='term-pane' data-tid='{tid}'>"
            f"<div class='term-bar'><span class='muted'>{title}</span>"
            f"<button class='popout linkbtn' data-tid='{tid}' title='Open this session in its own window'>"
            "&#10696; pop out</button></div>"
            f"<div class='xterm-host' id='x-{tid}'></div></div>"
        )
    return (
        "<div class='card termpanel'><h2>Terminal</h2>"
        f"<div class='term-tabs'>{''.join(tabs)}</div>"
        f"<div class='term-panes'>{''.join(panes)}</div></div>"
    )


# Vendored xterm.js (local, no CDN). _XTERM_ATTACH_JS defines window.horusAttachTerm,
# shared by the Control panel AND the pop-out window — both are just *viewers* attaching
# to the same host-owned PTY over SSE (bytes in) + POST (keystrokes/resize out). base64
# keeps control bytes intact. The pop-out works precisely because the session persists on
# the host independent of any viewer, so a second window attaches to the same live screen.
_TERMINAL_HEAD = (
    "<link rel='stylesheet' href='/assets/xterm/xterm.css'>"
    "<script src='/assets/xterm/xterm.js'></script>"
    "<script src='/assets/xterm/xterm-addon-fit.js'></script>"
)

_XTERM_ATTACH_JS = """
<script>
window.horusAttachTerm = function(hostId, tid){
  if(typeof Terminal==='undefined') return null;
  function b64bytes(b64){var s=atob(b64);var a=new Uint8Array(s.length);
    for(var i=0;i<s.length;i++){a[i]=s.charCodeAt(i);} return a;}
  function post(path, obj){
    var body=Object.keys(obj).map(function(k){return k+'='+encodeURIComponent(obj[k]);}).join('&');
    fetch(path,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body});
  }
  var term=new Terminal({convertEol:false, cursorBlink:true, fontSize:13,
    fontFamily:'ui-monospace, SFMono-Regular, Consolas, monospace',
    theme:{background:'#0b0d12', foreground:'#e6e6e6'}});
  var fit=new FitAddon.FitAddon(); term.loadAddon(fit);
  term.open(document.getElementById(hostId));
  function sync(){ try{fit.fit();}catch(_){ } if(term.cols>0 && term.rows>0){ post('/pty/resize',{id:tid, cols:term.cols, rows:term.rows}); } }
  term.onData(function(d){ post('/pty/input',{id:tid, data:d}); });
  term.onResize(function(s){ if(s.cols>0 && s.rows>0){ post('/pty/resize',{id:tid, cols:s.cols, rows:s.rows}); } });
  var es=new EventSource('/pty/stream?id='+encodeURIComponent(tid));
  es.addEventListener('output', function(e){ term.write(b64bytes(e.data)); });
  es.addEventListener('status', function(e){
    if(e.data==='exited'){ term.write('\\r\\n\\x1b[2m[process exited]\\x1b[0m\\r\\n'); es.close();
      var d=document.querySelector('.term-tab[data-tid="'+tid+'"] .tdot'); if(d){d.className='tdot s-exited';} }
  });
  setTimeout(sync, 30);
  return {term:term, fit:fit, sync:sync};
};
</script>
"""

_TERMINAL_JS = """
<script>
(function(){
  if(typeof Terminal==='undefined') return;
  var terms={};
  document.querySelectorAll('.term-pane').forEach(function(p){
    terms[p.dataset.tid]=window.horusAttachTerm('x-'+p.dataset.tid, p.dataset.tid);
  });
  function activate(tid){
    document.querySelectorAll('.term-tab').forEach(function(t){t.classList.toggle('active', t.dataset.tid===tid);});
    document.querySelectorAll('.term-pane').forEach(function(p){p.classList.toggle('active', p.dataset.tid===tid);});
    var t=terms[tid]; if(t){ t.sync(); t.term.focus(); }
  }
  document.querySelectorAll('.term-tab').forEach(function(t){
    t.addEventListener('click', function(){activate(t.dataset.tid);});
  });
  document.querySelectorAll('.popout').forEach(function(b){
    b.addEventListener('click', function(e){ e.stopPropagation();
      window.open('/pty/term?id='+encodeURIComponent(b.dataset.tid), 'horus-'+b.dataset.tid,
        'width=940,height=640'); });
  });
  window.addEventListener('resize', function(){
    var a=document.querySelector('.term-pane.active'); if(a&&terms[a.dataset.tid]){terms[a.dataset.tid].sync();}
  });
  var want=new URLSearchParams(location.search).get('tab');
  var first=document.querySelector('.term-tab');
  if(want && document.querySelector('.term-tab[data-tid="'+want+'"]')){activate(want);}
  else if(first){activate(first.dataset.tid);}
})();
</script>
"""


def render_pty_term_page(term_id: str, title: str = "") -> str:
    """Standalone full-window page for a single PTY terminal — the pop-out window.

    Just another viewer attaching to the same host-owned session, so the in-panel
    tab and the pop-out show the same live screen and either can be closed freely."""
    tid = html.escape(term_id, quote=True)
    label = html.escape(title or term_id)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Horus terminal — {label}</title>{_TERMINAL_HEAD}"
        "<style>html,body{margin:0;height:100%;background:#0b0d12;}"
        "#term{position:fixed;inset:0;padding:6px;}</style></head><body>"
        f"<div id='term'></div>{_XTERM_ATTACH_JS}"
        f"<script>window.horusAttachTerm('term', '{tid}');</script>"
        "</body></html>"
    )


def render_control(
    projects: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    sessions: list[registry.SessionRecord],
    notice: str = "",
    terminals: list[pty_host.PtyTerminal] | None = None,
) -> str:
    # Live processes only (per the design): a session is "live" while its process runs.
    live = [s for s in sessions if s.status == "running"]
    cards = "".join(_control_session_card(s, accounts) for s in live) or (
        "<p class='muted'>No windowed sessions. <strong>Separate OS window</strong> on a "
        "project opens the real TUI in its own console; it appears here while it runs.</p>"
    )
    body = (
        f"{_TERMINAL_HEAD}{notice}<div class='control'><div class='sidebar'>"
        f"{_accounts_panel(accounts)}{_projects_panel(projects, accounts)}</div>"
        f"<div class='control-main'>{_terminal_panel(terminals or [])}"
        f"<div class='card'><h2>Windowed sessions</h2>"
        f"<div class='sessions-grid'>{cards}</div></div></div></div>"
        f"{_XTERM_ATTACH_JS}{_TERMINAL_JS}"
    )
    return _page("Horus - Control", body, active="control", wide=True, live=len(live))


# --------------------------------------------------------------------------- #
# Launch (the one mutating action): POST /launch -> horus.launch
# --------------------------------------------------------------------------- #

def _known_aliases() -> set[str]:
    """Account aliases the dashboard will accept on a launch POST.

    Includes isolated config-dir aliases (Claude + Codex), the ambient Claude
    login, and the ambient Codex login. No network (unlike ``gather_accounts``).
    """
    aliases: set[str] = set()
    aliases.update(config.load_account_config_dirs())
    aliases.update(config.load_account_codex_homes())
    ambient_claude = config.alias_for(claude_usage.current_account())
    if ambient_claude:
        aliases.add(ambient_claude)
    ambient_codex_id = codex_usage.current_account()
    if ambient_codex_id:
        ambient_codex = config.alias_for(ambient_codex_id)
        if ambient_codex:
            aliases.add(ambient_codex)
    return aliases


def _identifier_for_alias(agent: str, alias: str) -> str | None:
    for identifier, mapped_alias in config.load_account_aliases().items():
        if mapped_alias == alias:
            return identifier
    if agent == "codex":
        home = config.load_account_codex_homes().get(alias)
        identifier = codex_usage.current_account(Path(home)) if home else codex_usage.current_account()
        return identifier if config.alias_for(identifier) == alias else None
    cfg = config.load_account_config_dirs().get(alias)
    identifier = claude_usage.current_account(Path(cfg) / ".claude.json") if cfg else claude_usage.current_account()
    return identifier if config.alias_for(identifier) == alias else None


def process_account_alias(form: dict[str, str]) -> str:
    agent = (form.get("agent") or "claude").strip()
    old_alias = (form.get("old_alias") or "").strip()
    new_alias = (form.get("alias") or "").strip()
    identifier = _identifier_for_alias(agent, old_alias) if old_alias else None
    if old_alias and new_alias:
        config.rename_account_alias(old_alias, new_alias, identifier=identifier)
    return "account=alias"


def process_account_add(form: dict[str, str]) -> str:
    agent = (form.get("agent") or "claude").strip()
    alias = (form.get("alias") or "").strip()
    path = (form.get("path") or "").strip()
    if not alias or not path:
        return "error=" + quote_plus("account alias and path are required")
    if agent == "codex":
        config.set_account_codex_home(alias, path)
    elif agent == "claude":
        config.set_account_config_dir(alias, path)
    else:
        return "error=" + quote_plus("unknown account agent")
    return "account=added"


def process_account_login(form: dict[str, str], *, launch_login: Any = None) -> str:
    """Account-setup wizard: derive an isolated login dir, record the mapping, and open
    a terminal running the native CLI's login so the *user* fills the dir by signing in.
    No path is asked for — that was the friction this replaces.

    ``launch_login`` is injectable for tests; it defaults to ``launcher.open_terminal``."""
    agent = (form.get("agent") or "claude").strip()
    alias = (form.get("alias") or "").strip()
    if not alias:
        return "error=" + quote_plus("account alias is required")
    if agent not in ("claude", "codex"):
        return "error=" + quote_plus("unknown account agent")

    login_dir = config.account_login_dir(agent, alias)
    # Map the alias now so the account shows in the panel immediately; the login
    # populates the directory with credentials.
    if agent == "codex":
        config.set_account_codex_home(alias, login_dir)
    else:
        config.set_account_config_dir(alias, login_dir)

    launch_login = launch_login or launcher.open_terminal
    try:
        Path(login_dir).mkdir(parents=True, exist_ok=True)
        argv, env = launcher.login_argv_env(agent, login_dir)
        launch_login(argv, Path.home(), env)
    except (OSError, ValueError) as exc:
        # The mapping stands; only the convenience terminal failed (e.g. headless POSIX).
        return "account=mapped&login_error=" + quote_plus(str(exc))
    return "account=login-started"


def _project_index(path: Path) -> int | None:
    """Index of ``path`` in the registered-projects list — the address ``/launch``
    uses — or None if it isn't registered. Match on resolved paths so slash/case
    differences don't miss it."""
    target = str(Path(path).resolve())
    for i, p in enumerate(config.load_projects()):
        try:
            if str(Path(p).resolve()) == target:
                return i
        except OSError:
            continue
    return None


def process_launch(
    form: dict[str, str],
    *,
    projects: list[str] | None = None,
    known_aliases: set[str] | None = None,
) -> str:
    """Handle a Control-tab launch request; return the query string to redirect
    ``/control`` to. ``target=app`` (default) opens an in-app terminal tab
    (``tab=<client_id>``); ``target=window`` opens an OS console (``launched=<id8>``).
    Failures return ``error=<reason>``.

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
    target = (form.get("target") or "app").strip()
    agent = (form.get("agent") or "claude").strip()
    raw_project = (form.get("project") or "").strip()

    posture = (form.get("posture") or "default").strip()
    try:
        adapters.PermissionPosture(posture)  # validate; the adapter maps it to --permission-mode
    except ValueError:
        return "error=" + quote_plus("unknown permission mode")

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

    if target == "app":
        # In-app terminal: spawn the real agent TUI under a PTY in the session-host.
        # Fresh opens an empty TUI; resume seeds it with the continuity prompt.
        try:
            term_id = pty_host.host.start(
                agent=agent, project_dir=project_dir, account=account,
                posture=posture, prompt=(prompt if mode == "resume" else ""),
            )
        except (ValueError, adapters.AccountMismatch) as exc:
            return "error=" + quote_plus(str(exc))
        return f"tab={quote_plus(term_id)}"

    result = launch.launch_interactive(
        agent=agent, project_dir=project_dir, account=account, posture=posture, prompt=prompt,
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

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _valid_github_catalog_target(self, target: str) -> bool:
        owner, sep, name = target.partition("/")
        return bool(owner and sep and name) and owner in config.load_github_owners()

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(render_index(gather_projects(), gather_sessions()))
            return
        if parsed.path == "/github-catalog":
            remote_projects, remote_errors, remote_notes = gather_remote_projects()
            visible_untracked, hidden_untracked = gather_untracked_repos()
            self._send(render_remote_catalog(
                remote_projects, remote_errors, remote_notes,
                untracked=visible_untracked, hidden=hidden_untracked,
            ))
            return
        if parsed.path == "/sessions":
            recs = gather_sessions()
            self._send(_page("Horus — sessions", render_sessions_card(recs), live=_live_count(recs)))
            return
        if parsed.path == "/control":
            notice = _launch_notice(parse_qs(parsed.query))
            self._send(render_control(
                gather_projects(), gather_accounts(), gather_sessions(),
                notice, pty_host.host.terminals(),
            ))
            return
        if parsed.path == "/pty/stream":
            term_id = parse_qs(parsed.query).get("id", [""])[0]
            self._stream_sse(term_id)
            return
        if parsed.path == "/pty/term":
            # Pop-out window: a standalone viewer for one host-owned terminal. Render
            # only for an existing session, using its canonical id (no request value
            # reaches the page markup -> no injection from the ?id= param).
            term = pty_host.host.get(parse_qs(parsed.query).get("id", [""])[0])
            if term is None:
                self._send(_page("Not found", "<p>Unknown terminal.</p>"), 404)
                return
            self._send(render_pty_term_page(term.term_id, term.title))
            return
        if parsed.path.startswith("/assets/xterm/"):
            self._send_asset(parsed.path[len("/assets/xterm/"):])
            return
        if parsed.path == "/favicon.ico":
            self._send_package_asset("icon.ico", "image/x-icon")
            return
        if parsed.path == "/assets/icon.png":
            self._send_package_asset("icon.png", "image/png")
            return
        if parsed.path == "/settings":
            saved = parse_qs(parsed.query).get("saved") == ["1"]
            recs = gather_sessions()
            self._send(_page(
                "Horus — settings",
                render_settings(config.load_workflow_policy(), saved=saved),
                active="settings",
                live=_live_count(recs),
            ))
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

    _ASSET_TYPES = {".js": "application/javascript", ".css": "text/css"}

    def _send_package_asset(self, name: str, content_type: str) -> None:
        if "/" in name or "\\" in name or ".." in name:
            self._send(_page("Not found", "<p>Not found.</p>"), 404)
            return
        try:
            data = resources.files("horus").joinpath("assets", name).read_bytes()
        except (FileNotFoundError, OSError, ModuleNotFoundError):
            self._send(_page("Not found", "<p>Not found.</p>"), 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _send_asset(self, name: str) -> None:
        """Serve a vendored xterm.js asset (local, no CDN). Name is a bare filename."""
        if "/" in name or "\\" in name or ".." in name:  # no path traversal
            self._send(_page("Not found", "<p>Not found.</p>"), 404)
            return
        try:
            data = resources.files("horus").joinpath("assets", "vendor", "xterm", name).read_bytes()
        except (FileNotFoundError, OSError, ModuleNotFoundError):
            self._send(_page("Not found", "<p>Not found.</p>"), 404)
            return
        ctype = self._ASSET_TYPES.get(name[name.rfind("."):], "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _stream_sse(self, term_id: str) -> None:
        """Stream a PTY terminal's bytes as Server-Sent Events until the client
        disconnects (a broken pipe on write ends the loop). The session keeps
        running on the host — detaching a viewer does not kill the terminal."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")  # don't let a proxy buffer the stream
        self.end_headers()
        try:
            for frame in pty_host.host.subscribe(term_id):
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            return  # client detached; the terminal stays alive on the host

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

    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        return {k: v[0] for k, v in parse_qs(raw).items()}

    def _no_content(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        if parsed.path not in (
            "/launch",
            "/settings",
            "/account-add",
            "/account-login",
            "/account-alias",
            "/github-refresh",
            "/github-onboard",
            "/github-ignore",
            "/github-unignore",
            "/pty/input",
            "/pty/resize",
            "/pty/kill",
        ):
            self._send(_page("Not found", "<p>Not found.</p>"), 404)
            return
        if not self._same_origin():
            self._send(_page("Forbidden", "<p>Cross-origin request refused.</p>"), 403)
            return

        if parsed.path == "/settings":
            form = self._read_form()
            try:
                config.set_workflow_policy(
                    integration=form.get("integration") or None,
                    commit=form.get("commit") or None,
                    merge=form.get("merge") or None,
                )
            except ValueError:
                pass  # invalid value from a non-form client — ignore and redirect
            self.send_response(303)
            self.send_header("Location", "/settings?saved=1")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if parsed.path == "/account-add":
            self._redirect(f"/control?{process_account_add(self._read_form())}")
            return
        if parsed.path == "/account-login":
            self._redirect(f"/control?{process_account_login(self._read_form())}")
            return
        if parsed.path == "/account-alias":
            self._redirect(f"/control?{process_account_alias(self._read_form())}")
            return
        if parsed.path == "/pty/input":
            # Keystrokes from an xterm tab → the PTY. Bytes are UTF-8 of the data field.
            form = self._read_form()
            pty_host.host.write(form.get("id", ""), form.get("data", "").encode("utf-8"))
            self._no_content()
            return
        if parsed.path == "/pty/resize":
            form = self._read_form()
            try:
                pty_host.host.resize(form.get("id", ""), int(form.get("cols", 0)), int(form.get("rows", 0)))
            except ValueError:
                pass
            self._no_content()
            return
        if parsed.path == "/pty/kill":
            pty_host.host.kill(self._read_form().get("id", ""))
            self._no_content()
            return
        if parsed.path == "/github-refresh":
            form = self._read_form()
            owner = form.get("owner", "")
            if owner not in config.load_github_owners():
                self._send(render_remote_catalog([], [f"unknown GitHub owner: {owner}"]), 400)
                return
            projects, errors, notes = force_refresh_remote(owner)
            visible_untracked, hidden_untracked = gather_untracked_repos()
            self._send(render_remote_catalog(
                projects, errors, notes,
                untracked=visible_untracked, hidden=hidden_untracked,
            ))
            return
        if parsed.path == "/github-ignore":
            form = self._read_form()
            target = form.get("target", "")
            if self._valid_github_catalog_target(target):
                config.ignore_repo(target)
            self._redirect("/#github-catalog")
            return
        if parsed.path == "/github-unignore":
            form = self._read_form()
            target = form.get("target", "")
            if self._valid_github_catalog_target(target):
                config.unignore_repo(target)
            self._redirect("/#github-catalog")
            return
        if parsed.path == "/github-onboard":
            form = self._read_form()
            target = form.get("target", "")
            owner = target.split("/")[0] if "/" in target else target
            if owner not in config.load_github_owners():
                projects, errors, notes = gather_remote_projects()
                visible_untracked, hidden_untracked = gather_untracked_repos()
                self._send(render_remote_catalog(
                    projects,
                    errors + [f"refusing to onboard untrusted repo: {target}"],
                    notes,
                    untracked=visible_untracked,
                    hidden=hidden_untracked,
                ), 400)
                return
            onboard_notes: list[str] = []
            onboard_errors: list[str] = []
            handoff = ""
            try:
                result = remote_start.onboard_github_project(f"github:{target}")
                integ = result.integration
                if integ.ok:
                    detail = f" (PR: {integ.pr_url})" if getattr(integ, "pr_url", None) else ""
                    onboard_notes.append(f"Onboarded {target} successfully.{detail}")
                else:
                    onboard_notes.append(f"Onboarded {target} (integration incomplete: {integ.detail}).")
                if result.registered:
                    # Post-Onboard handoff: offer a start-work CTA for the new project.
                    handoff = render_onboard_handoff(
                        result.path.name,
                        _project_index(result.path),
                        str(result.path),
                        [{"alias": a} for a in sorted(_known_aliases())],
                    )
            except (RuntimeError, ValueError) as exc:
                onboard_errors.append(f"Onboard failed for {target}: {exc}")
            projects, errors, notes = gather_remote_projects()
            visible_untracked, hidden_untracked = gather_untracked_repos()
            self._send(handoff + render_remote_catalog(
                projects, errors + onboard_errors, notes + onboard_notes,
                untracked=visible_untracked, hidden=hidden_untracked,
            ))
            return

        query = process_launch(self._read_form())
        # 303 -> GET /control so a refresh doesn't re-submit the launch (PRG pattern).
        self._redirect(f"/control?{query}")

    def log_message(self, *args: Any) -> None:  # silence default stderr logging
        pass


class _SingleInstanceServer(ThreadingHTTPServer):
    # One dashboard per port. On Windows, SO_REUSEADDR lets multiple sockets bind the
    # same port, so disable it there to prevent duplicate stale dashboards. POSIX needs
    # reuse enabled so a cleanly stopped dashboard can restart while the old socket is
    # still in TIME_WAIT.
    allow_reuse_address = sys.platform != "win32"


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    try:
        server = _SingleInstanceServer((host, port), _Handler)
    except OSError:
        print(f"Horus dashboard already running at http://{host}:{port}; not starting another.")
        return
    count = len(config.load_projects())
    print(f"Horus dashboard: http://{host}:{port}  ({count} project(s))")
    print("Local-only (loopback). Launches in-app terminals on request. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
