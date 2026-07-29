"""Session hosts: which one is in play, and how a caller finds it.

Selection order, most explicit first:

1. ``HORUS_TERMINAL_TARGET`` — the long-standing env override, unchanged.
2. ``[terminal] host`` in config.toml — per-machine preference.
3. ``auto`` — the first available host in :data:`AUTO_ORDER`.

A host id is durable: it is written into ``registry.SessionRecord.launch_target``
and read back by a possibly-different Horus install. So an id this install does
not recognise must degrade honestly (no attach offered) rather than raise — see
:func:`for_record`.
"""

from __future__ import annotations

import os

from horus import config
from horus.hosts.base import Capabilities, SessionHost
from horus.hosts.current import CurrentHost
from horus.hosts.tmux import TmuxHost

CURRENT = "current"
TMUX = "tmux"

# Preference order for `auto`: the most capable host that works here wins. The
# `current` host is last because it is the floor — it always works and promises
# nothing.
AUTO_ORDER: tuple[str, ...] = (TMUX, CURRENT)

_HOSTS: dict[str, SessionHost] = {}


def _hosts() -> dict[str, SessionHost]:
    # Built once, lazily: constructing a host must not run at import time, since
    # importing horus.hosts happens long before anyone launches anything.
    if not _HOSTS:
        for host in (TmuxHost(), CurrentHost()):
            _HOSTS[host.id] = host
    return _HOSTS


def all_hosts() -> list[SessionHost]:
    return list(_hosts().values())


def ids() -> tuple[str, ...]:
    """Every known host id, for building CLI choices from the registry rather
    than hard-coding a literal tuple in argparse."""
    return tuple(_hosts())


def get(host_id: str) -> SessionHost | None:
    return _hosts().get(host_id)


def resolve() -> SessionHost:
    """The host this process should use. Never raises: `current` is always valid."""
    override = os.environ.get("HORUS_TERMINAL_TARGET", "").strip().lower()
    if (host := _hosts().get(override)) is not None:
        return host
    preferred = config.load_terminal_host()
    if preferred != "auto" and (host := _hosts().get(preferred)) is not None and host.available():
        return host
    for host_id in AUTO_ORDER:
        host = _hosts()[host_id]
        if host.available():
            return host
    return _hosts()[CURRENT]


def for_record(record) -> SessionHost | None:
    """The host that owns ``record``, or ``None`` when this install has never
    heard of it. A None result means "make no promises about this session" —
    it is why an unknown ``launch_target`` degrades to `original terminal only`
    instead of offering an attach that cannot work.
    """
    return _hosts().get(getattr(record, "launch_target", "") or "")


__all__ = [
    "AUTO_ORDER", "CURRENT", "TMUX", "Capabilities", "SessionHost",
    "all_hosts", "for_record", "get", "ids", "resolve",
]
