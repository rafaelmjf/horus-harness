"""Inbound steering channel: deterministic Telegram control for horus.

The outbound half (:mod:`horus.notify`) pushes escalations to the owner's phone. This
is the inbound half — so the owner can *steer* horus projects from the phone, not just
receive pushes. It long-polls the Telegram Bot API ``getUpdates`` for the configured
owner ``chat_id`` and maps a BOUNDED command grammar 1:1 onto existing deterministic
``horus`` commands.

Load-bearing constraints (owner, 2026-07-18), mirroring :mod:`horus.notify`:

- **Deterministic, no LLM, no hermes.** Every inbound message or button tap resolves to
  an allowlisted ``horus`` subprocess (argv list, never a shell string). Unknown input
  returns the help card — never an error, never a shell.
- **Owner-only.** Only the configured ``chat_id`` is honored; every other sender is
  silently ignored (``unauthorized_dm_behavior: ignore``).
- **Never mints authority.** The grammar is read-mostly plus a few bounded mutations
  (cancel a pending dispatch, re-fire supervise). No ``envelope create``, nothing
  ``--allow-merge``, nothing work-plane. A ``supervise`` re-fire still obeys the run's
  standing envelope.
- **Best-effort transport.** A transport error never crashes the loop; the kill switch
  is not running ``listen`` (or ``sink = "none"``).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

from horus.notify import NotifyConfig, load_notify_config

# A phone screen + Telegram's 4096-char message cap. Truncate command output to fit.
_MAX_REPLY = 3500
# Long-poll seconds handed to getUpdates; the HTTP read timeout adds a margin on top.
_POLL_SECONDS = 30
_HTTP_MARGIN = 15.0
# Bounded-command subprocess cap. supervise can watch CI, so give it real room.
_CMD_TIMEOUT = 900.0

# Arguments are ids/session prefixes only — a tight charset keeps arbitrary text out of
# argv even though we never touch a shell.
_SAFE_ARG = re.compile(r"^[A-Za-z0-9_.\-]+$")

_NO_WINDOW = (
    {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    if sys.platform == "win32"
    else {}
)


@dataclass(frozen=True)
class Command:
    """One allowlisted verb → a base ``horus`` argv. ``takes_arg`` verbs require a
    single safe-charset argument (an id or session prefix)."""

    argv: tuple[str, ...]
    help: str
    takes_arg: bool = False
    mutating: bool = False
    wants_repo: bool = False  # append `--path <repo>` when a repo is known


# The whole steering surface. Read-mostly + two bounded mutations. Nothing here mints
# authority or reaches the work plane.
COMMANDS: dict[str, Command] = {
    "sessions": Command(("sessions",), "sessions — live/recent runs"),
    "schedule": Command(("schedule", "list"), "schedule — scheduled dispatches"),
    "backlog": Command(("backlog", "list"), "backlog — open cards"),
    "usage": Command(("usage", "check"), "usage — capacity"),
    "warmup": Command(
        ("warmup",), "warmup — start the 5h window on each Claude account", mutating=True,
    ),
    "cancel": Command(
        ("schedule", "cancel"), "cancel <id> — stop a pending dispatch",
        takes_arg=True, mutating=True,
    ),
    "release": Command(
        ("schedule", "release"), "release <id> — re-arm an andon-halted dispatch",
        takes_arg=True, mutating=True,
    ),
    "supervise": Command(
        ("supervise",), "supervise <session> — re-run the acceptance gate",
        takes_arg=True, mutating=True, wants_repo=True,
    ),
}


def _help_text(prefix: str = "") -> str:
    lines = [prefix.rstrip()] if prefix else []
    lines.append("horus steering — commands:")
    lines += [f"  {name} {'<arg>' if c.takes_arg else ''}".rstrip() + f"  · {c.help.split('—',1)[-1].strip()}"
              for name, c in COMMANDS.items()]
    lines.append("  help — this list")
    return "\n".join(lines)


@dataclass(frozen=True)
class Reply:
    """The result of handling one update: text to send back, and (for a button tap) the
    callback query id to acknowledge so Telegram stops showing the spinner."""

    text: str
    answer_callback_id: str | None = None


def _run_horus(argv: list[str], *, timeout: float = _CMD_TIMEOUT) -> str:
    """Run an allowlisted ``horus`` subcommand (argv list, no shell) and return its
    combined output, truncated for a phone."""
    try:
        result = subprocess.run(  # noqa: S603 - argv list, allowlisted verbs only
            ["horus", *argv], capture_output=True, text=True, timeout=timeout, **_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return f"(timed out after {int(timeout)}s: horus {' '.join(argv)})"
    except OSError as exc:
        return f"(could not run horus {' '.join(argv)}: {exc})"
    out = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    out = out.strip() or f"(no output; exit {result.returncode})"
    if len(out) > _MAX_REPLY:
        out = out[:_MAX_REPLY] + "\n…(truncated)"
    return out


def dispatch(
    command: str, *, repo: str | None = None,
    runner: Callable[[list[str]], str] = _run_horus,
) -> str:
    """Map one bounded command string onto a deterministic ``horus`` invocation.

    Pure but for ``runner`` (which shells out); tests pass a fake runner. Unknown or
    malformed input returns the help card, never an error and never a shell."""
    tokens = command.strip().lstrip("/").split(maxsplit=1)
    if not tokens:
        return _help_text()
    verb = tokens[0].lower()
    arg = tokens[1].strip() if len(tokens) > 1 else ""
    if verb in ("help", "start"):
        return _help_text()
    cmd = COMMANDS.get(verb)
    if cmd is None:
        return _help_text(f"unknown command: {verb!r}")
    if cmd.takes_arg:
        if not arg:
            return f"usage: {verb} <arg>  ({cmd.help})"
        arg = arg.split()[0]  # a single token only
        if not _SAFE_ARG.match(arg):
            return f"invalid argument for {verb} (letters, digits, . _ - only)"
    argv = list(cmd.argv) + ([arg] if cmd.takes_arg else [])
    if cmd.wants_repo and repo:
        argv += ["--path", repo]
    return runner(argv)


# --------------------------------------------------------------------------- #
# Update handling — chat_id gated, transport-agnostic.
# --------------------------------------------------------------------------- #


def _chat_id_of(update: dict) -> str | None:
    if "callback_query" in update:
        msg = update["callback_query"].get("message") or {}
    elif "message" in update:
        msg = update["message"]
    else:
        return None
    chat = (msg.get("chat") or {}).get("id")
    return str(chat) if chat is not None else None


def handle_update(
    update: dict, cfg: NotifyConfig, *, repo: str | None = None,
    runner: Callable[[list[str]], str] = _run_horus,
) -> Reply | None:
    """Turn one Telegram update into a :class:`Reply`, or ``None`` if it is ignored
    (wrong chat, or not a message/callback we handle). Owner ``chat_id`` gate first."""
    if cfg.chat_id and _chat_id_of(update) != str(cfg.chat_id):
        return None  # unauthorized sender — ignore silently
    if "callback_query" in update:
        cq = update["callback_query"]
        text = dispatch(str(cq.get("data") or ""), repo=repo, runner=runner)
        return Reply(text=text, answer_callback_id=cq.get("id"))
    if "message" in update:
        text = update["message"].get("text")
        if not text:
            return None
        return Reply(text=dispatch(text, repo=repo, runner=runner))
    return None


# --------------------------------------------------------------------------- #
# Telegram transport. Monkeypatched in tests.
# --------------------------------------------------------------------------- #


def _api(cfg: NotifyConfig, method: str) -> str:
    return f"https://api.telegram.org/bot{cfg.token}/{method}"


def _get_updates(cfg: NotifyConfig, offset: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "offset": offset, "timeout": _POLL_SECONDS,
        "allowed_updates": json.dumps(["message", "callback_query"]),
    })
    req = urllib.request.Request(_api(cfg, "getUpdates") + "?" + params)  # noqa: S310
    with urllib.request.urlopen(req, timeout=_POLL_SECONDS + _HTTP_MARGIN) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8", "replace"))
    return data.get("result", []) if data.get("ok") else []


def _post(cfg: NotifyConfig, method: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        _api(cfg, method), data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=_HTTP_MARGIN) as resp:  # noqa: S310
        resp.read()


def _reply(cfg: NotifyConfig, reply: Reply) -> None:
    if reply.answer_callback_id:
        try:
            _post(cfg, "answerCallbackQuery", {"callback_query_id": reply.answer_callback_id})
        except Exception:  # noqa: BLE001 - acking a tap is best-effort
            pass
    _post(cfg, "sendMessage", {
        "chat_id": cfg.chat_id, "text": reply.text, "disable_web_page_preview": True,
    })


@dataclass
class ListenResult:
    handled: int = 0
    ignored: int = 0
    errors: int = 0
    stopped: str = ""


def listen(
    cfg: NotifyConfig, *, duration: float | None = None, repo: str | None = None,
    now: Callable[[], float] = time.monotonic,
    get_updates: Callable[[NotifyConfig, int], list[dict]] = _get_updates,
    send: Callable[[NotifyConfig, Reply], None] = _reply,
    max_iterations: int | None = None,
) -> ListenResult:
    """Long-poll and dispatch until ``duration`` elapses or interrupted. Best-effort:
    a transport error is counted and the loop continues. ``max_iterations`` bounds the
    loop in tests."""
    deadline = (now() + duration) if duration else None
    offset = 0
    result = ListenResult()
    iterations = 0
    while True:
        if deadline is not None and now() >= deadline:
            result.stopped = "duration elapsed"
            break
        if max_iterations is not None and iterations >= max_iterations:
            result.stopped = "max iterations"
            break
        iterations += 1
        try:
            updates = get_updates(cfg, offset)
        except Exception as exc:  # noqa: BLE001 - best-effort poll
            result.errors += 1
            result.stopped = f"poll error: {exc}"
            time.sleep(2)
            continue
        for update in updates:
            offset = max(offset, int(update.get("update_id", 0)) + 1)
            reply = handle_update(update, cfg, repo=repo)
            if reply is None:
                result.ignored += 1
                continue
            try:
                send(cfg, reply)
                result.handled += 1
            except Exception:  # noqa: BLE001 - a failed send never stops the loop
                result.errors += 1
    return result


def validate_config() -> tuple[int, str] | None:
    """``None`` when the telegram sink is usable for listening, else the
    ``(exit_code, message)`` a CLI should print and return. Shared by the
    foreground listen and the persistent ``--service`` install so a dead unit is
    never installed against a misconfigured sink."""
    cfg = load_notify_config()
    if cfg.sink != "telegram":
        return 2, (
            f"notify listen needs the telegram sink (current: {cfg.sink!r}). "
            "Configure [notify] sink/token/chat_id in ~/.horus/config.toml."
        )
    if not cfg.token or not cfg.chat_id:
        return 2, "telegram sink needs both token and chat_id in [notify]."
    return None


def run_listen(*, duration: float | None, repo: str | None) -> tuple[int, str]:
    """CLI entry: validate config, then listen. Returns (exit_code, message)."""
    invalid = validate_config()
    if invalid is not None:
        return invalid
    cfg = load_notify_config()
    window = f"for {int(duration)}s" if duration else "until interrupted"
    print(f"horus notify listen: polling as owner chat {cfg.chat_id} ({window}). Ctrl-C to stop.")
    try:
        res = listen(cfg, duration=duration, repo=repo)
    except KeyboardInterrupt:
        return 0, "stopped (interrupt)."
    return 0, f"stopped ({res.stopped}); handled {res.handled}, ignored {res.ignored}, errors {res.errors}."
