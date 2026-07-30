"""Suite-wide isolation from the ambient agent environment.

Tests fake ``HOME`` (20+ helpers do) to point Horus's config/cache tree at a
tmp dir. That is not sufficient on its own: ``CLAUDE_CONFIG_DIR`` and
``CODEX_HOME`` are resolved *ahead* of ``HOME`` when locating an agent's
config/credentials (``config.agent_config_dir``, ``config.py:787``), and under
Horus account isolation both are always set in the environment a session runs
in. So a faked ``HOME`` alone leaves a real, logged-in account dir reachable.

The same gap exists one layer down, for the *terminal hosts*: a faked ``HOME``
does not move tmux's or herdr's default server socket, so any test that reaches
a real host binary talks to the owner's live server and its real agent
sessions. That is not hypothetical — it happened twice (see
``isolate_session_host_sockets``).

And it exists one layer *up* as well: faking ``HOME`` is a convention here, not
an invariant, so a test that simply forgets writes to the owner's real
``~/.horus`` (see ``isolate_home``).

The through-line for all three fixtures: **test state must never escape into
the owner's real environment**, and the guard belongs here rather than in the
tests, because a per-test guard protects only the test that remembers it.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

# Resolved ahead of HOME when locating an agent's config/credentials, so a faked
# HOME does not isolate them.
AMBIENT_AGENT_ENV = ("CLAUDE_CONFIG_DIR", "CODEX_HOME")

# Set by tmux/herdr inside their own panes. While one of these is set the host
# talks to *that* server, which defeats the socket redirection below — so they
# are cleared for the same reason, not merely for tidiness.
INSIDE_HOST_ENV = ("TMUX", "HERDR_ENV", "HERDR_PANE_ID")


@pytest.fixture(autouse=True)
def isolate_ambient_agent_env(monkeypatch):
    """Unset the per-account agent config-dir vars for every test.

    Hardening, not a fix for a specific known failure: this closes the gap
    between what a faked ``HOME`` claims to isolate and what it actually does,
    for the whole suite at once rather than per helper.

    Prompted by (but NOT demonstrated to fix)
    ``test_capture_usage_snapshot_unavailable_on_failed_read``, which asserts
    that an isolated fake HOME reads ``unavailable`` and was observed returning
    ``fresh`` twice on unmodified main on 2026-07-26 — blocking a dispatched
    worker whose gate it broke. That flake's mechanism is still unidentified;
    see the backlog card. Clearing these vars was one hypothesis, and the
    symptom did not reproduce afterwards either way.

    A test that genuinely needs one of these set does so itself; this fixture
    runs first, so an explicit ``setenv`` in the test still wins.
    """
    for name in AMBIENT_AGENT_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def isolate_home(monkeypatch, tmp_path_factory):
    """Give every test a private ``HOME``, so none can reach the real
    ``~/.horus``.

    ``config.config_dir()`` is ``Path.home() / ".horus"``, so a test that never
    fakes ``HOME`` reads and **writes** the owner's production registry. Most
    helpers do fake it — which is exactly the problem, because "most" is not an
    invariant and the exceptions are invisible.

    Measured on 2026-07-30, not theorised.
    ``test_an_unknown_launch_target_degrades_instead_of_raising`` takes no
    fixtures at all, so nothing faked ``HOME`` for it; its ``_reg_with`` helper
    calls ``Registry.default().upsert(...)`` and wrote the fictional session
    ``12345678-1234-1234-1234-123456789abc`` — plus a real
    ``~/.horus/logs/runs/<id>.jsonl`` — straight into the owner's tree. It was
    the only leaker in the suite, found by bisecting on that file's mtime, and
    it had been landing rows there for at least two days.

    This is the same defect as ``isolate_session_host_sockets`` one layer up:
    test state escaping into the owner's real environment. The socket fixture
    keeps tests off the owner's *servers*; this keeps them out of the owner's
    *config tree*. Both are suite-wide for the same reason — a per-test guard
    protects only the test that remembers it.

    A test that wants a differently-shaped home still sets one; this runs
    first, so its ``setenv`` wins.
    """
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


@pytest.fixture(scope="session")
def _throwaway_host_sockets():
    """One short-pathed directory for the whole run to point host sockets at.

    Kept SHORT deliberately, which is why this is ``mkdtemp`` and not
    ``tmp_path_factory``: a unix socket path is capped by ``sun_path``
    (108 bytes on Linux, 104 on macOS), and pytest's own tmp paths spend most
    of that budget on the session and test names before a socket name is even
    appended. ``mkdtemp`` under the system temp dir yields roughly 20
    characters, which leaves room.

    Removed at session end, since nothing here is worth keeping and the whole
    point is that no server was ever started on it.
    """
    path = Path(tempfile.mkdtemp(prefix="hz-"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def isolate_session_host_sockets(monkeypatch, _throwaway_host_sockets):
    """Point every terminal host's DEFAULT server at a throwaway socket.

    This is the suite-wide form of the ``-S <socket>`` guard that the tmux
    live test has carried since the 2026-07-13 incident. That guard was per
    test, so it protected exactly the one test that remembered it — and on
    2026-07-30 the herdr host proved the point: its live lifecycle test
    promised isolation in its docstring, never implemented it, and its
    ``finally`` block ran ``herdr server stop`` against the owner's real
    server, killing three live agent sessions mid-work. Both incidents are the
    same defect, one host apart, which is why the guard now lives here instead
    of in a test: a host added later inherits it rather than re-learning it.

    The redirection is per host, because each finds its server differently:

    - **tmux** — ``$TMUX_TMPDIR/tmux-<uid>/default``. Verified 2026-07-30: this
      is only honoured once ``$TMUX`` is unset, since a tmux inside a pane
      prefers the socket named in ``$TMUX``. Both are handled.
    - **herdr** — ``$HERDR_SOCKET_PATH`` directly. Note this is NOT
      ``HERDR_CONFIG_PATH``: that moves the config *file* only, and was
      measured on 2026-07-30 (herdr v0.7.5) to leave the socket pointing at
      the real one. The old docstring in ``test_hosts_herdr.py`` claimed
      otherwise; it was wrong.

    Nothing is started here. The paths simply have no server on them, so an
    unmocked host call fails with the same ENOENT the hosts already explain
    (``herdr._why_not``) instead of quietly succeeding against the owner's.

    A test that needs a real server of its own overrides these with its own
    socket — see ``test_live_herdr_server_lifecycle`` — and that override wins,
    because this fixture runs first.
    """
    for name in INSIDE_HOST_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TMUX_TMPDIR", str(_throwaway_host_sockets))
    monkeypatch.setenv("HERDR_SOCKET_PATH", str(_throwaway_host_sockets / "herdr.sock"))
