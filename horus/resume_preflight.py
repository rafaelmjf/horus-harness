"""Compact, deterministic session-start projection for ``horus resume``.

The projection composes existing Horus readers.  It never interprets capacity,
recommends a next step, chooses a model/account, or writes state.  Its only
sanctioned side effect is the caller-requested ``git fetch --all --prune``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from horus import closure, datums, fetchcheck, frontmatter, gitstate, registry, versioning


def _compact(value: object, fallback: str = "-") -> str:
    text = " ".join(str(value or "").split())
    return text or fallback


def _project_key(path: str | Path) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(Path(path))


def _git_projection(root: Path, *, do_fetch: bool) -> dict[str, Any]:
    try:
        state = (
            fetchcheck.fetch_and_state(root, ttl=0)
            if do_fetch
            else gitstate.git_state(root)
        )
    except Exception:  # noqa: BLE001 - a signal failure must not break the digest
        state = None
    if state is None:
        return {
            "available": False,
            "fetch": "failed" if do_fetch else "skipped",
            "branch": None,
            "ahead": None,
            "behind": None,
            "dirty": None,
            "upstream_gone": None,
        }
    tracks_upstream = bool(state.get("upstream")) and not state.get("own_upstream_gone")
    return {
        "available": True,
        "fetch": state.get("fetch_status", "unknown") if do_fetch else "skipped",
        "branch": state.get("branch"),
        "upstream": state.get("upstream"),
        "compare_ref": (
            (state.get("upstream") if tracks_upstream else None)
            or (f"origin/{state['default_branch']}" if state.get("default_branch") else None)
        ),
        "ahead": state.get("ahead") if tracks_upstream else state.get("default_ahead"),
        "behind": state.get("behind") if tracks_upstream else state.get("default_behind"),
        "dirty": bool(state.get("dirty")),
        "upstream_gone": bool(state.get("own_upstream_gone")),
        "detached": bool(state.get("detached")),
    }


def _project_projection(root: Path, *, installed: str, do_fetch: bool) -> dict[str, Any]:
    floor = versioning.read_floor(root)
    focus = frontmatter.resolve_focus(root)
    hygiene = [
        {"level": finding.level, "message": finding.message}
        for finding in closure.freshness_gate(root) + closure.checkpoint_gate(root)
        if finding.level in {"warn", "fail"}
    ]
    return {
        "name": root.name,
        "path": str(root),
        "git": _git_projection(root, do_fetch=do_fetch),
        "version": {
            "installed": installed,
            "floor": floor,
            "meets_floor": floor is None or versioning.is_at_least(installed, floor),
        },
        "handoff": {
            key: focus.get(key, "")
            for key in (
                "current_focus",
                "next_action",
                "next_prompt",
                "execution_recommendation",
            )
        },
        "hygiene": hygiene,
    }


def _session_projection(project_paths: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        records = registry.Registry.default().snapshot()
    except Exception:  # noqa: BLE001 - best-effort machine-local signal
        records = []
    visible = [
        record for record in records
        if record.status in {"running", "stale"} and _project_key(record.project) in project_paths
    ]
    visible.sort(key=lambda record: (record.status != "running", record.project, record.session_id))
    sessions = [
        {
            "session_id": record.session_id,
            "status": record.status,
            "agent": record.agent,
            "account": record.account,
            "project": record.project,
            "pid": record.pid,
            "updated_at": record.updated_at,
        }
        for record in visible
    ]

    by_project: dict[str, list[registry.SessionRecord]] = defaultdict(list)
    for record in visible:
        if record.status == "running":
            by_project[_project_key(record.project)].append(record)
    collisions = [
        {
            "project": records[0].project,
            "count": len(records),
            "sessions": [record.session_id for record in records],
        }
        for records in by_project.values()
        if len(records) > 1
    ]
    collisions.sort(key=lambda item: item["project"])
    return sessions, collisions


def gather(
    roots: Iterable[Path],
    *,
    installed: str,
    do_fetch: bool = True,
    mode: str = "project",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Gather the preflight digest as a JSON-safe, read-only data projection."""
    stamp = now or datetime.now(timezone.utc)
    normalized = [Path(root).expanduser().resolve() for root in roots]
    projects = [
        _project_projection(root, installed=installed, do_fetch=do_fetch)
        for root in normalized
    ]
    usage = datums.capture_usage_snapshot(
        None,
        None,
        since=stamp.isoformat(timespec="seconds"),
        persist_cache=False,
    )
    try:
        open_datums = [
            {
                "session_id": datum.session_id,
                "model": datum.model,
                "agent": datum.agent,
                "project": datum.project,
                "launched_at": datum.launched_at,
                "exit": datum.exit,
            }
            for datum in datums.DatumStore.default().all()
            if datum.closed_at is None
        ]
    except Exception:  # noqa: BLE001 - best-effort machine-local signal
        open_datums = []
    open_datums.sort(key=lambda item: (item["launched_at"] or "", item["session_id"]), reverse=True)
    sessions, collisions = _session_projection({_project_key(root) for root in normalized})
    return {
        "schema": 1,
        "mode": mode,
        "generated_at": stamp.isoformat(timespec="seconds"),
        "fetch": "enabled" if do_fetch else "skipped",
        "usage": usage,
        "open_datums": open_datums,
        "sessions": sessions,
        "collisions": collisions,
        "projects": projects,
    }


def _pct(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    return "?" if value is None else f"{value:g}%"


def render_text(digest: dict[str, Any]) -> str:
    """Render one compact block: lean status lines, never command output."""
    lines = [
        f"HORUS PREFLIGHT | mode={digest['mode']} | fetch={digest['fetch']} | at={digest['generated_at']}"
    ]
    for target in ("codex", "claude"):
        entry = digest.get("usage", {}).get(target, {})
        lines.append(
            f"USAGE {target} [{str(entry.get('freshness', 'unavailable')).upper()}] "
            f"5h={_pct(entry, 'pct_5h')} weekly={_pct(entry, 'pct_weekly')} "
            f"context={_pct(entry, 'pct_context')} read={entry.get('read_at', '-')}"
        )
    for project in digest.get("projects", []):
        git = project["git"]
        if git["available"]:
            branch = "detached" if git.get("detached") else _compact(git.get("branch"))
            git_text = (
                f"branch={branch} vs={_compact(git.get('compare_ref'))} "
                f"ahead={git.get('ahead') if git.get('ahead') is not None else '?'} "
                f"behind={git.get('behind') if git.get('behind') is not None else '?'} "
                f"dirty={'yes' if git.get('dirty') else 'no'} "
                f"upstream-gone={'yes' if git.get('upstream_gone') else 'no'} fetch={git.get('fetch')}"
            )
        else:
            git_text = f"unavailable fetch={git.get('fetch')}"
        version = project["version"]
        floor = version.get("floor") or "none"
        verdict = "PASS" if version["meets_floor"] else "FAIL"
        lines.append(
            f"PROJECT {project['name']} | git {git_text} | horus {version['installed']}>={floor} [{verdict}]"
        )
        handoff = project["handoff"]
        lines.append(
            f"HANDOFF {project['name']} | focus={_compact(handoff['current_focus'])} | "
            f"next={_compact(handoff['next_action'])} | prompt={_compact(handoff['next_prompt'])} | "
            f"execution={_compact(handoff['execution_recommendation'])}"
        )
        for finding in project.get("hygiene", []):
            lines.append(
                f"HYGIENE {project['name']} [{finding['level'].upper()}] {_compact(finding['message'])}"
            )
    open_datums = digest.get("open_datums", [])
    datum_items = ", ".join(
        f"{datum['session_id'][:8]}:{_compact(datum.get('model'))}/{_compact(datum.get('exit'), 'pending')}"
        for datum in open_datums
    )
    lines.append(f"DATUMS open={len(open_datums)}" + (f" | {datum_items}" if datum_items else ""))
    sessions = digest.get("sessions", [])
    running = [session for session in sessions if session["status"] == "running"]
    stale = [session for session in sessions if session["status"] == "stale"]
    running_items = ", ".join(
        f"{session['session_id'][:8]}:{session['agent']}/{_compact(session.get('account'))}@{Path(session['project']).name}"
        for session in running
    )
    lines.append(f"SESSIONS running={len(running)}" + (f" | {running_items}" if running_items else ""))
    stale_by_project: dict[str, int] = defaultdict(int)
    for session in stale:
        stale_by_project[Path(session["project"]).name] += 1
    stale_items = ", ".join(f"{name}={count}" for name, count in sorted(stale_by_project.items()))
    lines.append(f"SESSIONS stale={len(stale)}" + (f" | {stale_items}" if stale_items else ""))
    for collision in digest.get("collisions", []):
        lines.append(
            f"COLLISION [WARN] project={Path(collision['project']).name} running={collision['count']} "
            f"sessions={','.join(collision['sessions'])}"
        )
    return "\n".join(lines) + "\n"


def render_json(digest: dict[str, Any]) -> str:
    return json.dumps(digest, indent=2, sort_keys=True) + "\n"
