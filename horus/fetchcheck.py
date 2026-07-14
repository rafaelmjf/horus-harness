"""Session-start fetch-first signal.

The fetch-first rule lived only in instruction text; nothing deterministic fired
at session start, and a 21-release-stale clone nearly produced a wrong bug report
(field findings 2026-07-08). This is the enforcement analogue of ``close``'s
fetch-first guard at the session's other end: fetch (TTL-cached, hard-timeout),
then read the on-disk refs via :mod:`horus.gitstate` and produce a warning line
when the local branch is behind origin. Advisory only — hooks advise and ask,
never override; offline, non-repo, or no-upstream is a silent no-op.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from horus import config, gitstate

# One fetch per repo per window; sessions restart in bursts (resume/compact fire
# SessionStart too) and each miss costs a network round-trip at session start.
TTL_SECONDS = 600
# Hard cap on the fetch itself — a hung remote must never stall a session start.
FETCH_TIMEOUT = 10.0

_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}


def _cache_path() -> Path:
    return config.config_dir() / "cache" / "fetch-check.json"


def _load_cache() -> dict[str, Any]:
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(cache: dict[str, Any]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass  # cache is an optimization; never let it break the signal


def _fetch(root: Path, *, timeout: float = FETCH_TIMEOUT) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "fetch", "--all", "--prune", "--quiet"],
            capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def fetch_and_state(root: Path, *, ttl: float = TTL_SECONDS) -> dict[str, Any] | None:
    """Fetch (at most once per ``ttl`` seconds per repo), then return the git state.

    The cache records the *attempt*, success or not, so an offline machine pays the
    fetch timeout once per window instead of on every session start. Returns None
    when ``root`` is not a work tree.
    """
    state = gitstate.git_state(root)
    if state is None:
        return None
    state = dict(state)
    if state["remote_url"] is None:
        state["fetch_status"] = "not-needed"
        return state  # no remote — nothing to be behind of

    key = str(root.resolve())
    cache = _load_cache()
    entry = cache.get(key)
    last = entry.get("at", 0) if isinstance(entry, dict) else 0
    now = time.time()
    if not isinstance(last, (int, float)) or now - last >= ttl:
        ok = _fetch(root)
        cache[key] = {"at": now, "ok": ok}
        _save_cache(cache)
        state = gitstate.git_state(root)  # re-read refs the fetch just moved
        if state is None:
            return None
        state = dict(state)
        state["fetch_status"] = "ok" if ok else "failed"
    else:
        state["fetch_status"] = "cached-ok" if entry.get("ok") else "cached-failed"
    return state


def warning_line(state: dict[str, Any] | None) -> str:
    """The behind-origin warning for a session start, or "" when there is nothing
    to say (fresh, no upstream, not a repo)."""
    if not state or not state.get("behind"):
        return ""
    behind = state["behind"]
    branch = state.get("branch") or "?"
    line = (
        f"Horus fetch-check: local branch '{branch}' is {behind} commit(s) behind "
        "its upstream. Sync before trusting local refs or continuity prose "
        "(git pull / git rebase), per the fetch-first rule."
    )
    if state.get("dirty"):
        line += " Note: the working tree also has uncommitted changes."
    return line
