"""Machine-local push channel so an unattended supervisor can reach the owner.

Every escalation surface in ``horus`` is otherwise *pull-based*: a ``blocked``/
``failed`` delivery shows only in ``horus sessions``, a freshness finding only in
``horus close``. A headless run (scheduled dispatch, ``horus supervise``) that hits a
red gate at 05:30 has no way to actively notify. This module is that push channel.

Design constraints (owner, 2026-07-17), all load-bearing:

- **Horus owns the event wiring, never a transport or a token embedded in git.** The
  sink is configured machine-locally in ``~/.horus/config.toml`` ``[notify]`` — never
  ``fleet.toml``, never committed. Secrets live only on the machine that sends.
- **A sink is OPTIONAL.** With ``sink = "none"`` (the default) escalations stay
  pull-based exactly as before; a machine with no sink still schedules and supervises.
- **Best-effort by construction.** :func:`escalate` never raises. A dead bot, a webhook
  500, or no network yields an error *result* — it never fails the run being reported on.

Sinks:

- ``telegram`` — POST to the Telegram Bot API directly (a dedicated bot token +
  chat_id). Needs no Hermes at all, which is precisely how "Hermes is optional" is met.
- ``hermes`` — shell out to ``hermes send`` (one-shot messenger; Horus owns no token).
- ``webhook`` — POST the escalation as JSON to a URL, for anyone without either.
- ``none`` — no sink; pull-only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from typing import Callable

from horus import config

# --------------------------------------------------------------------------- #
# Events. Failure/halt events escalate by default; a clean-accept "success" ping
# is opt-in (add "success" to [notify].events) so the channel never nags on a good
# run. Unknown strings in the config simply never match an emitted event.
# --------------------------------------------------------------------------- #

DELIVERY_FAILED = "delivery-failed"   # a scheduled/unattended worker ended blocked/failed
USAGE_BAND = "usage-band"             # an unattended run halted on a usage band/death
SUPERVISE_GATE = "supervise-gate"     # a headless supervisor hit a red required gate
SUCCESS = "success"                   # a clean accept (opt-in only)

DEFAULT_EVENTS: frozenset[str] = frozenset({DELIVERY_FAILED, USAGE_BAND, SUPERVISE_GATE})
KNOWN_EVENTS: frozenset[str] = DEFAULT_EVENTS | {SUCCESS}

VALID_SINKS: frozenset[str] = frozenset({"none", "telegram", "hermes", "webhook"})

# Short so a hung network never stalls the run this is reporting on for long.
_SEND_TIMEOUT = 10.0

_NO_WINDOW = (
    {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    if sys.platform == "win32"
    else {}
)


@dataclass(frozen=True)
class NotifyConfig:
    """The ``[notify]`` block, already parsed. ``sink == "none"`` means pull-only."""

    sink: str = "none"
    events: frozenset[str] = DEFAULT_EVENTS
    # telegram
    token: str | None = None
    chat_id: str | None = None
    # hermes: `hermes send --to <target>`; None -> the home channel (bare platform).
    target: str | None = None
    # webhook
    url: str | None = None

    def enabled(self, event: str) -> bool:
        return event in self.events


@dataclass(frozen=True)
class Escalation:
    """The essentials an owner needs to act, transport-agnostic."""

    event: str
    project: str
    summary: str
    session_id: str | None = None
    card: str | None = None
    sha: str | None = None
    pr: int | None = None
    inspect: str | None = None

    def subject(self) -> str:
        return f"[horus] {self.project}: {self.summary}"

    def body(self) -> str:
        mark = "✓" if self.event == SUCCESS else "⚠"
        lines = [f"{mark} {self.summary}", f"project: {self.project}"]
        if self.card:
            lines.append(f"card: {self.card}")
        if self.session_id:
            lines.append(f"session: {self.session_id}")
        if self.sha:
            lines.append(f"sha: {self.sha}")
        if self.pr:
            lines.append(f"PR: #{self.pr}")
        if self.inspect:
            lines.append(f"inspect: {self.inspect}")
        return "\n".join(lines)

    def text(self) -> str:
        return f"{self.subject()}\n\n{self.body()}"


@dataclass(frozen=True)
class EscalationResult:
    """What happened to one escalation. ``delivered`` is the only success state;
    ``skipped`` (no sink / event off) and ``error`` (transport failed) are both
    non-fatal — the run that emitted this always continues."""

    sink: str
    delivered: bool = False
    skipped: str | None = None
    error: str | None = None

    def describe(self) -> str:
        if self.delivered:
            return f"delivered via {self.sink}"
        if self.skipped:
            return f"skipped ({self.skipped})"
        if self.error:
            return f"sink {self.sink} failed: {self.error} (run unaffected — best-effort)"
        return f"no-op ({self.sink})"


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def load_notify_config() -> NotifyConfig:
    """Read ``[notify]`` from ``~/.horus/config.toml``.

    Tolerant like the other owner-level loaders: a missing file, an absent block, or
    a malformed one degrades to ``sink = "none"`` (pull-only) rather than raising —
    escalation must never be able to break a command by being misconfigured.
    """
    path = config.config_path()
    if not path.exists():
        return NotifyConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return NotifyConfig()
    raw = data.get("notify")
    if not isinstance(raw, dict):
        return NotifyConfig()

    sink = raw.get("sink")
    if not isinstance(sink, str) or not sink.strip():
        sink = "none"
    else:
        sink = sink.strip()

    events_raw = raw.get("events")
    if isinstance(events_raw, list):
        events = frozenset(str(e).strip() for e in events_raw if str(e).strip())
    else:
        events = DEFAULT_EVENTS

    chat_id = raw.get("chat_id")
    chat_id = str(chat_id) if chat_id is not None else None

    def _s(key: str) -> str | None:
        v = raw.get(key)
        return v.strip() if isinstance(v, str) and v.strip() else None

    return NotifyConfig(
        sink=sink,
        events=events,
        token=_s("token"),
        chat_id=chat_id,
        target=_s("target"),
        url=_s("url"),
    )


def render_config(cfg: NotifyConfig) -> str:
    """Human summary for ``horus notify show`` — the token is always redacted."""
    lines = [f"sink   : {cfg.sink}"]
    if cfg.sink not in VALID_SINKS:
        lines.append(f"         (unknown sink — valid: {', '.join(sorted(VALID_SINKS))})")
    lines.append(f"events : {', '.join(sorted(cfg.events)) or '(none)'}")
    if cfg.sink == "telegram":
        lines.append(f"token  : {'set (' + _redact(cfg.token) + ')' if cfg.token else 'MISSING'}")
        lines.append(f"chat_id: {cfg.chat_id or 'MISSING'}")
    elif cfg.sink == "hermes":
        lines.append(f"target : {cfg.target or 'telegram (home channel)'}")
    elif cfg.sink == "webhook":
        lines.append(f"url    : {cfg.url or 'MISSING'}")
    return "\n".join(lines)


def _redact(token: str | None) -> str:
    if not token:
        return "?"
    return token[:4] + "…" + token[-3:] if len(token) > 10 else "set"


# --------------------------------------------------------------------------- #
# Sinks. Each raises on failure; escalate() converts that into an error result.
# --------------------------------------------------------------------------- #


def _send_telegram(cfg: NotifyConfig, esc: Escalation) -> None:
    if not cfg.token or not cfg.chat_id:
        raise ValueError("telegram sink needs both token and chat_id in [notify]")
    url = f"https://api.telegram.org/bot{cfg.token}/sendMessage"
    payload = {"chat_id": cfg.chat_id, "text": esc.text(), "disable_web_page_preview": True}
    status, body = _post_json(url, payload)
    if status != 200 or '"ok":true' not in body.replace(" ", ""):
        raise RuntimeError(f"telegram API returned {status}: {body[:200]}")


def _send_webhook(cfg: NotifyConfig, esc: Escalation) -> None:
    if not cfg.url:
        raise ValueError("webhook sink needs a url in [notify]")
    payload = {
        "event": esc.event,
        "subject": esc.subject(),
        "text": esc.text(),
        "project": esc.project,
        "summary": esc.summary,
        "session_id": esc.session_id,
        "card": esc.card,
        "sha": esc.sha,
        "pr": esc.pr,
    }
    status, body = _post_json(cfg.url, payload)
    if not 200 <= status < 300:
        raise RuntimeError(f"webhook returned {status}: {body[:200]}")


def _send_hermes(cfg: NotifyConfig, esc: Escalation) -> None:
    cmd = ["hermes", "send", "--quiet", "--subject", esc.subject()]
    if cfg.target:
        cmd += ["--to", cfg.target]
    cmd.append(esc.body())
    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, timeout=_SEND_TIMEOUT, **_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        # A machine without Hermes must still run — degrade, never crash.
        raise RuntimeError("hermes not installed on this machine") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"hermes send exited {result.returncode}: {detail[:200]}")


def _post_json(url: str, payload: dict) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 - url is owner-configured, not user input
        url, data=data, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=_SEND_TIMEOUT) as resp:  # noqa: S310
        return resp.status, resp.read().decode("utf-8", "replace")


_SINKS: dict[str, Callable[[NotifyConfig, Escalation], None]] = {
    "telegram": _send_telegram,
    "hermes": _send_hermes,
    "webhook": _send_webhook,
}


# --------------------------------------------------------------------------- #
# The one entry point
# --------------------------------------------------------------------------- #


def escalate(
    esc: Escalation,
    *,
    cfg: NotifyConfig | None = None,
    force: bool = False,
    sender: Callable[[NotifyConfig, Escalation], None] | None = None,
) -> EscalationResult:
    """Best-effort push of one escalation. NEVER raises.

    ``force=True`` bypasses the per-event enable check (used by ``horus notify test``
    to exercise the transport regardless of which events are turned on). ``sender``
    overrides sink dispatch, for tests.
    """
    try:
        cfg = cfg if cfg is not None else load_notify_config()
    except Exception as exc:  # pragma: no cover - load_notify_config is itself tolerant
        return EscalationResult(sink="none", error=f"config load failed: {exc}")

    if cfg.sink == "none":
        return EscalationResult(sink="none", skipped="no sink configured")
    if not force and not cfg.enabled(esc.event):
        return EscalationResult(sink=cfg.sink, skipped=f"event {esc.event!r} not enabled")

    dispatch = sender or _SINKS.get(cfg.sink)
    if dispatch is None:
        return EscalationResult(sink=cfg.sink, error=f"unknown sink {cfg.sink!r}")

    try:
        dispatch(cfg, esc)
    except Exception as exc:  # best-effort: a failing sink never fails the run
        return EscalationResult(sink=cfg.sink, error=str(exc) or exc.__class__.__name__)
    return EscalationResult(sink=cfg.sink, delivered=True)
