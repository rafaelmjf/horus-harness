"""Cached usage snapshot — the shared substrate for the usage-limit survival kit.

A tiny, best-effort helper that returns the freshest usage percents for a target
agent+account — both the fast *5-hour window* and the slower *weekly window* (claude's
seven-day limit / codex's secondary window) — backed by a short-lived file cache under
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from horus import config

# Cache freshness: a snapshot younger than this is served without a live fetch.
CACHE_TTL = 60.0
# Live-fetch ceiling — the PreToolUse guard must stay fast, so cap the network wait.
FETCH_TIMEOUT = 5.0

# Threshold bands shared by the survival-kit callers (single source of truth).
PREFLIGHT_CLOSING = 50.0  # `horus run`: closing-window notice (surface percent + reset)
PREFLIGHT_WARN = 80.0     # `horus run`: warn, continue
PREFLIGHT_REFUSE = 95.0   # `horus run`: refuse (exit 2) unless --force
GUARD_ADVISORY = 90.0     # PreToolUse: inject an advisory (existing 90% semantics)
GUARD_EMERGENCY = 97.0    # PreToolUse: emergency state-save, once per window


class UsageSnapshot(NamedTuple):
    percent: float | None            # 5-hour window utilization percent (None = unknown)
    resets_at: str | None            # human-readable local reset time, or None
    # Second, slower window: claude's weekly (seven_day) limit, codex's secondary
    # window. Defaulted so every existing positional ``UsageSnapshot(pct, reset)``
    # caller keeps working; the ``PreToolUse`` guard reads only the 5h fields above.
    weekly_percent: float | None = None   # weekly/secondary window percent (None = unknown)
    weekly_resets_at: str | None = None   # weekly reset time, or None

    def has_expired_window(self, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return _window_expired(self.resets_at, now) or _window_expired(self.weekly_resets_at, now)

    def without_expired_windows(self, *, now: float | None = None) -> "UsageSnapshot":
        """Return a copy with any reset-past window marked unknown.

        The native apps report capacity by window. Once a window's reset time is in
        the past, its cached percent is no longer evidence of current capacity; the
        two windows expire independently.
        """
        now = time.time() if now is None else now
        percent = self.percent
        resets_at = self.resets_at
        weekly_percent = self.weekly_percent
        weekly_resets_at = self.weekly_resets_at
        if _window_expired(resets_at, now):
            percent = None
            resets_at = None
        if _window_expired(weekly_resets_at, now):
            weekly_percent = None
            weekly_resets_at = None
        return UsageSnapshot(percent, resets_at, weekly_percent, weekly_resets_at)

    def worst(self) -> tuple[float | None, str | None, str]:
        """The MORE-CONSTRAINING window as ``(percent, reset, label)``.

        A higher utilization percent is closer to that window's own limit, so it is
        the more constraining of (5h, weekly). Windows with no reading are ignored;
        ``(None, None, "5h")`` when neither window has a percent.
        """
        candidates = [
            c for c in (
                (self.percent, self.resets_at, "5h"),
                (self.weekly_percent, self.weekly_resets_at, "weekly"),
            ) if c[0] is not None
        ]
        if not candidates:
            return (None, None, "5h")
        return max(candidates, key=lambda c: c[0])


# Where a reading came from. Recorded alongside it so a read-out can say which
# surface answered instead of asserting one: a number pushed by the statusline and
# a number polled from the experimental endpoint are not equally authoritative,
# and neither is a cached one that is an hour old.
SOURCE_STATUSLINE = "statusline"   # pushed by Claude Code (official, unmetered)
SOURCE_OAUTH = "oauth"             # polled from the experimental /usage endpoint
SOURCE_ROLLOUT = "rollout"         # read from Codex's local rollout JSONL
SOURCE_UNKNOWN = "unknown"

_SOURCE_LABELS = {
    SOURCE_STATUSLINE: "recorded from Claude Code's statusline",
    SOURCE_OAUTH: "live OAuth /usage read",
    SOURCE_ROLLOUT: "local Codex rollout telemetry",
    SOURCE_UNKNOWN: "unknown source",
}


def source_label(source: str) -> str:
    return _SOURCE_LABELS.get(source, _SOURCE_LABELS[SOURCE_UNKNOWN])


class _Cached(NamedTuple):
    """A fresh cache entry. ``snapshot`` is ``None`` for a cached negative result
    (distinguished from a cache miss, which is a plain ``None`` return)."""

    snapshot: UsageSnapshot | None
    source: str = SOURCE_UNKNOWN
    ts: float | None = None

    def age_seconds(self, *, now: float | None = None) -> float | None:
        if self.ts is None:
            return None
        return max(0.0, (time.time() if now is None else now) - self.ts)


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
    week_pct = report.seven_day_percent
    week_reset = claude_usage._fmt_reset(report.seven_day_resets_at) if week_pct is not None else None
    return UsageSnapshot(
        report.five_hour_percent,
        claude_usage._fmt_reset(report.five_hour_resets_at),
        week_pct,
        week_reset,
    )


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
    # Route each lane by the length Codex declared for it, not by its slot: this
    # snapshot's `percent` MEANS the fast window, so putting a weekly reading
    # there makes every consumer say "5h" about a window that resets in six days
    # (observed 2026-07-17, while Codex had the 5-hour limit removed).
    fast, slow = report.windows()
    return UsageSnapshot(
        fast.percent if fast else None,
        codex_usage._fmt_reset(fast.resets_at) if fast else None,
        slow.percent if slow else None,
        codex_usage._fmt_reset(slow.resets_at) if slow else None,
    )


def _fmt_epoch(ts: object) -> str | None:
    """Local ``%Y-%m-%d %H:%M`` for a unix-epoch-seconds reset, which is the shape
    the statusline reports (the OAuth endpoint uses ISO strings instead)."""
    if not isinstance(ts, int | float) or isinstance(ts, bool):
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return None


def _statusline_window(block: object) -> tuple[float | None, str | None]:
    if not isinstance(block, dict):
        return None, None
    pct = block.get("used_percentage")
    percent = float(pct) if isinstance(pct, int | float) and not isinstance(pct, bool) else None
    return percent, _fmt_epoch(block.get("resets_at"))


def snapshot_from_claude_statusline(payload: object) -> UsageSnapshot | None:
    """A snapshot from the JSON Claude Code passes to a ``statusLine`` command.

    This is the OFFICIAL, documented usage surface: Claude Code *pushes*
    ``rate_limits`` into the statusline payload on every render, so reading it
    needs no credentials, no network call, and cannot be rate-limited. The OAuth
    ``/usage`` endpoint this module also reads is, by contrast, an experimental
    surface that answers 429 under any real polling — which is why a recorded
    statusline reading is preferred whenever one is fresh.

    ``rate_limits`` is absent on non-Pro/Max plans and until a session's first API
    response, so ``None`` here is an ordinary outcome, never an error.
    """
    if not isinstance(payload, dict):
        return None
    limits = payload.get("rate_limits")
    if not isinstance(limits, dict):
        return None
    five_pct, five_reset = _statusline_window(limits.get("five_hour"))
    week_pct, week_reset = _statusline_window(limits.get("seven_day"))
    if five_pct is None and week_pct is None:
        return None
    return UsageSnapshot(five_pct, five_reset, week_pct, week_reset)


def record_snapshot(
    agent: str, account: str | None, snapshot: UsageSnapshot, *, now: float | None = None
) -> Path:
    """Persist a pushed reading into the shared cache every consumer already reads.

    Deliberately the same file and format as a live read, so recording costs no
    consumer any change: the preflight, the PreToolUse guard, the envelope's usage
    floor and the dashboard all just find a fresh entry and never reach for the
    rate-limited endpoint.
    """
    path = _cache_path(agent, account)
    _write_cache(
        path, snapshot, now=time.time() if now is None else now, source=SOURCE_STATUSLINE
    )
    return path


def _live_source(agent: str) -> str:
    return SOURCE_OAUTH if agent == "claude" else SOURCE_ROLLOUT


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


def refresh_usage(
    agent: str,
    account: str | None = None,
    *,
    timeout: float = FETCH_TIMEOUT,
    now: float | None = None,
) -> UsageSnapshot | None:
    """Best-effort live refresh used when a cached window is known expired.

    A failed refresh does not overwrite a previous positive cache entry; callers can
    still use any unexpired window from the cached snapshot.
    """
    now = time.time() if now is None else now
    snapshot = _read_live(agent, account, timeout=timeout)
    if snapshot is not None:
        _write_cache(_cache_path(agent, account), snapshot, now=now, source=_live_source(agent))
    return snapshot


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #

def _load_cache(path: Path, *, ttl: float | None, now: float) -> _Cached | None:
    """Return a cache entry, or ``None`` for a miss/stale/corrupt file.

    ``ttl=None`` skips the freshness gate entirely — whatever is on disk is
    returned regardless of age (used by ``read_cache_only``, which wants "what's
    there" rather than "is it fresh enough to skip a live fetch").
    """
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
    if ttl is not None and (now - ts >= ttl or now < ts):
        return None
    source = data.get("source")
    source = source if isinstance(source, str) and source else SOURCE_UNKNOWN
    if not data.get("ok"):
        return _Cached(None, source, ts)
    pct = data.get("percent")
    percent = float(pct) if isinstance(pct, int | float) else None
    resets = data.get("resets_at")
    # Weekly fields absent in caches written before multi-window support -> None.
    wpct = data.get("weekly_percent")
    weekly_percent = float(wpct) if isinstance(wpct, int | float) else None
    wresets = data.get("weekly_resets_at")
    return _Cached(
        UsageSnapshot(
            percent,
            resets if isinstance(resets, str) else None,
            weekly_percent,
            wresets if isinstance(wresets, str) else None,
        ),
        source,
        ts,
    )


def _reset_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    if not text or text == "unknown reset":
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    return dt.timestamp()


def reset_epoch(value: str | None) -> float | None:
    """Public: parse a human-readable reset string into a POSIX timestamp, or
    ``None`` when it is absent/unparseable. Callers that need to schedule off a
    recorded window reset (e.g. the keep-warm loop) reuse the one parser here
    rather than reinventing the format handling."""
    return _reset_timestamp(value)


def _window_expired(reset: str | None, now: float) -> bool:
    ts = _reset_timestamp(reset)
    return ts is not None and ts <= now


def _write_cache(
    path: Path, snapshot: UsageSnapshot | None, *, now: float, source: str = SOURCE_UNKNOWN
) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot is None:
            payload: dict[str, object] = {"ts": now, "ok": False, "source": source}
        else:
            payload = {
                "ts": now,
                "ok": True,
                "source": source,
                "percent": snapshot.percent,
                "resets_at": snapshot.resets_at,
                "weekly_percent": snapshot.weekly_percent,
                "weekly_resets_at": snapshot.weekly_resets_at,
            }
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
    _write_cache(path, snapshot, now=now, source=_live_source(agent))
    return snapshot


def read_cache_entry(agent: str, account: str | None = None) -> _Cached | None:
    """Whatever is cached for ``agent``+``account`` — at any age — with the source
    and timestamp attached, or ``None`` on a miss.

    For read-outs that must say where a number came from and how old it is rather
    than presenting every reading as equally live.
    """
    return _load_cache(_cache_path(agent, account), ttl=None, now=time.time())


def read_cache_only(agent: str, account: str | None = None) -> UsageSnapshot | None:
    """Whatever ``horus run`` preflight / the PreToolUse guard last wrote to disk
    for ``agent``+``account`` — however old, and with no live-fetch fallback.

    Distinct from ``cached_usage()``, which falls back to a live read on a stale
    or missing cache (built for the hot path that needs a fresh signal). This is
    for callers that must never touch the network — e.g. the dashboard's manual
    "refresh (cached)" control — and rely on the caller to apply
    ``UsageSnapshot.without_expired_windows``/reset-display logic for staleness
    that matters (a reset boundary already turns an old percent into "unknown"
    rather than a misleading stale figure).
    """
    cached = _load_cache(_cache_path(agent, account), ttl=None, now=time.time())
    return cached.snapshot if cached is not None else None


# --------------------------------------------------------------------------- #
# All-accounts roll-up — the fleet capacity glance the steering channel needs.
#
# The single-target reads above answer "this run's window"; this answers "every
# account's window" for `horus usage all` (and the phone's `usage` verb), so the
# owner can see, from anywhere, which account still has headroom.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AccountUsage:
    agent: str                 # "claude" | "codex"
    account: str               # alias, or "default"
    snapshot: UsageSnapshot | None


def all_account_targets() -> list[tuple[str, str | None]]:
    """Every ``(agent, account_alias)`` to read: each configured alias per agent,
    or that agent's default login (``None``) when it has no configured aliases."""
    targets: list[tuple[str, str | None]] = []
    for agent, loader in (
        ("claude", config.load_account_config_dirs),
        ("codex", config.load_account_codex_homes),
    ):
        aliases = sorted(loader())
        if aliases:
            targets += [(agent, alias) for alias in aliases]
        else:
            targets.append((agent, None))
    return targets


def all_accounts_usage(
    *,
    read_only: bool = False,
    ttl: float = CACHE_TTL,
    timeout: float = FETCH_TIMEOUT,
    now: float | None = None,
) -> list[AccountUsage]:
    """Freshest usage for every configured account (both windows).

    ``read_only=True`` serves only what's on disk (never touches the network);
    the default does one live read per target through :func:`cached_usage`. Each
    snapshot has reset-past windows blanked so a stale percent never misleads.
    Best-effort, like every read here — an unreadable target renders as ``None``.
    """
    now = time.time() if now is None else now
    rows: list[AccountUsage] = []
    for agent, account in all_account_targets():
        if read_only:
            snap = read_cache_only(agent, account)
        else:
            snap = cached_usage(agent, account, ttl=ttl, timeout=timeout, now=now)
        if snap is not None:
            snap = snap.without_expired_windows(now=now)
        rows.append(AccountUsage(agent=agent, account=account or "default", snapshot=snap))
    return rows


def _usage_cell(percent: float | None, reset: str | None) -> str:
    if percent is None:
        return "—"
    return f"{percent:.0f}%" + (f" (resets {reset})" if reset else "")


def render_all_accounts(rows: list[AccountUsage]) -> str:
    """Compact per-account capacity table for a CLI glance / a phone screen."""
    lines = ["Usage — all accounts (5h · weekly):"]
    if not rows:
        return lines[0] + "\n  (no accounts configured)"
    width = max(len(f"{r.agent}/{r.account}") for r in rows)
    for r in rows:
        label = f"{r.agent}/{r.account}".ljust(width)
        if r.snapshot is None:
            lines.append(f"  {label}  unknown")
            continue
        s = r.snapshot
        lines.append(
            f"  {label}  5h {_usage_cell(s.percent, s.resets_at)}"
            f" · weekly {_usage_cell(s.weekly_percent, s.weekly_resets_at)}"
        )
    return "\n".join(lines)
