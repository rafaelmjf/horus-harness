"""Read-only Claude Code subscription usage signals.

Claude Code does not expose subscription rate-limit usage to hooks or transcripts,
but its `/usage` panel reads it from the authenticated endpoint
``GET https://api.anthropic.com/api/oauth/usage``. Horus queries the same endpoint
with the OAuth token Claude Code already stores in ``~/.claude/.credentials.json``,
so it can use the 5-hour / weekly limits as a closure signal — the Claude-side peer
of the Codex rollout telemetry in ``codex_usage``.

Best-effort and read-only: a missing/expired token, an offline machine, or schema
drift simply produces no usable report (no exception escapes).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from horus.continuity import Finding

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"
# Beta header Claude Code sends for OAuth-scoped endpoints (found in the CLI binary).
_OAUTH_BETA = "oauth-2025-04-20"
# Public OAuth client id Claude Code authenticates with.
_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
# Cloudflare 1010-blocks requests with no User-Agent; mirror the CLI's shape.
_USER_AGENT = "claude-cli (external, cli)"


class UsageReport(NamedTuple):
    five_hour_percent: float | None
    five_hour_resets_at: str | None
    seven_day_percent: float | None
    seven_day_resets_at: str | None


def _claude_home() -> Path | None:
    """The relocated Claude config dir when ``CLAUDE_CONFIG_DIR`` is set (per-account
    isolation), else None (the ambient default locations apply)."""
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env) if env else None


def credentials_path() -> Path:
    home = _claude_home()
    return (home / ".credentials.json") if home else (Path.home() / ".claude" / ".credentials.json")


def config_path() -> Path:
    home = _claude_home()
    return (home / ".claude.json") if home else (Path.home() / ".claude.json")


def current_account(path: Path | None = None) -> str | None:
    """Email of the Claude account currently logged in, or None.

    Read from ``~/.claude.json`` (``oauthAccount.emailAddress``) — a read-only,
    non-secret anchor for *which* account a session ran under. Useful for tagging
    local recovery notes and, later, for scoping usage state per account.
    """
    cfg = path or config_path()
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    oauth = data.get("oauthAccount")
    if isinstance(oauth, dict):
        ident = oauth.get("emailAddress") or oauth.get("accountUuid")
        if isinstance(ident, str) and ident:
            return ident
    return None


# --------------------------------------------------------------------------- #
# Account attribution — whose number is this?
# --------------------------------------------------------------------------- #
# A token that authenticates is not evidence that it belongs to the account the
# session runs under. Under the desktop app the two routinely differ: switching
# accounts in the app never touches the CLI's ``.credentials.json``, so the endpoint
# answers 200 for the *CLI's* account and we would report it as the session's. Every
# signal says success, which is exactly what makes it dangerous — a session was told
# it was at 95% while actually at 15%, and spent four turns on closure pressure that
# did not apply. A wrong number is worse than no number: no number cannot make
# someone act.


class Identity(NamedTuple):
    """Who an account is: the user account, and the org it bills against.

    Both are carried because neither alone is sufficient. ``account_uuid`` is the
    precise identity — a ``claude_team`` org holds several member accounts, each with
    its own rate-limit pool, so matching on org alone would call two colleagues the
    same account. ``org_uuid`` is the fallback for state that records only the org.
    """

    account_uuid: str | None
    org_uuid: str | None

    def __bool__(self) -> bool:
        return bool(self.account_uuid or self.org_uuid)

    def matches(self, other: Identity) -> bool:
        """True only on positive evidence of the same account — never on two unknowns."""
        if self.account_uuid and other.account_uuid:
            return self.account_uuid == other.account_uuid
        if self.org_uuid and other.org_uuid:
            return self.org_uuid == other.org_uuid
        return False


class Attribution(NamedTuple):
    """Whether a reading may be reported as *this session's* usage."""

    ok: bool
    session: Identity
    reading: Identity
    reason: str | None


def in_claude_session() -> bool:
    """True when this process runs inside a Claude Code session (``CLAUDECODE=1``).

    Outside one — a human running ``horus usage check`` in a plain terminal — there is
    no session to attribute a reading to, so the ambient login is both the subject and
    the correct answer, and no attribution question arises.
    """
    return os.environ.get("CLAUDECODE", "").strip() == "1"


def running_surface() -> str:
    """Claude Code surface this session runs on: ``desktop``, ``cli`` or ``unknown``.

    ``CLAUDE_CODE_ENTRYPOINT`` is set by Claude Code itself and inherited by hook
    subprocesses, so it is readable from the hot path that actually misreported.
    """
    entry = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").strip().lower()
    if not entry:
        return "unknown"
    return "desktop" if "desktop" in entry else "cli"


def desktop_support_dir() -> Path | None:
    """The Claude *desktop app*'s per-user state directory, or None when absent.

    ``claude_usage`` otherwise has no notion that the desktop app exists, which is how
    a desktop session's account became invisible to it.
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        root = Path(base) / "Claude" if base else None
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "Claude"
    else:
        root = Path.home() / ".config" / "Claude"
    return root if root is not None and root.is_dir() else None


def identity_for_config(path: Path | None = None) -> Identity:
    """Identity recorded beside a Claude login — whose usage that login's token reports.

    Read from the ``.claude.json`` paired with the credentials actually used, so the
    answer describes *those* credentials and not some other config home's.
    """
    cfg = path or config_path()
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Identity(None, None)
    oauth = data.get("oauthAccount")
    if not isinstance(oauth, dict):
        return Identity(None, None)

    def _str(key: str) -> str | None:
        value = oauth.get(key)
        return value if isinstance(value, str) and value else None

    return Identity(_str("accountUuid"), _str("organizationUuid"))


def org_for_config(path: Path | None = None) -> str | None:
    """``organizationUuid`` recorded beside a Claude login, or None."""
    return identity_for_config(path).org_uuid


def session_identity(*, host_session_id: str | None = None, support_dir: Path | None = None) -> Identity:
    """Identity of the account THIS session runs under; empty when undeterminable.

    Under the desktop app this is *measured*, not inferred: the app files every session
    as ``claude-code-sessions/<accountUuid>/<organizationUuid>/<hostSessionId>.json``
    and the session knows its own id from ``CLAUDE_CODE_HOST_SESSION_ID``, so the two
    directories holding that file name the account and its org. Under the CLI the
    session and the login are the same thing by construction, so the login's identity
    is the session's.
    """
    if running_surface() == "cli":
        return identity_for_config()
    sid = host_session_id or os.environ.get("CLAUDE_CODE_HOST_SESSION_ID")
    root = support_dir if support_dir is not None else desktop_support_dir()
    if not sid or root is None:
        return Identity(None, None)
    try:
        for account_dir in (root / "claude-code-sessions").iterdir():
            if not account_dir.is_dir():
                continue
            for org_dir in account_dir.iterdir():
                if org_dir.is_dir() and (org_dir / f"{sid}.json").exists():
                    return Identity(account_dir.name, org_dir.name)
    except OSError:
        return Identity(None, None)
    return Identity(None, None)


def session_org(*, host_session_id: str | None = None, support_dir: Path | None = None) -> str | None:
    """Org UUID of the account THIS session runs under, or None when undeterminable."""
    return session_identity(host_session_id=host_session_id, support_dir=support_dir).org_uuid


def check_attribution(cred_path: Path | None = None) -> Attribution:
    """Whether a reading taken with ``cred_path``'s credentials describes this session.

    Refuses both on a genuine mismatch and on "cannot tell", because the defect being
    closed is a *confident* wrong number. The module already degrades silently on a
    missing token, an offline machine or schema drift; this is the same contract
    extended to identity.
    """
    none = Identity(None, None)
    if not in_claude_session():
        return Attribution(True, none, none, None)
    # Ambient credentials sit at ~/.claude/.credentials.json with their config one level
    # up; an isolated account keeps both in the same dir.
    cfg = (cred_path.parent / ".claude.json") if cred_path is not None else config_path()
    reading = identity_for_config(cfg)
    mine = session_identity()
    if mine.matches(reading):
        return Attribution(True, mine, reading, None)
    if not mine:
        return Attribution(False, mine, reading, "this session's account could not be determined")
    if not reading:
        return Attribution(False, mine, reading, "the account behind these credentials could not be determined")
    return Attribution(False, mine, reading, "these credentials belong to a different account than this session")


def _oauth_token(path: Path | None = None) -> str | None:
    """The Claude Code OAuth access token, refreshing it if the stored one expired.

    Claude Code refreshes its token in-process and writes the file on its own
    cadence, so the on-disk ``accessToken`` is routinely stale between runs. When
    it is, mint a fresh one from the ``refreshToken`` (and persist it) rather than
    going dark — otherwise the usage→closure hook never fires.
    """
    cred = path or credentials_path()
    try:
        data = json.loads(cred.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    oauth = data.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        return None
    token = oauth.get("accessToken")
    expires_at = oauth.get("expiresAt")
    # expiresAt is epoch milliseconds; treat a missing/past value as expired.
    expired = not isinstance(expires_at, int | float) or expires_at / 1000.0 <= time.time()
    if isinstance(token, str) and token and not expired:
        return token

    refresh = oauth.get("refreshToken")
    if isinstance(refresh, str) and refresh:
        return _refresh_access_token(refresh, cred)
    return None


def _refresh_access_token(refresh_token: str, cred_path: Path, *, timeout: float = 15.0) -> str | None:
    """Exchange the refresh token for a fresh access token and persist it.

    Refresh tokens rotate, so the new ``refresh_token`` must be saved or the next
    refresh fails. Best-effort: any auth/network/parse failure yields None.
    """
    body = json.dumps(
        {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": _OAUTH_CLIENT_ID}
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https host)
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    access = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(access, str) or not access:
        return None
    _persist_refreshed(cred_path, payload)
    return access


def _persist_refreshed(cred_path: Path, payload: dict[str, Any]) -> None:
    """Write the rotated token fields back into the credentials file in place.

    Re-reads the file so we only touch the three OAuth fields and keep everything
    else (subscriptionType, rateLimitTier, …) intact.
    """
    # ponytail: no file lock; a Claude Code write racing this is rare and self-heals
    # on the next run. Add locking only if concurrent corruption is ever observed.
    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    oauth = data.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        return
    oauth["accessToken"] = payload["access_token"]
    if isinstance(payload.get("refresh_token"), str):
        oauth["refreshToken"] = payload["refresh_token"]
    if isinstance(payload.get("expires_in"), int | float):
        oauth["expiresAt"] = int((time.time() + payload["expires_in"]) * 1000)
    if isinstance(payload.get("scope"), str):
        oauth["scopes"] = payload["scope"].split()
    try:
        cred_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    except OSError:
        return


def fetch_usage(*, token: str | None = None, timeout: float = 8.0, cred_path: Path | None = None) -> dict[str, Any] | None:
    """GET the OAuth usage payload. None on any auth/network/parse failure."""
    tok = token or _oauth_token(cred_path)
    if not tok:
        return None
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {tok}",
            "anthropic-beta": _OAUTH_BETA,
            "anthropic-version": "2023-06-01",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https host)
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _window(payload: dict[str, Any], key: str) -> tuple[float | None, str | None]:
    block = payload.get(key)
    if not isinstance(block, dict):
        return None, None
    pct = block.get("utilization")
    resets = block.get("resets_at")
    return (
        float(pct) if isinstance(pct, int | float) else None,
        resets if isinstance(resets, str) else None,
    )


def latest_usage(
    *,
    token: str | None = None,
    cred_path: Path | None = None,
    timeout: float = 8.0,
    require_session_attribution: bool = True,
) -> UsageReport | None:
    """The current usage reading, or None when there isn't one *for this session*.

    Attribution is enforced by default so that any caller reading "the ambient number"
    inherits the check rather than having to remember it. Pass
    ``require_session_attribution=False`` only when the reading is deliberately scoped
    to a *named* account (an explicit ``--account`` query), where it is that account's
    figure being asked for and no claim about this session is made.
    """
    if require_session_attribution and not check_attribution(cred_path).ok:
        return None
    payload = fetch_usage(token=token, cred_path=cred_path, timeout=timeout)
    if payload is None:
        return None
    five_pct, five_reset = _window(payload, "five_hour")
    week_pct, week_reset = _window(payload, "seven_day")
    if five_pct is None and week_pct is None:
        return None
    return UsageReport(five_pct, five_reset, week_pct, week_reset)


def _fmt_reset(value: str | None) -> str:
    if not value:
        return "unknown reset"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def usage_findings(*, threshold: float = 90.0, report: UsageReport | None = None, **kwargs: Any) -> list[Finding]:
    """Findings for Claude subscription usage, parallel to ``codex_usage.usage_findings``."""
    report = report if report is not None else latest_usage(**kwargs)
    if report is None:
        # Name identity as the cause when that is the cause. "Token missing/expired or
        # offline" would send a reader to look for a network fault that isn't there.
        attribution = check_attribution(kwargs.get("cred_path"))
        if not attribution.ok:
            return [Finding("ok", f"no Claude usage signal for this session's account ({attribution.reason})")]
        return [Finding("ok", "no Claude usage signal available (token missing/expired or offline)")]

    parts: list[str] = []
    # Closure triggers on the 5-hour window only — it's the fast-moving limit you hit
    # mid-session. The weekly figure is shown for context but does not drive closure
    # (a separate weekly-aware nudge is a future feature). See is_over_threshold.
    if report.five_hour_percent is not None:
        parts.append(f"5h limit {report.five_hour_percent:.0f}% used (resets {_fmt_reset(report.five_hour_resets_at)})")
    if report.seven_day_percent is not None:
        parts.append(f"weekly limit {report.seven_day_percent:.0f}% used (resets {_fmt_reset(report.seven_day_resets_at)})")

    if not parts:
        return [Finding("ok", "no Claude usage signal available")]
    over = is_over_threshold(threshold, report)
    level = "warn" if over else "ok"
    suffix = "; run the closure ritual before continuing this session" if over else ""
    return [Finding(level, "Claude " + "; ".join(parts) + suffix)]


def is_over_threshold(threshold: float, report: UsageReport | None) -> bool:
    """Closure trigger: the 5-hour window only (not weekly)."""
    if report is None or report.five_hour_percent is None:
        return False
    return report.five_hour_percent >= threshold
