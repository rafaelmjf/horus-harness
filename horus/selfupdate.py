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
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from horus import __version__, config
from horus.versioning import version_tuple as _version_tuple

PYPI_URL = "https://pypi.org/pypi/horus-harness/json"
CACHE_TTL_SECONDS = 6 * 60 * 60  # a release cadence signal, not a live feed


def _cache_path() -> Path:
    return config.config_dir() / "update-check.json"


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


def fetch_release_info(timeout: float = 3.0) -> dict[str, str | None] | None:
    """The latest release on PyPI as {version, requires_python}, or None offline.

    `requires_python` matters because raising the floor strands tool envs
    created under an older interpreter: uv resolves the newest floor-compatible
    (= OLD) release and reports success. run_upgrade needs the floor to detect
    that trap before it happens.
    """
    try:
        with urlopen(PYPI_URL, timeout=timeout) as response:
            payload = json.load(response)
        info = payload.get("info", {})
        version = info.get("version")
        if not (isinstance(version, str) and version):
            return None
        requires = info.get("requires_python")
        return {
            "version": version,
            "requires_python": requires if isinstance(requires, str) and requires else None,
        }
    except (OSError, TimeoutError, URLError, ValueError):
        return None


def _python_floor(requires_python: str | None) -> tuple[int, int] | None:
    """The minimum (major, minor) from a requires-python spec like '>=3.12,<4'."""
    if not requires_python:
        return None
    for clause in requires_python.split(","):
        clause = clause.strip()
        if clause.startswith(">="):
            parts = clause[2:].strip().split(".")
            try:
                return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                return None
    return None


def check_update(*, ttl: float = CACHE_TTL_SECONDS, now: float | None = None) -> dict[str, object]:
    """Cached update check: {installed, latest, requires_python, update_available}.

    Reads the last PyPI answer from ``~/.horus/update-check.json`` while it is
    fresher than ``ttl``; otherwise fetches and rewrites the cache. Errs toward
    "no update" — a failed fetch never surfaces as a warning.
    """
    current_time = time.time() if now is None else now
    cache = _cache_path()
    latest: str | None = None
    requires: str | None = None
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if current_time - float(cached.get("checked_at", 0)) < ttl:
            value = cached.get("latest")
            latest = value if isinstance(value, str) and value else None
            spec = cached.get("requires_python")
            requires = spec if isinstance(spec, str) and spec else None
    except (OSError, ValueError):
        cached = None
    if latest is None:
        info = fetch_release_info()
        if info is not None:
            latest = info.get("version")  # type: ignore[assignment]
            requires = info.get("requires_python")  # type: ignore[assignment]
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(
                    json.dumps(
                        {
                            "latest": latest,
                            "requires_python": requires,
                            "checked_at": current_time,
                        }
                    ),
                    encoding="utf-8",
                )
            except OSError:
                pass
    return {
        "installed": __version__,
        "latest": latest,
        "requires_python": requires,
        "update_available": bool(latest and is_newer(latest, __version__)),
    }


def run_upgrade(timeout: float = 120.0) -> tuple[bool, str]:
    """Upgrade the horus-harness tool env. Returns (ok, detail).

    Three traps from the 2026-07-02 two-machine test are handled here:
    ``--reinstall`` (implies ``--refresh``, which ``uv tool upgrade`` does not
    accept directly as of uv 0.11 — a stale index cache silently no-ops the
    upgrade otherwise); an
    interpreter-pinned env (env python below the latest release's
    requires-python floor → a plain upgrade resolves the newest OLD release
    and reports success) is migrated via ``uv tool install --force --python``;
    and the result is verified against the on-disk dist so a silent
    stay-at-old-version never reports as success.

    The new code lands on disk but the running process keeps its old build; the
    caller must tell the user to restart Horus to load it.
    """
    status = check_update()
    latest = status.get("latest")
    floor = _python_floor(status.get("requires_python"))  # type: ignore[arg-type]
    floor_str = f"{floor[0]}.{floor[1]}" if floor else "3.12"
    if floor and sys.version_info[:2] < floor:
        # Migrate the pinned env: recreate it under a floor-compatible python.
        cmd = ["uv", "tool", "install", "--force", "--python", floor_str, "horus-harness"]
    else:
        cmd = ["uv", "tool", "upgrade", "--reinstall", "horus-harness"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return False, "uv not found — install horus-harness updates manually"
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "upgrade failed").strip()
        return False, detail.splitlines()[-1] if detail else "upgrade failed"
    disk = installed_disk_version()
    if isinstance(latest, str) and disk and is_newer(latest, disk):
        return False, (
            f"still v{disk} after the upgrade — the tool env's interpreter is pinned "
            f"below the latest release's floor; run: "
            f"uv tool install --force --python {floor_str} horus-harness"
        )
    return True, (result.stderr or result.stdout or "upgraded").strip().splitlines()[-1]
