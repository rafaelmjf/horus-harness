"""Remote input bridge: a session asks, the owner answers from the phone.

When a session needs owner input mid-run — a decision, an approval, a choice, or
free-text guidance — it blocks. If the owner is away from that terminal (an
unattended away worker, or just stepped out), the session stalls. This is the
deterministic substrate that unblocks it: a session writes a bounded *input
request* to disk and polls for a *response*; the single ``horus notify listen``
loop pushes the request to Telegram with tap-option buttons, and a tap or reply
writes the response the session is waiting on.

Same on-disk rendezvous pattern the rest of the system already uses (schedule =
systemd unit files, andon = ``.halt`` markers): the requesting process and the
listener are separate, so they meet through files under
``~/.horus/input-requests/``, not a shared daemon.

Hard boundary (mirrors :mod:`horus.notify_listen`): deterministic, no LLM, no
hermes. The bridge is TRANSPORT ONLY — it delivers the owner's option/text to the
requesting session and grants no authority; if the session then does something
privileged, that is the session's own gated logic. A future hermes relay layers a
conversation ON TOP of this same registry; it is not part of the mechanism.
"""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from horus import config

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")
_DEFAULT_POLL = 2.0


def requests_dir() -> Path:
    return config.config_dir() / "input-requests"


def _request_path(request_id: str) -> Path:
    return requests_dir() / f"{request_id}.json"


def _response_path(request_id: str) -> Path:
    return requests_dir() / f"{request_id}.response.json"


@dataclass
class InputRequest:
    id: str
    question: str
    options: list[str] = field(default_factory=list)
    free_text: bool = False
    default: str | None = None
    session_id: str | None = None
    project: str | None = None
    created: float = 0.0
    pushed: bool = False   # whether the listener has already pushed it to Telegram

    @classmethod
    def from_dict(cls, data: dict) -> "InputRequest":
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)


@dataclass(frozen=True)
class InputResponse:
    id: str
    answer: str
    kind: str          # "option" | "text"
    answered_at: float


def _new_id(now: float) -> str:
    """A sortable-ish, collision-resistant request id (safe charset)."""
    return f"{int(now)}-{secrets.token_hex(3)}"


def write_request(
    question: str,
    options: list[str] | None = None,
    *,
    free_text: bool = False,
    default: str | None = None,
    session_id: str | None = None,
    project: str | None = None,
    now: float | None = None,
) -> InputRequest:
    """Persist a pending input request and return it. Best-effort dir creation."""
    now = time.time() if now is None else now
    req = InputRequest(
        id=_new_id(now),
        question=question.strip(),
        options=list(options or []),
        free_text=free_text,
        default=default,
        session_id=session_id,
        project=project,
        created=now,
    )
    requests_dir().mkdir(parents=True, exist_ok=True)
    _request_path(req.id).write_text(json.dumps(asdict(req), indent=2), encoding="utf-8")
    return req


def _load_request(path: Path) -> InputRequest | None:
    try:
        return InputRequest.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def list_pending() -> list[InputRequest]:
    """Every request that has no response yet, oldest first."""
    directory = requests_dir()
    if not directory.is_dir():
        return []
    out: list[InputRequest] = []
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(".response.json"):
            continue
        req = _load_request(path)
        if req is not None and not _response_path(req.id).exists():
            out.append(req)
    return sorted(out, key=lambda r: r.created)


def mark_pushed(request_id: str) -> None:
    """Record that the listener has pushed this request, so it isn't re-sent."""
    path = _request_path(request_id)
    req = _load_request(path)
    if req is None or req.pushed:
        return
    req.pushed = True
    try:
        path.write_text(json.dumps(asdict(req), indent=2), encoding="utf-8")
    except OSError:
        pass


def read_response(request_id: str) -> InputResponse | None:
    path = _response_path(request_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return InputResponse(**{k: data[k] for k in ("id", "answer", "kind", "answered_at") if k in data})
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def write_response(request_id: str, answer: str, *, kind: str, now: float | None = None) -> bool:
    """Record the owner's answer. False if the request is unknown or already
    answered (so a double-tap can't overwrite the first answer)."""
    now = time.time() if now is None else now
    if not _request_path(request_id).exists():
        return False
    if _response_path(request_id).exists():
        return False
    resp = InputResponse(id=request_id, answer=answer, kind=kind, answered_at=now)
    requests_dir().mkdir(parents=True, exist_ok=True)
    _response_path(request_id).write_text(json.dumps(asdict(resp), indent=2), encoding="utf-8")
    return True


def resolve(id_or_prefix: str) -> InputRequest | None:
    """The single pending request whose id equals or uniquely prefixes the input."""
    matches = [r for r in list_pending() if r.id == id_or_prefix or r.id.startswith(id_or_prefix)]
    return matches[0] if len(matches) == 1 else None


def record_answer(target: str | None, payload: str, *, now: float | None = None) -> tuple[bool, str]:
    """Interpret one inbound answer and write the response.

    ``target`` is an id/prefix, or ``None`` to bind a typed reply to the single
    open request. ``payload`` is either ``#<n>`` (a 0-based option index, how the
    tap buttons encode their choice) or free text. Returns ``(ok, message)`` for
    the listener to send back."""
    if target is not None:
        req = resolve(target)
        if req is None:
            return False, f"no single open request matches {target!r}"
    else:
        pending = list_pending()
        if not pending:
            return False, "no open input request to answer"
        if len(pending) > 1:
            return False, (
                f"{len(pending)} open requests — say `answer <id> <reply>` "
                f"({', '.join(r.id[:8] for r in pending)})"
            )
        req = pending[0]

    payload = payload.strip()
    if payload.startswith("#"):
        try:
            idx = int(payload[1:])
        except ValueError:
            return False, f"invalid option {payload!r}"
        if not (0 <= idx < len(req.options)):
            return False, f"option {idx} out of range for request {req.id[:8]}"
        answer, kind = req.options[idx], "option"
    else:
        if not payload:
            return False, "empty answer"
        if not req.free_text:
            return False, f"request {req.id[:8]} takes an option, not free text"
        answer, kind = payload, "text"

    if not write_response(req.id, answer, kind=kind, now=now):
        return False, f"request {req.id[:8]} is already answered"
    return True, f"answered {req.id[:8]}: {answer}"


def await_response(
    request_id: str,
    *,
    timeout: float,
    poll: float = _DEFAULT_POLL,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> InputResponse | None:
    """Block until this request is answered or ``timeout`` seconds elapse.

    Returns the :class:`InputResponse`, or ``None`` on timeout. ``clock``/``sleep``
    are test seams."""
    deadline = clock() + timeout
    while True:
        resp = read_response(request_id)
        if resp is not None:
            return resp
        if clock() >= deadline:
            return None
        sleep(min(poll, max(0.0, deadline - clock())))


def cleanup(request_id: str) -> None:
    """Remove a request and its response once the asker has consumed the answer."""
    for path in (_request_path(request_id), _response_path(request_id)):
        try:
            path.unlink()
        except OSError:
            pass
