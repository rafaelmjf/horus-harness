"""Self-update signal: is a newer horus-harness on PyPI, and one-click upgrade.

The dashboard's artifact-staleness badge covers *project vs installed CLI*; this
module covers *installed CLI vs latest release* plus *running server vs installed
CLI* (`build_state` — a long-running dashboard whose on-disk install has moved
past its loaded build must stop writing artifacts, because in-process writes
stamp the OLD generation while self-reporting fresh). The check is passive (a cached
PyPI JSON read that never blocks a page or fails the dashboard offline) and the
upgrade is explicit — a button running ``uv tool upgrade horus-harness``, never
automatic. A running server keeps serving its old in-memory build, so after an
upgrade Horus must be restarted from outside to load the new version (the same
no-hot-reload rule as templates.HOSTED_RESTART_INSTRUCTION).
"""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from horus import __version__, config

PYPI_URL = "https://pypi.org/pypi/horus-harness/json"
CACHE_TTL_SECONDS = 6 * 60 * 60  # a release cadence signal, not a live feed


def _cache_path() -> Path:
    return config.config_dir() / "update-check.json"


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(candidate: str, current: str) -> bool:
    return _version_tuple(candidate) > _version_tuple(current)


def installed_disk_version() -> str | None:
    """The horus-harness version currently installed on disk, or None.

    Re-read from dist metadata on every call (importlib.metadata invalidates its
    path cache on directory mtime), so after `uv tool upgrade` rewrites the env
    this reflects the NEW install while `__version__` stays the loaded build.
    """
    try:
        return importlib.metadata.version("horus-harness")
    except Exception:
        return None


def build_state() -> dict[str, object]:
    """Running (in-memory) vs installed (on-disk) build: {running, disk, stale}.

    `stale` only when the disk is NEWER — an upgrade landed under a running
    server. A dev checkout whose source version is ahead of its install
    metadata is not stale, and a missing dist (bare checkout) never warns.
    """
    disk = installed_disk_version()
    return {
        "running": __version__,
        "disk": disk,
        "stale": bool(disk and is_newer(disk, __version__)),
    }


def fetch_latest_version(timeout: float = 3.0) -> str | None:
    """The latest release on PyPI, or None when offline/unparseable."""
    try:
        with urlopen(PYPI_URL, timeout=timeout) as response:
            payload = json.load(response)
        version = payload.get("info", {}).get("version")
        return version if isinstance(version, str) and version else None
    except (OSError, TimeoutError, URLError, ValueError):
        return None


def check_update(*, ttl: float = CACHE_TTL_SECONDS, now: float | None = None) -> dict[str, object]:
    """Cached update check: {installed, latest, update_available}.

    Reads the last PyPI answer from ``~/.horus/update-check.json`` while it is
    fresher than ``ttl``; otherwise fetches and rewrites the cache. Errs toward
    "no update" — a failed fetch never surfaces as a warning.
    """
    current_time = time.time() if now is None else now
    cache = _cache_path()
    latest: str | None = None
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if current_time - float(cached.get("checked_at", 0)) < ttl:
            value = cached.get("latest")
            latest = value if isinstance(value, str) and value else None
    except (OSError, ValueError):
        cached = None
    if latest is None:
        latest = fetch_latest_version()
        if latest is not None:
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(
                    json.dumps({"latest": latest, "checked_at": current_time}),
                    encoding="utf-8",
                )
            except OSError:
                pass
    return {
        "installed": __version__,
        "latest": latest,
        "update_available": bool(latest and is_newer(latest, __version__)),
    }


def run_upgrade(timeout: float = 120.0) -> tuple[bool, str]:
    """Run ``uv tool upgrade horus-harness``. Returns (ok, detail).

    The new code lands on disk but the running process keeps its old build; the
    caller must tell the user to restart Horus to load it.
    """
    try:
        result = subprocess.run(
            ["uv", "tool", "upgrade", "horus-harness"],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return False, "uv not found — install horus-harness updates manually"
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "upgrade failed").strip()
        return False, detail.splitlines()[-1] if detail else "upgrade failed"
    return True, (result.stderr or result.stdout or "upgraded").strip().splitlines()[-1]
