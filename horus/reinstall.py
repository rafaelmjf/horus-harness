"""``horus reinstall --verify <marker>`` — the known-good reinstall sequence,
plus proof the fix actually landed.

Encodes two footguns from the 2026-07 release-hardening history:

- **The uv stale-wheel trap** — ``uv tool install --force --reinstall`` alone
  can silently keep serving a cached build of the SAME source path/version
  from uv's build cache (see ``scripts/deploy-hosted.sh``'s ``--refresh``
  note for the sibling PyPI-index version of this trap). ``uv cache clean
  <package>`` first, then the force-reinstall, closes it for a local source
  path the way ``--refresh`` closes it for a PyPI version bump.
- **deploy != reinstall** — landing bits on disk is not the same as a
  *running* process having loaded them (``selfupdate.build_state`` exists for
  exactly this gap on the hosted dashboard). This verb closes the FIRST half
  (get the fresh bits on disk, verifiably) and surfaces the second as a
  report line — a still-active ``horus-dashboard.service`` needs a restart —
  never an automatic action.

Verification reads the INSTALLED surface (the freshly-written files under the
tool's own env on disk), never this process's already-imported modules — the
same on-disk-vs-in-memory distinction, because ``horus reinstall`` may itself
be replacing the very build currently running it.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

_NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}

DEFAULT_PACKAGE = "horus-harness"
DEFAULT_PYTHON = "3.12"
# Generous: this is a foreground, user-waited-on one-shot, not a best-effort
# background probe — `uv cache clean` can block for minutes behind another
# uv process's lock on the same machine (observed live, 2026-07-14), and a
# from-source `uv tool install` also has real dependency-resolution work to do.
DEFAULT_TIMEOUT = 300.0

# Systemd unit deploy-hosted.sh restarts after an upgrade — the one concrete
# "a running process needs a restart" case this repo actually has today.
_KNOWN_SERVICES = ("horus-dashboard.service",)


class ReinstallError(Exception):
    """The reinstall sequence itself (cache clean or tool install) failed."""


@dataclass(frozen=True)
class ReinstallResult:
    ok: bool
    marker: str
    marker_found: bool
    detail: str
    service_notes: list[str] = field(default_factory=list)


def _run(cmd: list[str], *, timeout: float) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReinstallError(f"command failed: {' '.join(cmd)}: {exc}") from exc


def _uv_tool_dir(*, timeout: float) -> Path | None:
    r = _run(["uv", "tool", "dir"], timeout=timeout)
    if r.returncode != 0:
        return None
    text = r.stdout.strip()
    return Path(text) if text else None


def _site_packages_dirs(package: str, *, timeout: float) -> list[Path]:
    tool_dir = _uv_tool_dir(timeout=timeout)
    if tool_dir is None:
        return []
    base = tool_dir / package
    # `lib/python*/site-packages` on POSIX, `Lib/site-packages` on Windows.
    return sorted(base.glob("lib/python*/site-packages")) + sorted(base.glob("Lib/site-packages"))


def _grep_installed_surface(package: str, marker: str, *, timeout: float) -> tuple[bool, str]:
    dirs = _site_packages_dirs(package, timeout=timeout)
    if not dirs:
        return False, f"could not locate the installed tool env for {package!r} (`uv tool dir` unavailable)"
    for site_dir in dirs:
        for path in sorted(site_dir.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if marker in text:
                return True, f"found in {path}"
    return False, f"marker {marker!r} not found under {dirs[0]}"


def _service_notes() -> list[str]:
    """Best-effort: any known Horus systemd service still ACTIVE, which keeps
    serving its old in-memory build until restarted. Silently empty on a
    machine without systemd (Mac/Windows dev boxes) — this is a nudge, not a
    gate."""
    notes: list[str] = []
    for service in _KNOWN_SERVICES:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5.0, **_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0 and r.stdout.strip() == "active":
            notes.append(f"{service} is active — restart it to load this reinstall (systemctl restart {service})")
    return notes


def reinstall(
    source: str,
    marker: str,
    *,
    package: str = DEFAULT_PACKAGE,
    python: str = DEFAULT_PYTHON,
    timeout: float = DEFAULT_TIMEOUT,
) -> ReinstallResult:
    """``uv cache clean <package>`` then ``uv tool install --force --reinstall
    --python <python> <source>``, then grep the installed surface for
    ``marker``. Raises :class:`ReinstallError` only when the install sequence
    itself fails; a clean install that simply lacks the marker is a normal,
    non-exceptional result (``ok=True, marker_found=False``) — the caller
    decides what to do with an absent marker."""
    clean = _run(["uv", "cache", "clean", package], timeout=timeout)
    if clean.returncode != 0:
        raise ReinstallError(f"uv cache clean failed: {(clean.stderr or clean.stdout).strip()}")

    install = _run(
        ["uv", "tool", "install", "--force", "--reinstall", "--python", python, source],
        timeout=timeout,
    )
    if install.returncode != 0:
        raise ReinstallError(f"uv tool install failed: {(install.stderr or install.stdout).strip()}")

    found, detail = _grep_installed_surface(package, marker, timeout=timeout)
    return ReinstallResult(
        ok=True,
        marker=marker,
        marker_found=found,
        detail=detail,
        service_notes=_service_notes(),
    )
