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
import shutil
import subprocess
import sys

from horus import hosts

# One cockpit per host, by name. Deliberately not per-project: the TUI is the
# fleet-level surface, and a second one is confusion rather than capacity.
COCKPIT_REF = "horus-cockpit"


def _tui_command() -> list[str]:
    """The argv that runs this same Horus's TUI inside a pane.

    Uses the console script when it is on PATH, else this interpreter's own
    module entry point — so a repo checkout (`uv run horus`) opens a cockpit
    running the *checkout*, not whatever version happens to be installed
    globally.
    """
    if (script := shutil.which("horus")) is not None:
        return [script, "tui"]
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

    error = _attach_cockpit(host, existing)
    return (2, error) if error else (0, "")


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
        for pane in listed:
            workspace = herdr._payload(
                herdr._run("workspace", "get", pane.get("workspace_id", "")),
            ).get("workspace", {})
            if workspace.get("label") == COCKPIT_REF:
                return pane.get("pane_id")
        return None
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

        created = herdr._run("workspace", "create", "--label", COCKPIT_REF, "--no-focus")
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
