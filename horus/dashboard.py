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
import json
import os
import re
import subprocess
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
    offboard,
    overhead,
    projection_sync,
    pty_host,
    registry,
    remote_start,
    roadmap,
    routines,
    selfupdate,
    session_discovery,
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
        "projection_sync": {"verdict": "unknown"},
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
        # The inverse direction: repo artifacts NEWER than the installed CLI.
        # The remedy is updating horus-harness itself, not refreshing the repo.
        data["cli_outdated"] = any("newer than this CLI" in a.message for a in actions)
    except Exception:
        # never let a projection check break the dashboard render
        data["artifacts_stale"] = False

    # Per-surface sync (Claude vs installed CLI, Codex vs installed CLI - never
    # surfaces to each other). Read-only and self-guarded; see projection_sync.
    data["projection_sync"] = projection_sync.sync_state(root)

    return data


def gather_projects() -> list[dict[str, Any]]:
    paths = config.load_projects()
    if len(paths) <= 1:
        return [load_project(p) for p in paths]
    # load_project is I/O-bound per project (git subprocesses, file reads,
    # read-only staleness check). Run them concurrently so the index isn't N
    # sequential ~235ms git_state calls. Order is preserved by executor.map.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(8, len(paths))) as pool:
        return list(pool.map(load_project, paths))


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
.resume-text { font-size: 12px; color: var(--ink-2); background: var(--bg-2); border: 1px solid var(--border);
               border-radius: 6px; padding: 7px 9px; margin-top: 4px; white-space: pre-wrap; overflow-wrap: anywhere; }
.copy { font-size: 11px; color: var(--seal); background: var(--bg-2); border: 1px solid var(--border-strong);
        border-radius: 6px; padding: 2px 9px; cursor: pointer; }
.copy:hover { background: var(--raised); }
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
details.tasks { margin: 8px 0; border: 1px solid var(--border); border-radius: 8px; padding: 6px 12px; background: var(--panel-2); }
details.tasks summary { cursor: pointer; font-size: 13px; color: var(--ink-2); }
details.tasks ul { margin: 8px 0 4px; }
details.tasks li { list-style: none; margin-left: -16px; }
.t-done { color: #8a93a6; } .t-done .mk { color: #57d39a; }
.t-todo .mk { color: #6db3f2; } .t-partial { color: #e6c35c; }
.t-sec { color: #8a93a6; font-size: 12px; }
ul { padding-left: 22px; } li.task { list-style: none; margin-left: -16px; }
li.done { color: #8a93a6; } li.partial { color: #e6c35c; }
pre { background: var(--bg-2); padding: 12px; border-radius: 8px; overflow-x: auto; }
code { background: var(--bg-2); padding: 1px 5px; border-radius: 4px; }
.section { margin-top: 26px; }
.back { font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
td, th { text-align: left; padding: 6px 10px; border-bottom: 1px solid #232733; }
nav { margin-top: 10px; display: flex; gap: 18px; align-items: center; }
nav a { color: #8a93a6; font-size: 13px; padding-bottom: 4px; border-bottom: 2px solid transparent; }
nav a.active { color: #e6e6e6; border-bottom-color: #6db3f2; }
nav a:hover { text-decoration: none; color: #e6e6e6; }
@keyframes livepulse { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
.control { display: grid; grid-template-columns: 280px 1fr; gap: 18px; align-items: start; }
main.wide { max-width: none; }
.acct { display: flex; align-items: center; gap: 12px; margin: 12px 0; }
.acct .who { font-size: 14px; font-weight: 600; }
svg.ring text { font-family: -apple-system, Segoe UI, sans-serif; font-weight: 600; }
.proj-row { display: flex; justify-content: space-between; align-items: center;
            padding: 8px 0; border-bottom: 1px solid #1c1f2a; }
.proj-row:last-child { border-bottom: 0; }
/* launch disclosure summary + .launch-body are styled by the sumi-e block below */
.cmd { display: flex; align-items: center; gap: 6px; margin: 4px 0; }
.cmd code { flex: 1; font-size: 11px; white-space: pre-wrap; overflow-wrap: anywhere; }
.sessions-grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); }
.scard { background: #151823; border: 1px solid #232733; border-radius: 10px; padding: 16px 18px; }
.scard-h { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.scard-t { font-size: 16px; font-weight: 600; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #232733; color: #b9c2d0; }
.usagebar { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; margin: 12px 0 4px; }
.usagebar > span { display: block; height: 100%; }
form.launch-form { margin: 8px 0 4px; display: flex; flex-direction: column; gap: 8px; }
form.launch-form label { font-size: 12px; color: #b9c2d0; }
form.launch-form select { background: #0b0d12; color: #e6e6e6; border: 1px solid #284058;
            border-radius: 6px; padding: 3px 6px; font-size: 12px; margin-left: 4px; }
form.launch-form .modes { display: flex; flex-direction: column; gap: 3px; }
form.launch-form .modes label { display: flex; align-items: center; gap: 6px; }
button.start { font: inherit; cursor: pointer; }
.acct-actions { margin-left: auto; display: flex; gap: 6px; align-items: center; }
.acct-actions form { margin: 0; }
.acct-edit { margin-top: 4px; display: flex; gap: 5px; align-items: center; }
.acct-edit input { width: 118px; min-width: 0; background: #0b0d12; color: #e6e6e6;
                   border: 1px solid #284058; border-radius: 5px; padding: 3px 5px; font-size: 12px; }
.or-cmds { margin-top: 6px; }
.or-cmds > summary { cursor: pointer; font-size: 11px; color: #8a93a6; list-style: none; }
.or-cmds > summary::-webkit-details-marker { display: none; }
.banner { border-radius: 8px; padding: 9px 13px; margin: 0 0 16px; font-size: 13px; }
.banner.ok { background: var(--go-soft); border: 1px solid color-mix(in srgb, var(--go) 32%, transparent); color: var(--ink-2); }
.banner.ok strong { color: var(--go); }
.banner.err { background: var(--seal-soft); border: 1px solid var(--seal-line); color: var(--seal); }
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
/* Action buttons: green = refresh/upgrade (go), red = remove completely, neutral = keep. */
/* legacy pill btn-go removed; .btn + .btn-go (sumi-e) own this now */
button.btn-danger { font: inherit; font-size: 12px; cursor: pointer; color: #fff0f1;
    background: #b1404f; border: 1px solid #c9505f; border-radius: 6px; padding: 4px 12px; font-weight: 600; }
button.btn-danger:hover { background: #c64d5d; }
button.btn-keep { font: inherit; font-size: 12px; cursor: pointer; color: #cdd6e4;
    background: #232733; border: 1px solid #3a4250; border-radius: 6px; padding: 4px 12px; }
button.btn-keep:hover { background: #2c3140; }
details.offload { margin: 12px 0 2px; border-top: 1px solid #232733; padding-top: 10px; }
details.offload > summary { cursor: pointer; color: #8a93a6; font-size: 12px; }
details.offload .offload-actions { display: flex; gap: 8px; margin-top: 8px; }

/* Sumi-e dashboard redesign. Server-rendered, no external assets, tiny vanilla JS. */
:root{
  --bg:#15161a; --bg-2:#0e0f12; --panel:#1d1e23; --panel-2:#191a1f; --raised:#26272d;
  --border:#2f3036; --border-strong:#3e3f47; --hairline:#25262b;
  --ink:#eeeeef; --ink-2:#abacb2; --ink-3:#7c7d84; --ink-faint:#5b5c62;
  --seal:#df524a; --seal-strong:#c83f38; --seal-soft:rgba(223,82,74,.13); --seal-line:rgba(223,82,74,.45);
  --go:#62b18c; --go-soft:rgba(98,177,140,.13); --claude:#d98a6a; --codex:#7fb0e6;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 28px -14px rgba(0,0,0,.65);
  --shadow-lift:0 2px 4px rgba(0,0,0,.45),0 18px 44px -18px rgba(0,0,0,.7);
  --r-sm:7px; --r-md:11px; --r-lg:16px; --r-pill:999px;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --maxw:1320px; --t-fast:140ms cubic-bezier(.4,0,.2,1); --t-soft:280ms cubic-bezier(.16,.84,.44,1);
}
.skin-light{
  --bg:#f1f2f2; --bg-2:#e4e6e6; --panel:#ffffff; --panel-2:#f5f6f6; --raised:#ffffff;
  --border:#e3e5e5; --border-strong:#cdd0d0; --hairline:#edefef;
  --ink:#181a1a; --ink-2:#4d5252; --ink-3:#787d7d; --ink-faint:#9aa0a0;
  --seal:#d8362b; --seal-strong:#b62a20; --seal-soft:rgba(216,54,43,.085); --seal-line:rgba(216,54,43,.4);
  --go:#2f8c5d; --go-soft:rgba(47,140,93,.10); --claude:#bf5d39; --codex:#3f72a6;
  --shadow:0 1px 2px rgba(40,38,32,.08),0 10px 26px -16px rgba(40,38,32,.32);
  --shadow-lift:0 2px 6px rgba(40,38,32,.12),0 22px 48px -22px rgba(40,38,32,.4);
}
html,body{margin:0}
body{
  font:14.5px/1.5 var(--sans); background:var(--bg); color:var(--ink);
  -webkit-font-smoothing:antialiased; letter-spacing:.1px;
}
body::before{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(1200px 540px at 78% -8%, color-mix(in srgb,var(--seal) 7%, transparent), transparent 60%)}
a{color:var(--seal);text-decoration:none} a:hover{color:var(--seal-strong);text-decoration:none}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 28px}
.eyebrow{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
.mono{font-family:var(--mono)} .muted{color:var(--ink-3)}
#welcome{position:absolute;opacity:0;pointer-events:none}.welcome{position:fixed;inset:0;z-index:120;display:flex;align-items:center;justify-content:center;padding:24px;background:color-mix(in srgb,var(--bg-2) 80%, transparent);backdrop-filter:blur(8px)}#welcome:checked~.welcome,body.welcome-seen .welcome{display:none}.welcome-card{position:relative;background:var(--panel);border:1px solid var(--border);border-radius:var(--r-lg);box-shadow:var(--shadow-lift);padding:28px;max-width:360px;text-align:center}.welcome-card .wm{height:152px;width:auto;image-rendering:pixelated;display:block;margin:6px auto 4px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.4))}.skin-light .welcome-card .wm{filter:drop-shadow(0 6px 14px rgba(40,38,32,.22))}.welcome-card h3{margin:6px 0 8px;font-size:22px;font-weight:600;letter-spacing:.02em}.welcome-card p{margin:0 0 22px;font-size:13.5px;color:var(--ink-2);line-height:1.6}.welcome-card .btn{padding:11px 22px;font-size:14px}
header.top{position:sticky;top:0;z-index:40;background:color-mix(in srgb,var(--bg) 86%, transparent);backdrop-filter:saturate(1.1) blur(12px);border-bottom:1px solid var(--hairline);padding:0}
.top-in{display:flex;align-items:center;gap:22px;height:64px}
.brand{display:flex;align-items:center;gap:12px;min-width:0}.sun-mark{width:26px;height:26px;border-radius:50%;flex:none;background:radial-gradient(circle at 38% 35%, color-mix(in srgb,var(--seal) 78%, #fff 34%), var(--seal) 64%, var(--seal-strong) 100%)}
.wordmark{display:flex;flex-direction:column;line-height:1.05}.wordmark b{font-size:17px;font-weight:600;letter-spacing:.36em;text-transform:uppercase;padding-left:.36em}.wordmark small{font-size:11px;color:var(--ink-3);letter-spacing:.04em}
nav.tabs{display:flex;gap:4px;margin:0 0 0 6px}nav.tabs a{color:var(--ink-2);font-weight:500;padding:8px 14px;border-radius:var(--r-sm);border:1px solid transparent;position:relative;transition:color var(--t-fast),background var(--t-fast)}nav.tabs a:hover{color:var(--ink);background:var(--panel-2)}nav.tabs a .dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--seal);margin-right:7px;vertical-align:middle;opacity:0}nav.tabs a.active{color:var(--ink)}nav.tabs a.active .dot{opacity:1}
.top-right{margin-left:auto}.skin-btn{display:inline-flex;align-items:center;gap:8px;cursor:pointer;user-select:none;border:1px solid var(--border);background:var(--panel);border-radius:var(--r-pill);padding:6px 12px;font-size:12.5px;color:var(--ink-2)}.skin-btn:hover{border-color:var(--border-strong);color:var(--ink)}#skin{position:absolute;opacity:0;pointer-events:none}.skin-btn .sun{display:none}.skin-light .skin-btn .sun{display:inline}.skin-light .skin-btn .moon{display:none}
main{padding:0;max-width:none}.band{padding:30px 0}.band.tight{padding:20px 0}.ov-shell{display:grid;grid-template-columns:300px minmax(0,1fr);gap:30px;align-items:start;padding-top:26px;padding-bottom:8px}@media(max-width:1000px){.ov-shell{grid-template-columns:1fr}}.rail{position:sticky;top:84px;align-self:start;display:flex;flex-direction:column}@media(max-width:1000px){.rail{position:static}}.ov-col{min-width:0;display:flex;flex-direction:column}.greet{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin:0 0 6px}.greet .gtext{flex:1;min-width:240px;display:flex;flex-direction:column;gap:3px}.greet h2{font-size:22px;font-weight:600;margin:2px 0 0;letter-spacing:.01em}.shead{display:flex;align-items:baseline;gap:14px;margin:14px 0 16px}.shead h2{font-size:20px;font-weight:600;margin:0}.shead .meta{margin-left:auto;color:var(--ink-3);font-size:12.5px}
.attn-pill{display:inline-flex;align-items:center;gap:13px;background:var(--seal-soft);border:1px solid var(--seal-line);border-radius:var(--r-md);padding:11px 17px}.attn-pill .n{font-size:26px;font-weight:600;color:var(--seal);line-height:1}.attn-pill .lab{display:flex;flex-direction:column;line-height:1.3}.attn-pill .lab b{font-size:13px;color:var(--ink);font-weight:600}.attn-pill .lab span{font-size:12px;color:var(--ink-3)}
.acct-panel{background:var(--panel);border:1px solid var(--border);border-radius:var(--r-lg);overflow:hidden}.acct-panel>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:15px 18px}.acct-panel>summary::-webkit-details-marker{display:none}.acct-panel>summary h3{margin:0;font-size:14.5px}.acct-panel>summary .chev{margin-left:auto;color:var(--ink-3);transition:transform var(--t-fast);font-size:11px}.acct-panel[open]>summary{border-bottom:1px solid var(--hairline)}.acct-panel[open]>summary .chev{transform:rotate(90deg)}
.acct-c{display:grid;grid-template-columns:46px minmax(0,1fr) auto;gap:10px 16px;align-items:center;padding:16px 20px;border-bottom:1px solid var(--hairline)}.acct-row{display:contents}.ring-wrap{position:relative;width:46px;height:46px;flex:none}.ring{width:46px;height:46px;transform:rotate(-90deg)}.ring .track{fill:none;stroke:var(--border);stroke-width:3.4}.ring .meter{fill:none;stroke-width:3.4;stroke-linecap:round}.ring-num{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:600;font-family:var(--mono)}.acct-row .info{min-width:0}.alias-edit{display:flex;align-items:center;gap:4px}.alias-in{font:inherit;font-size:13.5px;font-weight:600;color:var(--ink);background:transparent;border:1px solid transparent;border-radius:5px;padding:2px 5px;width:100%;max-width:150px}.alias-in:hover{border-color:var(--border)}.alias-in:focus{outline:none;border-color:var(--seal);background:var(--panel-2);box-shadow:0 0 0 2px var(--seal-soft)}.icon-btn{flex:none;width:23px;height:23px;display:inline-flex;align-items:center;justify-content:center;border:1px solid transparent;background:transparent;color:var(--ink-3);border-radius:5px;cursor:pointer;font-size:12px;opacity:0}.alias-edit:hover .icon-btn,.alias-in:focus+.icon-btn{opacity:1}.icon-btn:hover{background:var(--go-soft);color:var(--go)}
.prov-line{display:flex;align-items:center;gap:7px;margin-top:3px;padding-left:5px}.tag-prov{font-size:10px;letter-spacing:.16em;text-transform:uppercase;font-weight:700;padding:2px 7px;border-radius:4px;background:color-mix(in srgb,var(--claude) 15%,transparent);color:var(--claude);border:1px solid color-mix(in srgb,var(--claude) 34%,transparent)}.tag-prov.codex{background:color-mix(in srgb,var(--codex) 15%,transparent);color:var(--codex);border-color:color-mix(in srgb,var(--codex) 34%,transparent)}.when2{font-size:11px;color:var(--ink-faint)}
.mini-session{flex:none;width:27px;height:27px;border-radius:7px;font-size:17px;line-height:1;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);background:var(--panel-2);color:var(--ink-2);cursor:pointer}.mini-session:hover{background:var(--raised);color:var(--ink);border-color:var(--border-strong)}.wbar.mini{grid-column:1/-1;margin-top:0}.wbar .lab{font-size:11px;margin-bottom:4px;color:var(--ink-3);display:flex;gap:8px}.wbar .lab b{color:var(--ink-2)}.track-bar{height:6px;border-radius:var(--r-pill);background:var(--border);overflow:hidden}.track-bar>i{display:block;height:100%;border-radius:var(--r-pill)}.acct-foot2{padding:14px 18px;display:flex;flex-direction:column;gap:12px}.remove-pop>summary{list-style:none;cursor:pointer;font-size:12.5px;color:var(--ink-3);display:inline-flex;align-items:center;gap:7px}.remove-pop>summary::-webkit-details-marker{display:none}.remove-pop>summary:hover{color:var(--seal)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(372px,1fr));gap:18px}.pcard{position:relative;background:var(--panel);border:1px solid var(--border);border-radius:var(--r-lg);padding:18px 18px 16px;display:flex;flex-direction:column;gap:14px;transition:transform var(--t-soft),box-shadow var(--t-soft),border-color var(--t-fast)}.pcard:hover{transform:translateY(-2px);box-shadow:var(--shadow-lift);border-color:var(--border-strong);cursor:pointer}.card-link{position:absolute;inset:0;z-index:0;border-radius:var(--r-lg)}.pcard>*:not(.card-link){position:relative;z-index:1}.pc-head{display:flex;align-items:flex-start;gap:12px}.pc-title{min-width:0}.pc-title h3{margin:0;font-size:16.5px;font-weight:600}.pc-title h3 a{color:var(--ink)}.pc-sub{display:flex;align-items:center;gap:9px;margin-top:5px;flex-wrap:wrap;font-size:12px}.branch{font-family:var(--mono);font-size:11.5px;color:var(--ink-2)}.pc-health{margin-left:auto;flex:none}.health-dot{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:var(--ink-2);font-weight:500}.health-dot i{width:9px;height:9px;border-radius:50%;background:var(--go);box-shadow:0 0 0 3px var(--go-soft)}.health-dot.warn i{background:var(--seal);box-shadow:0 0 0 3px var(--seal-soft)}.health-dot.plan i{background:var(--ink-3);box-shadow:0 0 0 3px var(--panel-2)}.pc-open{flex:none;width:30px;height:30px;display:inline-flex;align-items:center;justify-content:center;border-radius:7px;border:1px solid transparent;color:var(--ink-3);font-size:15px}.pcard:hover .pc-open{color:var(--ink);border-color:var(--border);background:var(--panel-2)}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:500;padding:3px 9px;border-radius:var(--r-pill);background:var(--panel-2);border:1px solid var(--border);color:var(--ink-2);white-space:nowrap}.badge.seal,.badge.warn{color:var(--seal);border-color:var(--seal-line);background:var(--seal-soft)}.badge .gd{width:6px;height:6px;border-radius:50%;background:var(--ink-3)}.statline{display:flex;gap:8px;flex-wrap:wrap}
.glyph{width:17px;height:12px;color:var(--seal);flex:none}.next{position:relative;background:var(--panel-2);border:1px solid var(--border);border-radius:var(--r-md);padding:13px 15px 13px 16px;overflow:hidden;margin:0}.next::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--seal)}.next .nh{display:flex;align-items:center;gap:8px;margin-bottom:6px}.next .nh .glyph{width:17px;height:12px;color:var(--seal);flex:none}.next .nh b{font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--ink-2);font-weight:700}.next p,.next-one{margin:0;font-size:13.5px;line-height:1.5;color:var(--ink)}.next .mode,.next-mode{margin-top:9px;padding-top:9px;border-top:1px solid var(--hairline);font-size:12.5px;color:var(--ink-2)}.next .mode b,.next-mode strong{color:var(--ink);font-weight:600}.next .hint,.next-mode .why{display:block;margin-top:3px;font-style:italic;color:var(--ink-3);font-size:12px}.next.empty{border:1px dashed var(--border-strong)}.next.empty::before{background:var(--border-strong)}.next.empty .nh b,.next.empty .nh .glyph,.next.empty p{color:var(--ink-3)}
.feat{display:flex;flex-direction:column;gap:9px}.feat .feat-head{font-size:11.5px;color:var(--ink-3)}.feat .road-stat a{color:inherit;text-decoration:none}.feat .road-stat a:hover{color:var(--seal)}.feat .fbar{display:flex;height:7px;border-radius:var(--r-pill);overflow:hidden;background:var(--border)}.feat .fbar i{display:block;height:100%}.feat .fbar i.s{background:var(--ink)}.feat .fbar i.p{background:var(--ink-3)}.feat .fbar i.q{background:var(--border-strong)}.feat .fk{display:flex;gap:16px;font-size:12px;flex-wrap:wrap}.feat .fk span{display:flex;align-items:center;gap:6px;color:var(--ink-3)}.feat .fk b{color:var(--ink);font-weight:600}.feat .fk i{width:8px;height:8px;border-radius:2px}.dot-s{background:var(--ink)}.dot-p{background:var(--ink-3)}.dot-q{background:var(--border-strong)}.recap{font-size:12.5px;color:var(--ink-2);line-height:1.5}.recap .when{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);display:block;margin-bottom:3px}.recap.none{color:var(--ink-faint);font-style:italic}.pc-foot{display:block;border-top:1px solid var(--hairline);padding-top:13px}.pc-actions{display:flex;gap:9px}.pc-actions .btn{flex:1}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;font:inherit;font-size:13px;font-weight:500;cursor:pointer;white-space:nowrap;border-radius:var(--r-sm);border:1px solid var(--border);background:var(--panel);color:var(--ink);padding:8px 13px;line-height:1}.btn:hover{border-color:var(--border-strong);background:var(--raised)}.btn.sm{padding:6px 10px;font-size:12px}.btn.block{width:100%}.btn-go{background:var(--ink)!important;border-color:var(--ink)!important;color:var(--panel)!important}.btn-seal{background:var(--seal);border-color:var(--seal);color:#fff}.btn-warn{background:var(--seal-soft);border-color:var(--seal-line);color:var(--seal)}.btn-danger{background:transparent!important;border-color:var(--seal-line)!important;color:var(--seal)!important}.btn-ghost{background:transparent;border-color:transparent;color:var(--ink-2)}
details.launch,details.disc{border:1px solid var(--border);border-radius:var(--r-md);background:var(--panel-2);overflow:hidden;margin-top:11px}details.launch>summary,details.disc>summary{list-style:none;cursor:pointer;padding:11px 14px;font-size:13px;font-weight:500;display:flex;align-items:center;gap:9px;color:var(--ink-2)}details.launch>summary::-webkit-details-marker,details.disc>summary::-webkit-details-marker{display:none}details.launch[open]>summary,details.disc[open]>summary{border-bottom:1px solid var(--hairline);color:var(--ink)}.disc-body,.launch-body{padding:14px}.lform{display:grid;gap:11px}.frow{display:flex;gap:10px;flex-wrap:wrap}.field{flex:1 1 150px;min-width:0}.field label{display:block;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);margin-bottom:5px;font-weight:600}select,.field input[type=text],.field input:not([type]){width:100%;font:inherit;font-size:13px;background:var(--panel);color:var(--ink);border:1px solid var(--border);border-radius:var(--r-sm);padding:8px 10px}.intent-row{display:flex;gap:10px}.intent-row .btn{flex:1}
details.fold{border:1px solid var(--border);border-radius:var(--r-lg);background:var(--panel);overflow:hidden;margin-top:0}details.fold+details.fold{margin-top:18px}details.fold>summary{list-style:none;cursor:pointer;padding:18px 22px;display:flex;align-items:center;gap:12px}details.fold>summary::-webkit-details-marker{display:none}details.fold>summary .chev{color:var(--ink-3);transition:transform var(--t-fast)}details.fold[open]>summary{border-bottom:1px solid var(--hairline)}details.fold[open]>summary .chev{transform:rotate(90deg)}details.fold>summary h2{margin:0;font-size:18px;font-weight:600}details.fold>summary .count{color:var(--ink-3);font-size:13px}.fold-body{padding:22px}.repogrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}.repo{border:1px solid var(--border);border-radius:var(--r-md);background:var(--panel-2);padding:15px}.repo h3,.repo h4{margin:0 0 9px;font-size:14px;font-weight:600}.repo p{margin:0 0 11px;font-size:12.5px;color:var(--ink-3);line-height:1.45}.repo .meta,.repo .acts{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.detail-top{display:flex;align-items:flex-start;gap:18px;flex-wrap:wrap;margin-top:8px}.crumb{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--ink-3);margin-bottom:14px}.detail-top h1{margin:0;font-size:28px;font-weight:600}.detail-top .sub{display:flex;gap:10px;align-items:center;margin-top:9px;flex-wrap:wrap}.detail-top .right{margin-left:auto;display:flex;gap:9px;align-items:center;flex-wrap:wrap}.dlayout{display:grid;grid-template-columns:1fr 360px;gap:22px;margin-top:26px;align-items:start}@media(max-width:1080px){.dlayout{grid-template-columns:1fr}}.col{display:flex;flex-direction:column;gap:18px;min-width:0;max-width:none;flex:initial;padding:0;background:transparent;border:0}.panel{background:var(--panel);border:1px solid var(--border);border-radius:var(--r-lg);padding:20px;min-width:0}.panel.sticky{position:sticky;top:84px}.panel .ph{display:flex;align-items:baseline;gap:10px;margin-bottom:14px}.panel .ph .x{margin-left:auto;font-size:12px;color:var(--ink-3)}.panel table{display:block;max-width:100%;overflow-x:auto}.panel th,.panel td{white-space:nowrap}.lead{font-size:14.5px;line-height:1.6;color:var(--ink)}.buckets{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}@media(max-width:640px){.buckets{grid-template-columns:1fr}}.bucket .bh{display:flex;align-items:center;gap:8px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;color:var(--ink-3);margin-bottom:11px;padding-bottom:9px;border-bottom:1px solid var(--hairline)}.bucket .bh .n{margin-left:auto}.bucket ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}.bucket li{font-size:13px;line-height:1.4;color:var(--ink-2);padding-left:15px;position:relative}.bucket li::before{content:"";position:absolute;left:0;top:7px;width:5px;height:5px;border-radius:50%;background:var(--border-strong)}.bucket.ship li{color:var(--ink)}.bucket.ship li::before{background:var(--ink)}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:14px}.metric{background:var(--panel-2);border:1px solid var(--border);border-radius:var(--r-md);padding:13px 14px}.metric .k{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-weight:600}.metric .v{font-size:22px;font-weight:600;margin-top:6px}.roadprog{display:flex;align-items:center;gap:12px;margin-top:12px}.roadprog .track-bar{flex:1}.roadprog .pct{font-family:var(--mono);font-size:12px;color:var(--ink-2);white-space:nowrap}.roadprog .pct a{color:inherit;text-decoration:none}.roadprog .pct a:hover{color:var(--seal)}.kv{display:grid;grid-template-columns:auto 1fr;gap:8px 16px;font-size:13px}.kv dt{color:var(--ink-3)}.kv dd{margin:0;color:var(--ink)}
.settings-form{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:22px;max-width:920px}.sfield label{display:block;font-size:13.5px;font-weight:600;margin-bottom:6px}.sfield .desc{font-size:12.5px;color:var(--ink-3);margin:0 0 10px;line-height:1.45}.settings-actions{display:flex;gap:10px;margin-top:22px}
footer{border-top:1px solid var(--hairline);margin-top:40px;padding:26px 0}.foot-in{display:flex;align-items:center;gap:14px;color:var(--ink-faint);font-size:12.5px}.eye{width:26px;height:17px;color:var(--ink-faint)}
"""

_LEVEL_CLASS = {"ok": "health-ok", "warn": "health-warn", "fail": "health-fail"}


def _live_count(records: list[registry.SessionRecord]) -> int:
    """Native agent sessions currently running (a live process)."""
    return sum(1 for r in records if r.status == "running")


def _nav(active: str, live: int = 0) -> str:
    # Control (the session cockpit) was retired — its useful bits (account usage,
    # start/resume) now live on the Projects tab. ``live`` is accepted for call
    # compatibility but no longer renders a badge.
    links = [("/", "Projects", "projects"), ("/settings", "Settings", "settings")]
    out = []
    for href, label, key in links:
        if key == active:
            out.append(
                f"<a class=\"active\" href='{href}'><span class='dot'></span>{label}</a>"
            )
        else:
            out.append(f"<a href='{href}'>{label}</a>")
    items = "".join(out)
    return f"<nav class='tabs'>{items}</nav>"


def _active_class(active: bool) -> str:
    return ' class="active"' if active else ""


def _stale_build() -> dict[str, object] | None:
    """Build state when this server's loaded build is older than the on-disk
    install, else None. A stale server must not write artifacts: its in-process
    `upgrade_project` stamps the OLD generation and its staleness badge compares
    against that same generation (self-referentially "fresh") — see history.md
    "The stale dashboard fixed staleness against itself"."""
    try:
        state = selfupdate.build_state()
    except Exception:
        return None
    return state if state.get("stale") else None


def _stale_build_banner() -> str:
    state = _stale_build()
    if not state:
        return ""
    return (
        "<div class='banner err'>This dashboard is running an old build "
        f"(v{html.escape(str(state['running']))} in memory; v{html.escape(str(state['disk']))} "
        "is installed) &mdash; restart Horus to load it. Artifact writes are disabled and "
        "staleness badges may be wrong until then.</div>"
    )


def _update_pill_html(status: dict[str, object] | None = None) -> str:
    """Top-nav "update available" pill + Update button, or "" when current.

    The button runs `uv tool upgrade horus-harness`; the running server keeps its
    old in-memory build (no hot reload), so the post-upgrade banner says to
    restart Horus rather than pretending the new version is live.
    """
    status = status if status is not None else selfupdate.check_update()
    if not status.get("update_available"):
        return ""
    latest = html.escape(str(status.get("latest")))
    return (
        "<form method='post' action='/self-update' style='display:inline-block;margin-right:10px'"
        f" onsubmit=\"return confirm('Upgrade horus-harness to v{latest}? Horus must be restarted afterwards to load it.')\">"
        f"<button class='btn sm btn-seal' type='submit' title='Installed: v{html.escape(__version__)}'>"
        f"&#8599; Update to v{latest}</button></form>"
    )


def _project_sessions_html(path: Path) -> str:
    """Recent sessions panel: every Claude/Codex session that touched this project,
    discovered read-only from the transcripts the CLIs write — regardless of how the
    session was started. Counts + timestamps only, never transcript content."""
    try:
        sessions = session_discovery.discover_sessions(Path(path))
    except Exception as exc:  # noqa: BLE001 — panel must never break the page
        return (
            "<div class='panel'><div class='ph'><span class='eyebrow'>Recent sessions</span></div>"
            f"<p class='muted'>Session discovery unavailable: {html.escape(str(exc))}</p></div>"
        )
    if not sessions:
        return (
            "<div class='panel'><div class='ph'><span class='eyebrow'>Recent sessions</span></div>"
            "<p class='muted'>No Claude/Codex transcripts found for this project on this machine.</p></div>"
        )
    rows = []
    for s in sessions[:8]:
        last = html.escape((s.last_activity or "")[:16].replace("T", " ")) or "—"
        rows.append(
            f"<tr><td><span class='badge'>{html.escape(s.agent)}</span></td>"
            f"<td class='mono'>{html.escape(s.session_id[:12])}</td>"
            f"<td>{last}</td><td>{s.message_count}</td></tr>"
        )
    more = (
        f"<p class='muted' style='font-size:12px'>+ {len(sessions) - 8} older session(s)</p>"
        if len(sessions) > 8 else ""
    )
    return (
        "<div class='panel'><div class='ph'><span class='eyebrow'>Recent sessions</span>"
        "<span class='x mono'>from local transcripts</span></div>"
        "<div style='overflow-x:auto'><table><tr><th>Agent</th><th>Session</th>"
        f"<th>Last activity</th><th>Msgs</th></tr>{''.join(rows)}</table></div>{more}</div>"
    )


def _page(title: str, body: str, active: str = "projects", wide: bool = False, live: int = 0) -> str:
    icon_key = html.escape(__version__, quote=True)
    main_cls = " class='wide'" if wide else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)}</title>"
        f"<link rel='icon' href='/favicon.ico?v={icon_key}' sizes='any'>"
        f"<link rel='icon' type='image/png' href='/assets/icon.png?v={icon_key}'>"
        f"<style>{_STYLE}</style>"
        "<script>try{if(localStorage.getItem('horus_skin')!=='dark')document.documentElement.classList.add('skin-light')}catch(e){document.documentElement.classList.add('skin-light')}</script>"
        "</head><body>"
        "<input type='checkbox' id='skin' onclick=\"var l=document.documentElement.classList.toggle('skin-light');try{localStorage.setItem('horus_skin',l?'light':'dark')}catch(e){};this.checked=l\">"
        "<input type='checkbox' id='welcome'>"
        "<div class='welcome'><div class='welcome-card'>"
        f"<img class='wm' src='/assets/mascot.png?v={icon_key}' alt=''>"
        "<h3>Horus is watching</h3>"
        "<p>Project continuity, account usage, and the next action are gathered here.</p>"
        "<label class='btn btn-seal' for='welcome' onclick=\"sessionStorage.setItem('horusWelcome','1')\">Enter the dashboard</label>"
        "</div></div>"
        "<script>if(sessionStorage.getItem('horusWelcome')==='1'){document.body.classList.add('welcome-seen');document.getElementById('welcome').checked=true;}</script>"
        "<header class='top'><div class='wrap top-in'><div class='brand'>"
        "<span class='sun-mark' aria-hidden='true'></span>"
        "<div class='wordmark'><b>Horus</b><small>project continuity &amp; control panel</small></div>"
        "</div>"
        f"{_nav(active, live)}"
        "<div class='top-right'>"
        # Self-update pill: async (PyPI check must never block a paint); empty
        # fragment = up to date, so the placeholder just disappears.
        "<span data-horus-src='/update-check'></span>"
        "<label class='skin-btn' for='skin'>"
        "<span class='moon'>&#9687; Dark</span><span class='sun'>&#9686; Light</span></label></div>"
        "</div></header>"
        f"<main{main_cls}>{_stale_build_banner()}{body}</main>"
        "<script>"
        "if(sessionStorage.getItem('horusWelcome')==='1'){document.body.classList.add('welcome-seen');}"
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
        ".catch(function(){el.innerHTML=\"<div class='banner err'>This section failed to load.</div>\";});"
        "});"
        # Ignore-in-place: intercept catalog Ignore submits (delegated, so it also
        # covers the async-loaded fragment) and remove the card without a reload,
        # so several repos can be ignored in one sitting. Non-JS falls back to PRG.
        "document.addEventListener('submit',function(ev){"
        "var f=ev.target;"
        "if(!f||!f.getAttribute||f.getAttribute('action')!=='/github-ignore')return;"
        "ev.preventDefault();"
        "fetch('/github-ignore',{method:'POST',headers:{'X-Horus-Fetch':'1'},"
        "body:new URLSearchParams(new FormData(f))})"
        ".then(function(r){if(r.ok){var c=f.closest('.repo');if(c)c.remove();}});"
        "},true);"
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


def _health_dot(p: dict[str, Any]) -> str:
    fails = sum(1 for f in p["findings"] if f["level"] == "fail")
    warns = sum(1 for f in p["findings"] if f["level"] == "warn")
    status = (p.get("status") or "").lower()
    if fails or warns or p.get("artifacts_stale"):
        n = fails + warns + (1 if p.get("artifacts_stale") else 0)
        label = f"{n} warning" if n == 1 else f"{n} warnings"
        return f"<span class='health-dot warn'><i></i>{label}</span>"
    if status == "planning":
        return "<span class='health-dot plan'><i></i>planning</span>"
    return "<span class='health-dot'><i></i>healthy</span>"


def _eye_glyph(filled: bool = True) -> str:
    pupil = "<circle cx='25' cy='18.5' r='5.5' fill='currentColor'/>" if filled else ""
    return (
        "<svg class='glyph' viewBox='0 0 64 40' fill='none'>"
        "<path d='M4 20 Q24 7 47 17 Q26 31 4 20Z' stroke='currentColor' stroke-width='3'/>"
        f"{pupil}</svg>"
    )


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


def _road_progress_html(p: dict[str, Any], href: str | None = None) -> str:
    pr = p["progress"]
    if not pr["total"]:
        return ""
    label = f"{pr['done']}/{pr['total']} · {pr['pct']}%"
    label_html = f"<a href='{href}'>{html.escape(label)}</a>" if href else html.escape(label)
    return (
        "<div class='roadprog'><span class='muted' style='font-size:12px'>roadmap</span>"
        f"<div class='track-bar'><i style='width:{pr['pct']}%;background:var(--ink-3)'></i></div>"
        f"<span class='pct'>{label_html}</span></div>"
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


def _breakdown_html(p: dict[str, Any], *, completed: bool = True) -> str:
    """The items behind the progress count: open/in-progress and (optionally) completed.

    The dashboard passes ``completed=False`` to keep the detail page focused on
    open work — completed items only grow and live in the file (open it to see all).
    """
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
    elif completed:
        out.append("<p class='muted' style='font-size:13px'>No open roadmap items.</p>")
    if completed and done_tasks:
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
            "<div class='next'><div class='nh'>"
            f"{_eye_glyph()}<b>NEXT ACTION</b></div>"
            f"<p>{html.escape(_plain(text))}</p>{rec_html}</div>"
        )
    if p["progress"]["total"] and p["progress"]["done"] == p["progress"]["total"]:
        return (
            "<div class='next empty'><div class='nh'>"
            f"{_eye_glyph(False)}<b>NEXT ACTION</b></div><p>roadmap complete</p></div>"
        )
    return (
        "<div class='next empty'><div class='nh'>"
        f"{_eye_glyph(False)}<b>NEXT ACTION</b></div>"
        "<p>not set - author <code>next_action</code> in roadmap.md at closure</p></div>"
    )


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
        f"<span class='why'>{html.escape(rec)}</span></div>"
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


def _features_summary_html(p: dict[str, Any], road_href: str | None = None) -> str:
    fc = p["feature_counts"]
    total = sum(fc.values())
    pr = p.get("progress") or {}
    road = ""
    if pr.get("total"):
        rlabel = f"roadmap {pr['pct']}%"
        rinner = f"<a href='{road_href}'>{html.escape(rlabel)}</a>" if road_href else html.escape(rlabel)
        road = f"<div class='feat-head'><span class='road-stat'>{rinner}</span></div>"
    if not total:
        # No features ledger yet — still surface the roadmap stat if there is one.
        return f"<div class='feat'>{road}</div>" if road else ""
    shipped = fc["shipped"] / total * 100
    progress = fc["in_progress"] / total * 100
    planned = max(0.0, 100.0 - shipped - progress)
    return (
        "<div class='feat'>"
        + road
        + "<div class='fbar'>"
        f"<i class='s' style='width:{shipped:.0f}%'></i>"
        f"<i class='p' style='width:{progress:.0f}%'></i>"
        f"<i class='q' style='width:{planned:.0f}%'></i></div>"
        "<div class='fk'>"
        f"<span><i class='dot-s'></i><b>{fc['shipped']}</b> shipped</span>"
        f"<span><i class='dot-p'></i><b>{fc['in_progress']}</b> in progress</span>"
        f"<span><i class='dot-q'></i><b>{fc['planned']}</b> planned</span>"
        "</div></div>"
    )


def _project_column(p: dict[str, Any], i: int, aliases: list[dict[str, Any]] | None = None) -> str:
    missing = "" if p["exists"] else " <span class='badge seal'>no .horus/</span>"
    git = p.get("git") or {}
    branch = html.escape(git.get("branch") or "-")
    rel = html.escape((git.get("commit") or {}).get("rel") or "")
    git_bits = f"<span class='branch'>branch {branch}</span>"
    if rel:
        git_bits += f"<span class='muted'>- {rel}</span>"
    status_badges = [f"<span class='badge'>status {html.escape(p['status']) or 'unknown'}</span>", f"<span class='badge'><b class='mono'>{len(p['sessions'])}</b>&nbsp;sessions</span>"]
    if p.get("artifacts_stale"):
        status_badges.append("<span class='badge seal'><span class='gd'></span>&#9888; artifacts outdated</span>")
    if p.get("cli_outdated"):
        status_badges.append("<span class='badge seal'><span class='gd'></span>&#9888; Horus CLI outdated</span>")
    if git.get("dirty"):
        status_badges.append("<span class='badge warn'><span class='gd'></span>uncommitted</span>")
    if p.get("findings"):
        warns = len([f for f in p["findings"] if f.get("level") in ("warn", "fail")])
        if warns:
            status_badges.append(f"<span class='badge warn'><span class='gd'></span>{warns} warnings</span>")
    latest = p.get("latest")
    if latest:
        summary = html.escape(latest.get("summary") or _session_summary_excerpt(p.get("latest_body", "")) or "(no summary)")
        recap = f"<div class='recap'><span class='when'>last session - {html.escape(latest.get('date', ''))}</span>{summary}</div>"
    else:
        recap = "<div class='recap none'>No sessions yet.</div>"
    refresh = ""
    if p.get("artifacts_stale"):
        refresh = (
            "<form method='post' action='/upgrade-project' style='display:inline'>"
            f"<input type='hidden' name='project' value='{i}'>"
            "<button class='btn btn-warn' type='submit'>Refresh artifacts</button></form>"
        )
    return (
        "<article class='pcard'>"
        f"<a class='card-link' href='/project?i={i}' aria-label='Open project'></a>"
        "<div class='pc-head'><div class='pc-title'>"
        f"<h3><a href='/project?i={i}'>{html.escape(p['name'])}</a>{missing}</h3>"
        f"<div class='pc-sub'>{git_bits}</div></div>"
        f"<div class='pc-health'>{_health_dot(p)}</div><a class='pc-open' href='/project?i={i}' title='Open project' aria-label='Open project'>&#8599;</a></div>"
        f"<div class='statline'>{''.join(status_badges)}</div>"
        f"{_single_next_html(p)}<div hidden><span>Last session summary</span>{_resume_html(p)}{_remaining_items_html(p)}{_features_buckets_html(p)}</div>"
        f"{_features_summary_html(p, road_href=f'/project?i={i}#roadmap')}{recap}"
        "<div class='pc-foot'>"
        f"<div class='pc-actions'>{refresh}</div>"
        "<details class='launch'><summary><span class='chev'>&#9656;</span>Start a session</summary>"
        f"<div class='launch-body'>{_project_launch_form(i, p, aliases or [])}</div></details>"
        "<!-- Offload controls moved to the project detail page by the redesign. -->"
        "</div></article>"
    )

def _remote_project_card(p: github_catalog.RemoteProject) -> str:
    badge_class = "badge" if p.is_local else "badge seal"
    badge_text = "cloned here" if p.is_local else "remote only"
    focus = f"<p class='muted'>{html.escape(p.current_focus)}</p>" if p.current_focus else ""
    next_action = (
        "<div class='next'>"
        "<div class='nh'>" + _eye_glyph() + "<b>NEXT ACTION</b></div>"
        f"<div class='next-one'>{html.escape(_plain(p.next_action))}</div></div>"
        if p.next_action
        else ""
    )
    if p.local_path:
        command = f"cd {p.local_path} && horus open"
    else:
        command = f"horus start github:{p.full_name}"
    return (
        "<div class='repo'>"
        f"<h3><a href='{html.escape(p.url)}'>{html.escape(p.full_name)}</a></h3>"
        f"<div class='meta'><span class='branch'>{html.escape(p.default_branch)}</span>"
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
            f"<button class='btn sm btn-warn' type='submit'>Refresh {html.escape(owner)}</button>"
            "</form>"
        )
    return "<div style='margin:0 0 12px'>" + "".join(forms) + "</div>"


def _untracked_card(u: github_catalog.UntrackedRepo) -> str:
    badge_class = "badge seal" if u.is_local else "badge"
    badge_text = "cloned, not initialized" if u.is_local else "remote only"
    description = f"<p class='muted'>{html.escape(u.description)}</p>" if u.description else ""
    onboard_form = (
        "<form method='post' action='/github-onboard' style='display:inline-block;margin-right:8px'>"
        f"<input type='hidden' name='target' value='{html.escape(u.full_name)}'>"
        "<button class='btn sm btn-seal' type='submit'>Onboard</button>"
        "</form>"
    )
    ignore_form = (
        "<form method='post' action='/github-ignore' style='display:inline-block'>"
        f"<input type='hidden' name='target' value='{html.escape(u.full_name)}'>"
        "<button class='btn sm' type='submit'>Ignore</button>"
        "</form>"
    )
    return (
        "<div class='repo'>"
        f"<h3><a href='{html.escape(u.url)}'>{html.escape(u.full_name)}</a></h3>"
        f"<div class='meta'><span class='branch'>{html.escape(u.default_branch)}</span>"
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
        "<button class='btn sm' type='submit'>Unignore</button>"
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
                "<details class='fold' id='github-catalog'><summary><span class='chev'>&#9656;</span>"
                "<h2>GitHub remote catalog</h2><span class='count'>0</span></summary><div class='fold-body'>"
                "<div class='repo'>"
                "<p><strong>No GitHub owner configured on this machine.</strong></p>"
                "<p class='muted'>GitHub owners and workspace paths are per-machine and are not"
                " git-synced, so a fresh machine always starts empty.</p>"
                "<p class='muted'>Run <code>horus discover github &lt;owner&gt; --save</code>"
                " to add an owner and see your remote projects here.</p>"
                "</div></div></details>"
            )
        return (
            "<details class='fold' id='github-catalog'><summary><span class='chev'>&#9656;</span>"
            "<h2>GitHub remote catalog</h2><span class='count'>0</span></summary><div class='fold-body'>"
            "<div class='repo'><p class='muted'>No Horus-enabled remote repos found yet.</p></div>"
            "</div></details>"
        )
    cards = "".join(_remote_project_card(p) for p in projects)
    if not cards:
        cards = "<div class='repo'><p class='muted'>No Horus-enabled remote repos found yet.</p></div>"
    if notes:
        msg = "".join(f"<li>{html.escape(n)}</li>" for n in notes)
        cards = f"<div class='banner ok'><strong>GitHub catalog cache</strong><ul>{msg}</ul></div>{cards}"
    if errors:
        err = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        cards = f"<div class='banner err'><strong>GitHub discovery issue</strong><ul>{err}</ul></div>{cards}"
    horus_grid = f"<div class='repogrid'>{cards}</div>"

    untracked_section = ""
    if _untracked:
        untracked_cards = "".join(_untracked_card(u) for u in _untracked)
        untracked_section = (
            f"<details class='fold' open><summary><span class='chev'>&#9656;</span>"
            f"<h2>Not tracked</h2><span class='count'>{len(_untracked)}</span></summary>"
            f"<div class='fold-body'><div class='repogrid'>{untracked_cards}</div></div></details>"
        )

    hidden_section = ""
    if _hidden:
        hidden_rows = "".join(_hidden_row(u) for u in _hidden)
        hidden_section = (
            f"<details class='fold'><summary><span class='chev'>&#9656;</span>"
            f"<h2>Hidden</h2><span class='count'>{len(_hidden)}</span></summary>"
            f"<div class='fold-body'>{hidden_rows}</div>"
            "</details>"
        )

    return (
        f"<details class='fold' id='github-catalog'><summary><span class='chev'>&#9656;</span>"
        f"<h2>GitHub remote catalog</h2><span class='count'>{len(projects)}</span>"
        "<span class='grow'></span></summary><div class='fold-body'>"
        f"{_refresh_forms()}"
        f"{horus_grid}"
        "</div></details>"
        f"{untracked_section}"
        f"{hidden_section}"
    )


def render_remote_catalog_placeholder() -> str:
    if not config.load_github_owners():
        return render_remote_catalog([], [])
    return (
        "<details id='github-catalog' class='fold' data-horus-src='/github-catalog' open>"
        "<summary><span class='chev'>&#9656;</span><h2>GitHub remote catalog</h2>"
        "<span class='count'>loading</span></summary>"
        "<div class='fold-body'><div class='repo'><p class='muted'>Loading GitHub projects...</p></div></div>"
        "</details>"
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
    labels = {
        "integration": ("Integration", "How Horus-driven git actions land: PR, direct push, or local only."),
        "commit": ("Commit", "Whether Horus may create its own continuity/onboarding commits."),
        "merge": ("Merge", "Whether PRs are auto-merged or held for review."),
    }
    banner = "<div class='banner ok'>Settings saved.</div>" if saved else ""
    fields = []
    for key, (label, desc) in labels.items():
        opts = "".join(
            f"<option value='{html.escape(v, quote=True)}'"
            f"{' selected' if v == policy.get(key) else ''}>{html.escape(v)}</option>"
            for v in config.WORKFLOW_CHOICES[key]
        )
        fields.append(
            "<div class='sfield'>"
            f"<label>{html.escape(label)}</label>"
            f"<p class='desc'>{html.escape(desc)}</p>"
            f"<select name='{html.escape(key, quote=True)}'>{opts}</select></div>"
        )
    fields.extend([
        "<div class='sfield'><label>Theme</label><p class='desc'>Default appearance. Light is the default; the header toggle changes it too. Stored in this browser.</p>"
        "<select id='theme-sel' onchange=\"try{localStorage.setItem('horus_skin',this.value)}catch(e){};document.documentElement.classList.toggle('skin-light',this.value==='light')\">"
        "<option value='light'>Light</option><option value='dark'>Dark</option></select></div>",
        "<div class='sfield'><label>Default agent</label><p class='desc'>Pre-selected when starting a session.</p><select disabled><option>Choose at launch</option></select></div>",
        "<div class='sfield'><label>Account ID display</label><p class='desc'>Locked by product policy; raw IDs are never shown.</p><select disabled><option>Friendly aliases only</option></select></div>",
        "<div class='sfield'><label>Context loading</label><p class='desc'>Keep startup light and load lanes as needed.</p><select disabled><option>Lazy</option></select></div>",
    ])
    inner = (
        f"{banner}<section class='band'><div class='wrap'>"
        "<div class='shead'><span class='eyebrow'>Configuration</span><h2>Settings</h2>"
        "<span class='meta'>workflow policy applies to Horus-driven actions</span></div>"
        "<div class='panel' style='max-width:980px'>"
        "<form method='post' action='/settings'>"
        f"<div class='settings-form'>{''.join(fields)}</div>"
        "<div class='settings-actions'><button class='btn btn-seal' type='submit'>Save</button>"
        "<a class='btn' href='/'>Cancel</a></div>"
        "</form></div></div></section>"
        "<script>try{document.getElementById('theme-sel').value=(localStorage.getItem('horus_skin')==='dark')?'dark':'light'}catch(e){}</script>"
        f"{_footer_html()}"
    )
    return inner

def _footer_html() -> str:
    return (
        "<footer><div class='wrap foot-in'>"
        "<svg class='eye' viewBox='0 0 64 40' fill='none'>"
        "<path d='M4 20 Q24 7 47 17 Q26 31 4 20Z' stroke='currentColor' stroke-width='2'/>"
        "<circle cx='25' cy='18.5' r='4' fill='var(--seal)'/></svg>"
        "Horus runs locally - single user - subscription auth only - deliberately lightweight"
        "</div></footer>"
    )


def _projects_section_html(projects: list[dict[str, Any]]) -> str:
    """Greeting + needs-attention pill + the project card grid. Heavy: it needs the
    full gather_projects() data (~1.2s), so the index loads it lazily via
    /projects-grid while the shell paints immediately."""
    launch_aliases = [{"alias": a} for a in sorted(_known_aliases())]
    cards = "".join(_project_column(p, i, launch_aliases) for i, p in enumerate(projects))
    if not cards:
        cards = (
            "<div class='panel'><h3>No projects registered</h3>"
            "<p class='muted'>Run <code>horus init</code> inside a project to register it here.</p></div>"
        )
    attention = next((p for p in projects if p.get("artifacts_stale") or p.get("findings")), None)
    if attention:
        idx = projects.index(attention)
        issue = "artifacts outdated" if attention.get("artifacts_stale") else "continuity warning"
        attn = (
            f"<a class='attn-pill' href='/project?i={idx}'><span class='n'>1</span>"
            f"<span class='lab'><b>Needs attention</b><span>{html.escape(attention['name'])} - {issue}</span></span></a>"
        )
    else:
        attn = (
            "<span class='attn-pill'><span class='n'>0</span>"
            "<span class='lab'><b>Needs attention</b><span>all tracked projects calm</span></span></span>"
        )
    count = len(projects)
    plural = "project" if count == 1 else "projects"
    return (
        "<div class='greet'><div class='gtext'><span class='eyebrow'>Cockpit</span>"
        f"<h2>{count} {plural} under watch</h2>"
        "<span class='meta'>local projects - tracked on this machine</span></div>"
        f"{attn}</div>"
        "<div class='shead'><span class='eyebrow'>Under watch</span><h2>Projects</h2>"
        "<span class='meta'>local projects - tracked on this machine</span></div>"
        f"<div class='grid'>{cards}</div>"
    )


def render_index(
    projects: list[dict[str, Any]],
    sessions: list[registry.SessionRecord] | None = None,
    *,
    notice: str = "",
    defer: bool = False,
) -> str:
    records = sessions or []
    live = _live_count(records)
    accounts_placeholder = (
        "<div class='section rail' data-horus-src='/accounts-panel'>"
        "<details class='acct-panel' open><summary><span class='eyebrow'>Usage</span>"
        "<h3>Accounts</h3><span class='chev'>&#9656;</span></summary>"
        "<div class='acct-c'><p class='muted' style='margin:0'>Loading account usage...</p></div>"
        "</details></div>"
    )
    remote = render_remote_catalog_placeholder()
    if defer:
        # Paint instantly: the project section needs the ~1.2s gather_projects(), so
        # load it via the shared fetch loader as a sibling of the remote catalog.
        projects_part = (
            "<div data-horus-src='/projects-grid'><div class='greet'><div class='gtext'>"
            "<span class='eyebrow'>Cockpit</span><h2 class='muted'>Loading projects&hellip;</h2>"
            "</div></div></div>"
        )
    else:
        projects_part = _projects_section_html(projects)
    body_html = (
        f"{notice}<div class='wrap ov-shell'>{accounts_placeholder}<div class='ov-col'>"
        f"{projects_part}"
        f"<div class='band tight'>{remote}</div>"
        "</div></div>"
        f"{_footer_html()}"
    )
    return _page("Horus", body_html, live=live)

def _feature_buckets_detail_html(p: dict[str, Any]) -> str:
    items = p.get("feature_items") or {}
    labels = (("Planned", "planned", ""), ("In progress", "in_progress", "prog"), ("Shipped", "shipped", "ship"))
    buckets = []
    for label, key, cls in labels:
        vals = items.get(key, [])[:8]
        lis = "".join(f"<li>{html.escape(v)}</li>" for v in vals) or "<li class='muted'>No entries yet</li>"
        dot = "dot-q" if key == "planned" else "dot-p" if key == "in_progress" else "dot-s"
        buckets.append(
            f"<div class='bucket {cls}'><div class='bh'><i class='{dot}'></i>{html.escape(label)}"
            f"<span class='n'>{len(items.get(key, []))}</span></div><ul>{lis}</ul></div>"
        )
    return "<div class='buckets'>" + "".join(buckets) + "</div>"


def _latest_session_panel_html(p: dict[str, Any]) -> str:
    latest = p.get("latest")
    if not latest:
        return "<p class='lead' style='font-size:13.5px'>No sessions yet.</p>"
    text = latest.get("summary") or _session_summary_excerpt(p.get("latest_body", "")) or "(no summary)"
    return (
        f"<p class='lead' style='font-size:13.5px'>{html.escape(text)}</p>"
        "<dl class='kv' style='margin-top:14px'>"
        f"<dt>Date</dt><dd>{html.escape(latest.get('date', ''))}</dd>"
        f"<dt>Agent</dt><dd>{html.escape(latest.get('agent', '') or '-')}</dd>"
        f"<dt>Account</dt><dd>{html.escape(latest.get('account', '') or '-')}</dd>"
        f"<dt>Status</dt><dd>{html.escape(latest.get('status', '') or '-')}</dd>"
        "</dl>"
    )


def _cache_sidebar_panel(project_path: str) -> str:
    try:
        statuses = cache_status.project_cache_status(Path(project_path))
    except Exception as exc:
        return f"<p class='muted'>Context cache unavailable: {html.escape(str(exc))}</p>"
    if not statuses:
        return "<p class='muted'>No local Claude/Codex cache signal for this project yet.</p>"
    cards = []
    for s in statuses[:2]:
        cache_bits = []
        if s.cached_input_tokens:
            cache_bits.append(f"cached {_fmt_int(s.cached_input_tokens)}")
        if s.cache_read_input_tokens:
            cache_bits.append(f"read {_fmt_int(s.cache_read_input_tokens)}")
        if s.cache_creation_input_tokens:
            cache_bits.append(f"write {_fmt_int(s.cache_creation_input_tokens)}")
        cache_text = ", ".join(cache_bits) if cache_bits else "no cache tokens in last turn"
        cards.append(
            "<div class='metric'>"
            f"<div class='k'>{html.escape(s.agent)}</div>"
            f"<div class='v'>{html.escape(s.state())}</div>"
            f"<div class='muted' style='font-size:12px'>last turn {_fmt_duration(s.age_seconds())} ago</div>"
            f"<div class='muted' style='font-size:12px'>{html.escape(cache_text)}</div>"
            "</div>"
        )
    return "<div class='metrics'>" + "".join(cards) + "</div>"


def _manage_integration_panel(index: int, stale: bool) -> str:
    refresh = (
        "<form method='post' action='/upgrade-project'>"
        f"<input type='hidden' name='project' value='{index}'>"
        "<button class='btn btn-warn block' type='submit'>Refresh artifacts</button></form>"
        if stale else ""
    )
    keep_form = (
        "<form method='post' action='/offboard' onsubmit='return confirm(\"Remove Horus integration but KEEP the .horus/ files?\")'>"
        f"<input type='hidden' name='project' value='{index}'>"
        "<button class='btn block' type='submit'>Stop tracking - keep .horus/ files</button></form>"
    )
    remove_form = (
        "<form method='post' action='/offboard' onsubmit='return confirm(\"Delete EVERYTHING including the .horus/ memory? This cannot be undone.\")'>"
        f"<input type='hidden' name='project' value='{index}'>"
        "<input type='hidden' name='purge' value='1'>"
        "<button class='btn btn-danger block' type='submit'>Remove completely (delete .horus/)</button></form>"
    )
    return f"<div class='lform'>{refresh}{keep_form}{remove_form}</div>"


def _projection_sync_badge_html(p: dict[str, Any]) -> str:
    """Compact badge: does each agent surface (Claude vs Codex) carry the current
    generation of projected artifacts, compared to the installed CLI. Each surface
    is only ever compared to the CLI, never to the other surface - see
    horus.projection_sync. Sits next to the existing Refresh artifacts affordance."""
    state = p.get("projection_sync") or {}
    verdict = state.get("verdict", "unknown")
    if verdict == "in_sync":
        return "<span class='badge'><span class='gd'></span>Projections in sync</span>"
    if verdict == "cli_outdated":
        return "<span class='badge seal'><span class='gd'></span>&#9888; Horus CLI outdated</span>"
    badges = []
    if verdict in ("codex_behind", "behind"):
        n = state.get("codex", {}).get("pending", 0)
        badges.append(f"<span class='badge warn'><span class='gd'></span>Codex projection behind ({n})</span>")
    if verdict in ("claude_behind", "behind"):
        n = state.get("claude", {}).get("pending", 0)
        badges.append(f"<span class='badge warn'><span class='gd'></span>Claude projection behind ({n})</span>")
    if badges:
        return "".join(badges)
    return "<span class='muted' style='font-size:12px'>sync unknown</span>"


def render_project(p: dict[str, Any], *, index: int | None = None, notice: str = "") -> str:
    idx = 0 if index is None else index
    git = p.get("git") or {}
    branch = html.escape(git.get("branch") or "-")
    git_state = "clean" if not git.get("dirty") else "uncommitted"
    status_badges = (
        f"<span class='branch'>branch {branch}</span>"
        f"<span class='muted'>- {git_state}</span>"
        f"{_health_dot(p)}"
        f"<span class='badge'>status {html.escape(p['status']) or 'unknown'}</span>"
        f"<span class='badge'><b class='mono'>{len(p['sessions'])}</b>&nbsp;sessions</span>"
        f"{_projection_sync_badge_html(p)}"
    )
    refresh = _upgrade_button(idx) if p.get("artifacts_stale") and index is not None else ""
    aliases = [{"alias": a} for a in sorted(_known_aliases())]
    focus = html.escape(p.get("current_focus") or p.get("tagline") or "No current focus recorded yet.")
    roadmap_progress = _road_progress_html(p, href="#roadmap")
    main_parts = [
        "<div class='panel'><div class='ph'><span class='eyebrow'>Current focus</span><span class='x mono'>.horus/project.md</span></div>"
        f"<p class='lead'>{focus}</p></div>",
        "<div class='panel' id='roadmap'><div class='ph'><span class='eyebrow'>Roadmap - next</span><span class='x mono'>.horus/roadmap.md</span></div>"
        f"{_single_next_html(p)}{roadmap_progress}</div>",
        "<div class='panel' id='features'><div class='ph'><span class='eyebrow'>Features ledger</span><span class='x mono'>.horus/features.md</span></div>"
        f"{_feature_buckets_detail_html(p)}</div>",
    ]
    if p.get("artifacts_stale"):
        main_parts.append(
            "<div class='panel'><div class='ph'><span class='eyebrow'>Artifacts outdated</span></div>"
            f"<p class='lead' style='font-size:13.5px'>&#9888; artifacts outdated - {html.escape(str(p.get('artifacts_stale_count', 0)))} item(s) behind the installed CLI. "
            "Run <code>horus upgrade-project --apply</code> or use Refresh artifacts.</p></div>"
        )
    if p.get("cli_outdated"):
        main_parts.append(
            "<div class='panel'><div class='ph'><span class='eyebrow'>Horus CLI outdated</span></div>"
            "<p class='lead' style='font-size:13.5px'>&#9888; this project's Horus artifacts are "
            "<em>newer</em> than the installed CLI &mdash; refreshing would downgrade them. "
            "Update horus-harness itself, then restart Horus.</p>"
            "<form method='post' action='/self-update' "
            "onsubmit=\"return confirm('Run uv tool upgrade horus-harness? Horus must be restarted afterwards to load it.')\">"
            "<button class='btn sm btn-go' type='submit'>Update horus-harness from PyPI</button></form></div>"
        )
    rows = "".join(
        f"<tr><td class='{_LEVEL_CLASS.get(f['level'], '')}'>{html.escape(f['level'])}</td>"
        f"<td>{html.escape(f['message'])}</td></tr>"
        for f in p["findings"]
    ) or "<tr><td>ok</td><td>healthy</td></tr>"
    main_parts.append(
        "<div class='panel'><div class='ph'><span class='eyebrow'>Continuity health</span></div>"
        f"<table>{rows}</table></div>"
    )
    if p.get("decisions_body") or p.get("history_body"):
        decisions_part = ""
        if p.get("decisions_body") and index is not None:
            decisions_part = (
                "<details class='tasks'><summary>Durable decisions</summary>"
                f"{markdown.render(p.get('decisions_body', ''))}</details>"
                f"<div style='margin-top:8px'>{_open_lane_button(idx, 'decisions', 'Open decisions.md')}</div>"
            )
        elif p.get("decisions_body"):
            decisions_part = (
                "<details class='tasks' open><summary>Durable decisions</summary>"
                f"{markdown.render(p.get('decisions_body', ''))}</details>"
            )
        history_part = ""
        if p.get("history_body"):
            # History grows without bound and holds the full rationale; keep it out of
            # the dashboard render and offer an editor link instead.
            note = "<p class='muted' style='font-size:13px;margin:0 0 8px'>History holds the full rationale and bumps in the road. It grows over time, so it's kept out of the dashboard."
            note += " Open it in your editor for the detail.</p>" if index is not None else "</p>"
            history_part = note + (_open_lane_button(idx, "history", "Open history.md") if index is not None else "")
        main_parts.append(
            "<div class='panel'><div class='ph'><span class='eyebrow'>Decisions &amp; history</span>"
            "<span class='x mono'>.horus/decisions.md - history.md</span></div>"
            f"{decisions_part}{history_part}</div>"
        )
    if p.get("execution_body"):
        main_parts.append(
            "<div class='panel' id='execution'><div class='ph'><span class='eyebrow'>Execution plan</span>"
            "<span class='x mono'>.horus/execution.md</span></div>"
            f"{markdown.render(p['execution_body'])}</div>"
        )
    if p.get("roadmap_body"):
        open_btn = (
            f"<div style='margin-top:10px'>{_open_lane_button(idx, 'roadmap', 'Open roadmap.md')}</div>"
            if index is not None else ""
        )
        main_parts.append(
            "<div class='panel'><div class='ph'><span class='eyebrow'>Roadmap details</span>"
            "<span class='x mono'>open items</span></div>"
            f"{_breakdown_html(p, completed=False)}{open_btn}</div>"
        )
    if index is not None:
        # Heavy: parses Claude/Codex session logs (~seconds). Load it lazily so the
        # page paints immediately; the shared fetch loader swaps in the real panel.
        main_parts.append(
            f"<div class='panel' data-horus-src='/project-overhead?i={idx}'>"
            "<div class='ph'><span class='eyebrow'>Token overhead</span></div>"
            "<p class='muted' style='font-size:12.5px'>Loading&hellip;</p></div>"
        )
    else:
        main_parts.append(_project_overhead_html(p["path"]).replace("class='section'", "class='panel'"))
    if index is not None:
        # Same lazy pattern: transcript scanning is disk-heavy, keep it off the paint.
        main_parts.append(
            f"<div class='panel' data-horus-src='/project-sessions?i={idx}'>"
            "<div class='ph'><span class='eyebrow'>Recent sessions</span></div>"
            "<p class='muted' style='font-size:12.5px'>Loading&hellip;</p></div>"
        )
    if index is not None:
        cache_panel = (
            f"<div class='panel' data-horus-src='/project-cache?i={idx}'>"
            "<div class='ph'><span class='eyebrow'>Context cache</span></div>"
            "<p class='muted' style='font-size:12.5px'>Loading&hellip;</p></div>"
        )
    else:
        cache_panel = (
            "<div class='panel'><div class='ph'><span class='eyebrow'>Context cache</span></div>"
            f"{_cache_sidebar_panel(p['path'])}</div>"
        )
    sidebar = (
        "<div class='col'><div class='panel sticky'><h3>"
        f"{_eye_glyph()}Start a session</h3>"
        "<p class='muted' style='font-size:12.5px;margin:0 0 16px'>Launch an attended CLI against this repo.</p>"
        f"{_project_launch_form(idx, p, aliases)}</div>"
        f"{cache_panel}"
        "<div class='panel'><div class='ph'><span class='eyebrow'>Last session</span></div>"
        f"{_latest_session_panel_html(p)}</div>"
        "<div class='panel'><div class='ph'><span class='eyebrow'>Manage Horus integration</span></div>"
        f"{_manage_integration_panel(idx, bool(p.get('artifacts_stale'))) if index is not None else ''}</div></div>"
    )
    body = (
        f"{notice}<section class='band'><div class='wrap'>"
        f"<div class='crumb'><a href='/'>Projects</a><span>/</span><span class='mono'>{html.escape(p['name'])}</span></div>"
        "<div class='detail-top'><div>"
        f"<h1>{html.escape(p['name'])}</h1><div class='sub'>{status_badges}</div></div>"
        f"<div class='right'>{refresh}<a class='btn' href='/'>Back</a></div></div>"
        f"<div class='dlayout'><div class='col'>{''.join(main_parts)}</div>{sidebar}</div>"
        "</div></section>"
        f"{_footer_html()}"
    )
    return _page(f"Horus - {p['name']}", body, live=_live_count(gather_sessions()))

_LANE_FILES = {
    "project": "project.md", "roadmap": "roadmap.md", "features": "features.md",
    "decisions": "decisions.md", "history": "history.md", "execution": "execution.md",
}


def _open_in_editor(path: Path) -> None:
    """Open a local lane file in the OS default handler. Best-effort; the dashboard
    is local-only, so this runs on the user's own machine."""
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError:
        pass


def _open_lane_button(index: int, lane: str, label: str) -> str:
    """A same-origin POST button that opens one `.horus/<lane>.md` in the editor."""
    return (
        "<form method='post' action='/open-lane' style='display:inline'>"
        f"<input type='hidden' name='project' value='{index}'>"
        f"<input type='hidden' name='lane' value='{html.escape(lane, quote=True)}'>"
        f"<button class='btn sm' type='submit'>{html.escape(label)}</button></form>"
    )


def process_open_lane(form: dict[str, list[str]]) -> str:
    """Open a project's lane file in the OS editor; addressed by index, lane allow-listed."""
    try:
        idx = int(form.get("project", [""])[0])
        project = config.load_projects()[idx]
    except (ValueError, IndexError):
        return "/"
    lane = form.get("lane", [""])[0]
    fname = _LANE_FILES.get(lane)
    if fname:
        path = Path(project) / HORUS_DIR / fname
        if path.is_file():
            _open_in_editor(path)
    return f"/project?i={idx}"


def _upgrade_button(index: int) -> str:
    """A one-click 'apply upgrade-project' button (same-origin POST, project by index)."""
    return (
        " <form method='post' action='/upgrade-project' style='display:inline'>"
        f"<input type='hidden' name='project' value='{index}'>"
        "<button class='btn btn-go' type='submit' "
        "title='Refresh Horus-managed artifacts to the installed version'>Refresh now</button>"
        "</form>"
    )


def _offload_control(index: int, *, compact: bool = False) -> str:
    """Offload a project: two explicit choices — *Keep files* (remove the projected
    artifacts + unregister, keep `.horus/`) or *Remove completely* (also delete
    `.horus/`). ``compact`` renders a `<details>` reveal for the overview card; the full
    form renders a labelled section for the detail page.
    """
    keep_form = (
        "<form method='post' action='/offboard' style='display:inline' "
        "onsubmit='return confirm(\"Remove Horus integration but KEEP the .horus/ files?\")'>"
        f"<input type='hidden' name='project' value='{index}'>"
        "<button class='btn-keep' type='submit'>Keep files</button></form>"
    )
    remove_form = (
        "<form method='post' action='/offboard' style='display:inline' "
        "onsubmit='return confirm(\"Delete EVERYTHING including the .horus/ memory? "
        "This cannot be undone.\")'>"
        f"<input type='hidden' name='project' value='{index}'>"
        "<input type='hidden' name='purge' value='1'>"
        "<button class='btn-danger' type='submit'>Remove completely</button></form>"
    )
    actions = f"<div class='offload-actions'>{keep_form}{remove_form}</div>"
    if compact:
        return (
            "<details class='offload'><summary>Offload project</summary>"
            "<p class='muted' style='font-size:12px;margin:8px 0 0'>Keep files removes the Horus "
            "integration but leaves <code>.horus/</code>; Remove completely deletes it too.</p>"
            f"{actions}</details>"
        )
    return (
        "<div class='section'><h2>Manage Horus integration</h2><div class='card'>"
        "<p class='muted'>Offload this project. <strong>Keep files</strong> removes the projected "
        "artifacts (managed block, skills, hooks) and unregisters it but leaves the "
        "<code>.horus/</code> memory; <strong>Remove completely</strong> also deletes "
        "<code>.horus/</code> (irreversible).</p>"
        f"{actions}</div></div>"
    )


# --------------------------------------------------------------------------- #
# Control panel — accounts (usage rings) + projects (launch) + live sessions
# --------------------------------------------------------------------------- #

def _usage_color(pct: float) -> str:
    return "#f08a8a" if pct >= 90 else "#e6c35c" if pct >= 70 else "#57d39a"


def _ring(pct: float | None) -> str:
    """Small donut showing a usage percent; gray when unknown (offline/no token)."""
    if pct is None:
        color, dash, txt = "var(--border)", 0.0, "--"
    else:
        v = max(0.0, min(100.0, pct))
        if v >= 80:
            color = "var(--seal)"
        elif v >= 35:
            color = "var(--ink-3)"
        else:
            color = "var(--border-strong)"
        dash, txt = v, f"{v:.0f}%"
    return (
        "<div class='ring-wrap'><svg class='ring' viewBox='0 0 40 40'>"
        "<circle class='track' cx='20' cy='20' r='17' pathLength='100'/>"
        f"<circle class='meter' cx='20' cy='20' r='17' pathLength='100' stroke='{color}' "
        f"stroke-dasharray='{dash:.0f} 100'/>"
        f"</svg><span class='ring-num'>{txt}</span></div>"
    )


def _usage_bar(pct: float | None, label: str) -> str:
    fill = ""
    if pct is not None:
        v = max(0.0, min(100.0, pct))
        color = "var(--seal)" if v >= 80 else "var(--ink-3)" if v >= 35 else "var(--border-strong)"
        fill = f"<i style='width:{v:.0f}%;background:{color}'></i>"
    return (
        f"<div class='wbar mini'><div class='lab'><b>{html.escape(label)}</b></div>"
        f"<div class='track-bar'>{fill}</div></div>"
    )


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



def _accounts_strip(accounts: list[dict[str, Any]]) -> str:
    """Sticky overview accounts rail: usage rings, alias editing, add/remove, launch."""
    add_form = _account_add_form()
    shell_start = (
        "<div class='section'><div class='rail'><details class='acct-panel' open>"
        "<summary><span class='eyebrow'>Usage</span><h3>Accounts</h3><span class='chev'>&#9656;</span></summary>"
    )
    shell_end = (
        "</details><p class='muted' style='font-size:11.5px;margin:13px 4px 0;line-height:1.5'>"
        "Subscription auth only - friendly aliases shown, never raw account emails or IDs.</p></div></div>"
    )
    if not accounts:
        return (
            shell_start
            + "<div class='acct-c'><p class='muted' style='font-size:13px;margin:0'>No agent account detected. Run "
            "<code>claude</code> / <code>codex login</code>, or add an isolated account below.</p></div>"
            f"<div class='acct-foot2'>{add_form}</div>"
            + shell_end
        )

    rows = []
    for a in accounts:
        agent = a.get("agent", "claude")
        provider_cls = " codex" if agent == "codex" else ""
        provider = "Codex" if agent == "codex" else "Claude"
        reset = f"<span class='when2'>5h resets {html.escape(a['five_reset'])}</span>" if a.get("five_reset") else ""
        week_bar = ""
        if a.get("week_pct") is not None:
            label = f"Weekly {a['week_pct']:.0f}%"
            if a.get("week_reset"):
                label += f" - resets {a['week_reset']}"
            week_bar = _usage_bar(a["week_pct"], label)
        rows.append(
            "<div class='acct-c'><div class='acct-row'>"
            f"{_ring(a['five_pct'])}<div class='info'>{_account_alias_form(a)}"
            f"<div class='prov-line'><span class='tag-prov{provider_cls}'>{provider}</span>{reset}</div></div>"
            f"{_account_launch_form(a['alias'], agent)}</div>{week_bar}</div>"
        )
    remove = (
        "<details class='remove-pop'><summary><span class='chev'>&#9656;</span>Remove an account</summary>"
        "<div class='menu'>" + "".join(_account_remove_form(a["alias"]) for a in accounts) + "</div></details>"
    )
    return shell_start + "".join(rows) + f"<div class='acct-foot2'>{add_form}{remove}</div>" + shell_end


def _account_alias_form(account: dict[str, Any]) -> str:
    alias = account.get("alias", "")
    agent = account.get("agent", "claude")
    return (
        "<form class='alias-edit' method='post' action='/account-alias'>"
        f"<input type='hidden' name='agent' value='{html.escape(agent, quote=True)}'>"
        f"<input type='hidden' name='old_alias' value='{html.escape(alias, quote=True)}'>"
        f"<input class='alias-in' name='alias' value='{html.escape(alias, quote=True)}' aria-label='Account alias'>"
        "<button class='icon-btn' type='submit' title='Save alias'>&#10003;</button>"
        "</form>"
    )


def _account_add_form() -> str:
    return (
        "<details class='disc'><summary><span class='chev'>&#9656;</span>+ Add account</summary>"
        "<form class='lform disc-body' method='post' action='/account-login'>"
        "<div class='field'><label>Agent</label><select name='agent'>"
        "<option value='claude'>Claude</option><option value='codex'>Codex</option>"
        "</select></div>"
        "<div class='field'><label>Alias</label><input name='alias' placeholder='personal' required></div>"
        "<button class='btn btn-go block' type='submit'>Add &amp; sign in</button>"
        "<p class='muted' style='font-size:12px;margin:0'>Creates an isolated login directory "
        "under <code>~/.horus/accounts/</code> and opens a terminal to sign in - no path to "
        "enter. The directory is filled by the login itself.</p>"
        "</form></details>"
    )


def _account_launch_form(alias: str, agent: str = "claude") -> str:
    """One-click fresh session as this account in a native OS terminal."""
    return (
        "<form class='acct-launch' method='post' action='/launch' style='display:inline'>"
        f"<input type='hidden' name='account' value='{html.escape(alias, quote=True)}'>"
        f"<input type='hidden' name='agent' value='{html.escape(agent, quote=True)}'>"
        "<input type='hidden' name='mode' value='fresh'>"
        "<button class='mini-session' type='submit' name='target' value='window' "
        "title='+ session - open a fresh session as this account in a native terminal'>+</button></form>"
    )


def _account_remove_form(alias: str) -> str:
    """Forget an account mapping; login dir on disk is left intact."""
    return (
        "<form method='post' action='/account-remove' style='display:block' "
        "onsubmit='return confirm(\"Remove this account from Horus? (its login files are left on disk)\")'>"
        f"<input type='hidden' name='alias' value='{html.escape(alias, quote=True)}'>"
        "<button class='btn btn-danger block' type='submit' title='Forget this account'>"
        f"{html.escape(alias)} <span class='x'>remove</span></button></form>"
    )

def _launch_cmds(project_path: str, accounts: list[dict[str, Any]]) -> str:
    """Copyable real launch commands: Claude + Codex (ambient), then one per known account."""
    cmds = [
        f'horus open "{project_path}"',
        f'horus open "{project_path}" --agent codex',
    ]
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
    """Pick agent/account/posture and launch fresh or resume in a native window."""
    opts = "<option value=''>ambient</option>" + "".join(
        f"<option value='{html.escape(a['alias'], quote=True)}'>{html.escape(a['alias'])}</option>"
        for a in accounts
    )
    return (
        "<form class='lform' method='post' action='/launch'>"
        f"<input type='hidden' name='project' value='{i}'>"
        "<div class='frow'>"
        "<div class='field'><label>Agent</label><select name='agent'>"
        "<option value='claude'>Claude Code</option><option value='codex'>Codex</option>"
        "</select></div>"
        f"<div class='field'><label>Account</label><select name='account'>{opts}</select></div>"
        "</div>"
        "<div class='frow'>"
        f"<div class='field'><label>Permission posture</label><select name='posture'>{_POSTURE_OPTIONS}</select></div>"
        "<div class='field'><label>Open in</label><select name='target'>"
        "<option value='window'>Native terminal</option>"
        "<option value='vscode'>VS Code</option>"
        "</select></div>"
        "</div>"
        "<div class='intent-row'>"
        "<button class='btn btn-go' type='submit' name='mode' value='resume'>&#9656; Resume - next action</button>"
        "<button class='btn' type='submit' name='mode' value='fresh'>Fresh session</button>"
        "</div>"
        f"<div hidden>{_launch_cmds(project['path'], accounts)}</div>"
        "</form>"
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
    if "vscode" in params:
        name = html.escape(params["vscode"][0])
        return (
            f"<div class='banner ok'>Opened <code>{name}</code> in VS Code &mdash; start "
            "the agent there (Claude extension or integrated terminal); the fresh/resume "
            "prompt is copyable on the project page.</div>"
        )
    if "error" in params:
        return f"<div class='banner err'>Launch failed: {html.escape(params['error'][0])}</div>"
    if params.get("account") == ["added"]:
        return "<div class='banner ok'>Account mapping added.</div>"
    if params.get("account") == ["alias"]:
        return "<div class='banner ok'>Account alias updated.</div>"
    if params.get("account") == ["removed"]:
        return "<div class='banner ok'>Account removed from Horus (login files left on disk).</div>"
    if params.get("account") == ["absent"]:
        return "<div class='banner err'>Nothing to remove for that account.</div>"
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


def process_account_remove(form: dict[str, str]) -> str:
    alias = (form.get("alias") or "").strip()
    if not alias:
        return "error=" + quote_plus("account alias is required")
    removed = config.remove_account(alias)
    return "account=removed" if removed else "account=absent"


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


def _project_by_index(form: dict[str, str], projects: list[str] | None) -> tuple[Path | None, int | None]:
    """Resolve a project POST by its index into the registered list (same safety model
    as /launch — never an arbitrary path)."""
    projects = config.load_projects() if projects is None else projects
    raw = (form.get("project") or "").strip()
    try:
        idx = int(raw)
        return Path(projects[idx]), idx
    except (ValueError, IndexError):
        return None, None


def process_upgrade_project(form: dict[str, str], *, projects: list[str] | None = None) -> str:
    """Apply `upgrade-project` to a registered project (by index). Returns a redirect
    location back to the project detail page with a result count."""
    root, idx = _project_by_index(form, projects)
    if root is None:
        return "/?upgrade_error=" + quote_plus("unknown project")
    if _stale_build():
        return f"/project?i={idx}&stale_build=1"
    actions = upgrade.upgrade_project(root, apply=True)
    updated = sum(1 for a in actions if a.status in ("updated", "created"))
    return f"/project?i={idx}&upgraded={updated}"


def process_offboard(form: dict[str, str], *, projects: list[str] | None = None) -> str:
    """Offboard a registered project (by index): remove projected artifacts + unregister,
    purging `.horus/` only when the purge box is ticked. Redirects to the overview (the
    project is no longer registered, so its index is gone)."""
    root, _ = _project_by_index(form, projects)
    if root is None:
        return "/?offboard_error=" + quote_plus("unknown project")
    if _stale_build():
        return "/?stale_build=1"
    purge = (form.get("purge") or "").strip().lower() in ("1", "true", "on", "yes")
    name = root.name
    offboard.offboard_project(root, apply=True, purge=purge)
    return "/?offboarded=" + quote_plus(name) + ("&purged=1" if purge else "")


def _notice(params: dict[str, list[str]]) -> str:
    """Unified post-redirect banner: project actions (upgrade/offboard) + launch/account."""
    return _project_action_banner(params) or _launch_notice(params)


def _project_action_banner(params: dict[str, list[str]]) -> str:
    """Banner for upgrade/offboard POST redirects (index + project pages)."""
    if "selfupdated" in params:
        return (
            f"<div class='banner ok'>{html.escape(params['selfupdated'][0])} &mdash; "
            "restart Horus to load the new version (the running server keeps its old build).</div>"
        )
    if "selfupdate_error" in params:
        return f"<div class='banner err'>Self-update failed: {html.escape(params['selfupdate_error'][0])}</div>"
    if "stale_build" in params:
        return (
            "<div class='banner err'>Refused: this dashboard is running an old build &mdash; "
            "an in-process write would stamp the project with an outdated artifact generation. "
            "Restart Horus, then retry.</div>"
        )
    if "upgraded" in params:
        n = html.escape(params["upgraded"][0])
        return f"<div class='banner ok'>Refreshed Horus artifacts &mdash; {n} item(s) updated.</div>"
    if "upgrade_error" in params:
        return f"<div class='banner err'>Upgrade failed: {html.escape(params['upgrade_error'][0])}</div>"
    if "offboarded" in params:
        name = html.escape(params["offboarded"][0])
        extra = " and deleted its <code>.horus/</code> memory" if "purged" in params else " (<code>.horus/</code> kept)"
        return f"<div class='banner ok'>Removed Horus from {name}{extra}.</div>"
    if "offboard_error" in params:
        return f"<div class='banner err'>Offboard failed: {html.escape(params['offboard_error'][0])}</div>"
    if "onboarded" in params:
        name = html.escape(params["onboarded"][0])
        pr = params.get("onboard_pr", [""])[0]
        pr_html = (
            f" Continuity PR: <a href='{html.escape(pr, quote=True)}'>{html.escape(pr)}</a>."
            if pr else ""
        )
        out = (
            f"<div class='banner ok'>Onboarded {name} &mdash; start a session below.{pr_html}</div>"
        )
        if "onboard_detail" in params:
            out += (
                "<div class='banner err'>Integration incomplete: "
                f"{html.escape(params['onboard_detail'][0])}</div>"
            )
        return out
    if "onboard_error" in params:
        return f"<div class='banner err'>Onboard failed: {html.escape(params['onboard_error'][0])}</div>"
    return ""


def process_launch(
    form: dict[str, str],
    *,
    projects: list[str] | None = None,
    known_aliases: set[str] | None = None,
) -> str:
    """Handle a Control-tab launch request; return the query string to redirect
    ``/control`` to. ``target=app`` (default) opens an in-app terminal tab
    (``tab=<client_id>``); ``target=window`` opens an OS console (``launched=<id8>``);
    ``target=vscode`` opens/focuses the project folder in VS Code (``vscode=<name>``)
    without spawning or registering an agent session. Failures return
    ``error=<reason>``.

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

    if target == "vscode":
        # A destination, not a session: open/focus the folder in VS Code and stop.
        # The user starts the agent there themselves, so mode/agent/posture don't
        # apply and a resume prompt is never injected into a surface Horus doesn't
        # control — its copyable text stays on the project page.
        try:
            launcher.open_vscode(project_dir)
        except OSError as exc:
            return "error=" + quote_plus(str(exc))
        return "vscode=" + quote_plus(project_dir.name)

    if raw_project != "" and mode == "resume":
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
            # Paint the shell immediately; the project grid (gather_projects ~1.2s)
            # loads async via /projects-grid, like the accounts strip and catalog.
            self._send(render_index(
                [], gather_sessions(),
                notice=_notice(parse_qs(parsed.query)), defer=True,
            ))
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
            # Control (the session cockpit) was retired; its useful bits moved to the
            # Projects tab. Redirect old links/bookmarks there.
            self._redirect("/")
            return
        if parsed.path == "/accounts-panel":
            # Async fragment for the main-tab accounts/usage strip (network — loaded lazily).
            self._send(_accounts_strip(gather_accounts()))
            return
        if parsed.path == "/projects-grid":
            # Async fragment for the index project section (greeting + grid); carries
            # the ~1.2s gather_projects cost off the initial paint.
            self._send(_projects_section_html(gather_projects()))
            return
        if parsed.path in ("/project-overhead", "/project-cache", "/project-sessions"):
            # Heavy per-project panels (session-log parsing) loaded lazily so the
            # detail page paints immediately. Project addressed by index, never path.
            projects = gather_projects()
            try:
                idx = int(parse_qs(parsed.query).get("i", ["?"])[0])
                path = projects[idx]["path"]
            except (ValueError, IndexError):
                self._send("<div class='panel'><p class='muted'>Unknown project.</p></div>", 404)
                return
            if parsed.path == "/project-overhead":
                self._send(_project_overhead_html(path).replace("class='section'", "class='panel'"))
            elif parsed.path == "/project-sessions":
                self._send(_project_sessions_html(path))
            else:
                self._send(
                    "<div class='panel'><div class='ph'><span class='eyebrow'>Context cache</span></div>"
                    f"{_cache_sidebar_panel(path)}</div>"
                )
            return
        if parsed.path == "/update-check":
            # Async top-nav fragment; a failed/offline check renders as up-to-date.
            self._send(_update_pill_html())
            return
        if parsed.path == "/health":
            # Machine-readable identity for the companion: lets a starting mascot
            # tell a current dashboard from a stale orphan (and from a foreign
            # server) before adopting the port.
            payload = json.dumps(
                {"app": "horus-dashboard", "version": __version__, "pid": os.getpid()}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
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
        if parsed.path == "/assets/mascot.png":
            self._send_package_asset("mascot.png", "image/png")
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
            self._send(render_project(
                project, index=idx,
                notice=_notice(parse_qs(parsed.query)),
            ))
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
            "/self-update",
            "/upgrade-project",
            "/offboard",
            "/open-lane",
            "/account-add",
            "/account-login",
            "/account-alias",
            "/account-remove",
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

        if parsed.path == "/self-update":
            ok, detail = selfupdate.run_upgrade()
            if ok:
                self._redirect(f"/?selfupdated={quote_plus(detail)}")
            else:
                self._redirect(f"/?selfupdate_error={quote_plus(detail)}")
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
        if parsed.path == "/upgrade-project":
            self._redirect(process_upgrade_project(self._read_form()))
            return
        if parsed.path == "/offboard":
            self._redirect(process_offboard(self._read_form()))
            return
        if parsed.path == "/open-lane":
            self._redirect(process_open_lane(self._read_form()))
            return
        if parsed.path == "/account-add":
            self._redirect(f"/?{process_account_add(self._read_form())}")
            return
        if parsed.path == "/account-login":
            self._redirect(f"/?{process_account_login(self._read_form())}")
            return
        if parsed.path == "/account-remove":
            self._redirect(f"/?{process_account_remove(self._read_form())}")
            return
        if parsed.path == "/account-alias":
            self._redirect(f"/?{process_account_alias(self._read_form())}")
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
            if self.headers.get("X-Horus-Fetch"):
                self._no_content()  # in-place JS removal; no reload
            else:
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
            # PRG like ignore/unignore — the POST must never answer with a raw
            # catalog fragment at /github-onboard (unstyled page, F5 re-onboards).
            if _stale_build():
                self._redirect("/?stale_build=1#github-catalog")
                return
            form = self._read_form()
            target = form.get("target", "")
            owner = target.split("/")[0] if "/" in target else target
            if owner not in config.load_github_owners():
                self._redirect(
                    "/?onboard_error="
                    + quote_plus(f"refusing to onboard untrusted repo: {target}")
                    + "#github-catalog"
                )
                return
            try:
                result = remote_start.onboard_github_project(f"github:{target}")
            except (RuntimeError, ValueError) as exc:
                self._redirect("/?onboard_error=" + quote_plus(str(exc)) + "#github-catalog")
                return
            integ = result.integration
            params = "onboarded=" + quote_plus(target)
            if getattr(integ, "pr_url", None):
                params += "&onboard_pr=" + quote_plus(str(integ.pr_url))
            if not integ.ok:
                params += "&onboard_detail=" + quote_plus(integ.detail)
            # Land on the new project's detail page: its "Start a session" card is
            # the post-onboard CTA (accounts chooser + fresh/resume launch).
            idx = _project_index(result.path) if result.registered else None
            if idx is not None:
                self._redirect(f"/project?i={idx}&{params}")
            else:
                self._redirect(f"/?{params}#github-catalog")
            return

        form = self._read_form()
        query = process_launch(form)
        # PRG: redirect back to the project detail page (or the index for an account-only
        # session) so a refresh doesn't re-submit the launch.
        raw = (form.get("project") or "").strip()
        self._redirect(f"/project?i={raw}&{query}" if raw.isdigit() else f"/?{query}")

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
