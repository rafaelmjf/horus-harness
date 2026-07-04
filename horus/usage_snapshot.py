"""Cached usage snapshot — the shared substrate for the usage-limit survival kit.

A tiny, best-effort helper that returns the freshest *5-hour window* usage percent
for a target agent+account, backed by a short-lived file cache under
``~/.horus/cache/``. Two callers depend on it:

- ``horus run`` preflight (warn/refuse before launching into a closing window);
- the ``PreToolUse`` usage guard (so a single long turn can't sail past the
  advisory threshold, and so an emergency state-save can fire near the cutoff).

Contract, always: **never raise, never block.** A missing credential, an offline
machine, a slow endpoint, or schema drift all resolve to ``None`` (or a snapshot
whose ``percent`` is ``None``) — the caller then proceeds silently. The cache makes
the ``PreToolUse`` hot path a file read; a negative result is cached too, so a
machine with no usable usage signal does not pay the fetch timeout on every tool
call.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import NamedTuple

from horus import config

# Cache freshness: a snapshot younger than this is served without a live fetch.
CACHE_TTL = 60.0
# Live-fetch ceiling — the PreToolUse guard must stay fast, so cap the network wait.
FETCH_TIMEOUT = 5.0

# Threshold bands shared by the survival-kit callers (single source of truth).
PREFLIGHT_WARN = 80.0     # `horus run`: warn, continue
PREFLIGHT_REFUSE = 95.0   # `horus run`: refuse (exit 2) unless --force
GUARD_ADVISORY = 90.0     # PreToolUse: inject an advisory (existing 90% semantics)
GUARD_EMERGENCY = 97.0    # PreToolUse: emergency state-save, once per window


class UsageSnapshot(NamedTuple):
    percent: float | None   # 5-hour window utilization percent (None = unknown)
    resets_at: str | None   # human-readable local reset time, or None


class _Cached(NamedTuple):
    """A fresh cache entry. ``snapshot`` is ``None`` for a cached negative result
    (distinguished from a cache miss, which is a plain ``None`` return)."""

    snapshot: UsageSnapshot | None


def cache_dir() -> Path:
    return config.config_dir() / "cache"


def _cache_key(agent: str, account: str | None) -> str:
    raw = f"{agent}-{account or 'default'}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)[:80]


def _cache_path(agent: str, account: str | None) -> Path:
    return cache_dir() / f"usage-{_cache_key(agent, account)}.json"


# --------------------------------------------------------------------------- #
# Live reads (best-effort; any failure -> None)
# --------------------------------------------------------------------------- #

def _read_claude(account: str | None, *, timeout: float) -> UsageSnapshot | None:
    from horus import claude_usage

    cred_path: Path | None = None
    if account:
        cfg = config.load_account_config_dirs().get(account)
        if cfg:
            cred_path = Path(cfg) / ".credentials.json"
    report = claude_usage.latest_usage(cred_path=cred_path, timeout=timeout)
    if report is None:
        return None
    return UsageSnapshot(report.five_hour_percent, claude_usage._fmt_reset(report.five_hour_resets_at))


def _read_codex(account: str | None) -> UsageSnapshot | None:
    from horus import codex_usage

    home: Path | None = None
    if account:
        h = config.load_account_codex_homes().get(account)
        if h:
            home = Path(h)
    report = codex_usage.latest_account_usage(home=home)
    if report is None:
        return None
    return UsageSnapshot(report.primary_percent, codex_usage._fmt_reset(report.primary_resets_at))


def _read_live(agent: str, account: str | None, *, timeout: float) -> UsageSnapshot | None:
    """A single live usage read for ``agent``+``account``. Never raises."""
    try:
        if agent == "claude":
            return _read_claude(account, timeout=timeout)
        if agent == "codex":
            return _read_codex(account)
    except Exception:  # noqa: BLE001 (best-effort: any failure is "no signal")
        return None
    return None


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #

def _load_cache(path: Path, *, ttl: float, now: float) -> _Cached | None:
    """Return a fresh cache entry, or ``None`` for a miss/stale/corrupt file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    ts = data.get("ts")
    if not isinstance(ts, int | float):
        return None
    # Stale, or a clock that jumped backwards past the write — treat as a miss.
    if now - ts >= ttl or now < ts:
        return None
    if not data.get("ok"):
        return _Cached(None)
    pct = data.get("percent")
    percent = float(pct) if isinstance(pct, int | float) else None
    resets = data.get("resets_at")
    return _Cached(UsageSnapshot(percent, resets if isinstance(resets, str) else None))


def _write_cache(path: Path, snapshot: UsageSnapshot | None, *, now: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot is None:
            payload: dict[str, object] = {"ts": now, "ok": False}
        else:
            payload = {"ts": now, "ok": True, "percent": snapshot.percent, "resets_at": snapshot.resets_at}
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def cached_usage(
    agent: str,
    account: str | None = None,
    *,
    ttl: float = CACHE_TTL,
    timeout: float = FETCH_TIMEOUT,
    now: float | None = None,
) -> UsageSnapshot | None:
    """Freshest usage snapshot for ``agent``+``account`` (5-hour window).

    Serves a cache entry younger than ``ttl`` without any network I/O (the hot
    path for the PreToolUse guard); otherwise does one live read, caches it
    (including a negative result), and returns it. Returns ``None`` when no usable
    signal exists; callers treat both ``None`` and ``percent is None`` as "unknown,
    proceed silently".
    """
    now = time.time() if now is None else now
    path = _cache_path(agent, account)
    cached = _load_cache(path, ttl=ttl, now=now)
    if cached is not None:
        return cached.snapshot
    snapshot = _read_live(agent, account, timeout=timeout)
    _write_cache(path, snapshot, now=now)
    return snapshot
