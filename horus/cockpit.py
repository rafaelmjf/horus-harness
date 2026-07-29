"""`horus tui <host>` — open the Horus cockpit *inside* a session host.

`horus tui` runs the TUI in the terminal you are standing in. Naming a host runs
it inside that host instead, which is what makes the multi-agent workflow
practical: the cockpit lives in one pane, every launch creates a sibling session
on the same server, and attaching switches you there and back (`Ctrl-b L` on
tmux) rather than nesting a client.

This is composition, not new mechanism — it reuses each host's own create/attach
verbs. Two behaviours are the whole design:

- **Idempotent.** One cockpit per host, found by a fixed ref. Re-running attaches
  to the existing one instead of accumulating cockpits you lose track of.
- **Never nests.** Already inside the host you asked for? Run in place.
"""

from __future__ import annotations

import os
import subprocess
import sys

from horus import hosts

# One cockpit per host, by name. Deliberately not per-project: the TUI is the
# fleet-level surface, and a second one is confusion rather than capacity.
#
# The tmux name keeps the ``horus-`` prefix, which is how Horus-owned tmux sessions are
# identifiable (and what `_live_tmux_sessions` filters on). herdr's is a space label the
# owner reads in a sidebar, so it is spelled for a human — see `hosts.herdr`.
COCKPIT_REF = "horus-cockpit"


def _tui_command() -> list[str]:
    """The argv that runs *this* Horus's TUI inside a pane.

    Always this interpreter's own module entry point, never `shutil.which("horus")`.
    A console script resolves against ambient PATH, so the cockpit could end up
    running a different Horus than the caller — observed live: a checkout invoked
    a globally-installed 0.0.77 cockpit, which would not even have this command.
    Binding to `sys.executable` makes "the cockpit runs what I ran" true by
    construction rather than by PATH order.
    """
    return [sys.executable, "-m", "horus", "tui"]


def open_in(host_id: str) -> tuple[int, str]:
    """Open the cockpit inside ``host_id``. Returns ``(exit_code, message)``."""
    host = hosts.get(host_id)
    if host is None:
        known = ", ".join(hosts.ids())
        return 2, f"unknown session host {host_id!r}. Known hosts: {known}"

    if host_id == hosts.CURRENT:
        # The explicit no-op: what plain `horus tui` already does.
        return 0, ""

    if not host.available():
        return 2, f"{host_id} is not installed or is unavailable on this platform"

    if (not_ready := host.ensure_ready()) is not None:
        return 2, not_ready

    # Already inside the host we were asked for: run here rather than nesting a
    # cockpit inside a cockpit.
    if host.switches_in_place():
        return 0, ""

    existing = _find_cockpit(host)
    if existing is None:
        created, error = _create_cockpit(host)
        if error is not None:
            return 2, error
        existing = created
    elif not _cockpit_is_live(host, existing):
        # A cockpit whose TUI has died. This is not hypothetical: herdr persists
        # workspace *structure* across a server restart but not processes, so the
        # workspace comes back with a bare shell in it. Attaching to that is a blank
        # screen; re-running the TUI in the pane we already have both fixes it and
        # avoids leaving a second cockpit behind.
        if (error := _revive_cockpit(host, existing)) is not None:
            return 2, error

    error = _attach_cockpit(host, existing)
    return (2, error) if error else (0, "")


def _cockpit_is_live(host, ref: str) -> bool:
    """Whether the cockpit's TUI is actually running in ``ref``.

    A ref existing is not evidence that anything is in it — the same reason the
    reaper never trusts a ref's mere presence. Checked by looking for our own
    process, because a host that cannot report liveness cannot be asked.
    """
    if host.id == hosts.TMUX:
        # tmux ends a session when its process exits, so a listed session is live.
        return True
    if host.id == hosts.HERDR:
        from horus.hosts import herdr

        return not herdr.pane_is_idle(ref)
    return True


def _revive_cockpit(host, ref: str) -> str | None:
    """Restart the TUI inside an existing but dead cockpit pane."""
    if host.id != hosts.HERDR:
        return None
    from horus.hosts import herdr

    started = herdr._run("pane", "run", ref, " ".join(_tui_command()))
    if started.returncode != 0:
        return f"failed to restart the cockpit in {host.id}: {herdr._detail(started)}"
    return None


def _find_cockpit(host) -> str | None:
    """The ref of this host's live cockpit, or ``None``.

    Asked of the host's own listing rather than remembered in the registry: a
    cockpit is not a tracked agent session, and a stale note about one would send
    an attach at a pane that no longer exists.
    """
    if host.id == hosts.TMUX:
        from horus.hosts import tmux

        return COCKPIT_REF if COCKPIT_REF in tmux.TmuxHost().live_refs() else None
    if host.id == hosts.HERDR:
        from horus.hosts import herdr

        listed = herdr._payload(herdr._run("pane", "list")).get("panes", [])
        candidates = []
        for pane in listed:
            workspace = herdr._payload(
                herdr._run("workspace", "get", pane.get("workspace_id", "")),
            ).get("workspace", {})
            if workspace.get("label") == herdr.COCKPIT_LABEL and pane.get("pane_id"):
                candidates.append(pane["pane_id"])
        if not candidates:
            return None
        # Restarts can leave more than one labelled workspace behind. Prefer one with
        # a live TUI; otherwise take the first so it gets revived rather than
        # duplicated. Never close the extras here — one of them may be someone's
        # live cockpit, and guessing is how a live session gets killed.
        for ref in candidates:
            if _cockpit_is_live(host, ref):
                return ref
        return candidates[0]
    return None


def _create_cockpit(host) -> tuple[str | None, str | None]:
    """Create the cockpit pane and return ``(ref, error)``."""
    command = _tui_command()
    if host.id == hosts.TMUX:
        created = subprocess.run(  # noqa: S603,S607 - fixed argv; ref is Horus-owned
            ["tmux", "new-session", "-d", "-s", COCKPIT_REF, *command],
            capture_output=True, text=True, check=False,
        )
        if created.returncode != 0:
            detail = (created.stderr or created.stdout).strip() or "tmux failed"
            return None, f"failed to create the tmux cockpit: {detail}"
        return COCKPIT_REF, None
    if host.id == hosts.HERDR:
        from horus.hosts import herdr

        created = herdr._run("workspace", "create", "--label", herdr.COCKPIT_LABEL, "--no-focus")
        pane_id = herdr._payload(created).get("root_pane", {}).get("pane_id")
        if not pane_id:
            return None, f"failed to create the herdr cockpit: {herdr._detail(created)}"
        started = herdr._run("pane", "run", pane_id, " ".join(command))
        if started.returncode != 0:
            herdr._run("pane", "close", pane_id)
            return None, f"failed to start the cockpit in herdr: {herdr._detail(started)}"
        return pane_id, None
    return None, f"{host.id} cannot host a cockpit"


def _attach_cockpit(host, ref: str) -> str | None:
    """Put this terminal on the cockpit. Error string, or ``None``.

    Goes through the host's own viewer argv rather than a hand-built command, so
    a host that needs preparation first (herdr focuses the workspace) gets it.
    """
    argv = host.viewer_argv(ref)
    if argv is None:
        return f"{host.id} could not provide a viewer for the cockpit"
    attached = subprocess.run(  # noqa: S603 - argv came from the host itself
        argv, check=False, env={**os.environ, "TERM": os.environ.get("TERM") or "xterm-256color"},
    )
    if attached.returncode != 0:
        return f"attaching the {host.id} cockpit failed with exit code {attached.returncode}"
    return None
