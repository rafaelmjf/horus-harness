"""Launch destination options adapt to whether a desktop session exists.

Headless hosts (the hosted dashboard under systemd) must default to the in-app
terminal and hide native-terminal / VS Code targets, which can only open on a
desktop. Regression test for: a fresh session over the hosted dashboard failed
with "no graphical display detected" because the form only offered window/vscode.
"""

from horus import dashboard, launcher


def test_has_display_false_without_env(monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert launcher.has_display() is False


def test_has_display_true_with_x11(monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":0")
    assert launcher.has_display() is True


def test_target_options_headless_only_in_app(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: False)
    html = dashboard._launch_target_options()
    assert "value='app'" in html            # in-app terminal always offered
    assert "value='window'" not in html      # native terminal hidden headless
    assert "value='vscode'" not in html      # VS Code hidden headless
    # app is first -> the default selected option
    assert html.strip().startswith("<option value='app'")


def test_target_options_desktop_offers_all(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: True)
    html = dashboard._launch_target_options()
    assert "value='app'" in html and "value='window'" in html and "value='vscode'" in html


def test_project_form_defaults_to_in_app_when_headless(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: False)
    form = dashboard._project_launch_form(0, {"path": "/p", "name": "p"}, [])
    assert "In-app terminal" in form
    assert "Native terminal" not in form


def test_account_quick_button_uses_app_target_when_headless(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: False)
    html = dashboard._account_launch_form("work")
    assert "name='target' value='app'" in html


def test_account_quick_button_uses_window_target_on_desktop(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: True)
    html = dashboard._account_launch_form("work")
    assert "name='target' value='window'" in html


# --- project/index show a compact link, not a duplicate terminal -------------
import types


def _fake_term(tid="term-abc", title="claude", alive=True):
    return types.SimpleNamespace(term_id=tid, title=title, alive=alive)


def test_terminal_section_empty_without_live_terminals():
    assert dashboard._terminal_section(None) == ""
    assert dashboard._terminal_section([]) == ""
    # All-dead terminals also render nothing — there is no live session to link to.
    assert dashboard._terminal_section([_fake_term("t", alive=False)]) == ""


def test_terminal_section_is_a_compact_link_not_an_embedded_terminal():
    section = dashboard._terminal_section([_fake_term("term-abc"), _fake_term("term-def")])
    # The Sessions cockpit is the single terminal host: project/index only link over.
    assert "href='/sessions'" in section                # a link across, not a viewer
    assert "<b>2</b>" in section                          # counts the live terminals
    assert "live-sessions-link" in section
    # Crucially, it must NOT embed xterm assets or open an SSE stream (the old
    # duplicate-viewer bug): those belong only to /sessions.
    assert "/assets/xterm/xterm.js" not in section
    assert "EventSource('/pty/stream" not in section
    assert "horusAttachTerm" not in section


# --- Sessions cockpit (revived Control tab) ----------------------------------

def test_nav_includes_sessions_link(monkeypatch):
    monkeypatch.setattr(dashboard.pty_host.host, "terminals", lambda: [])
    nav = dashboard._nav("projects")
    assert "href='/sessions'" in nav and ">Sessions" in nav


def test_nav_sessions_badge_counts_open_terminals(monkeypatch):
    monkeypatch.setattr(dashboard.pty_host.host, "terminals",
                        lambda: [_fake_term("a", alive=True), _fake_term("b", alive=True), _fake_term("c", alive=False)])
    nav = dashboard._nav("sessions")
    assert ">2<" in nav  # badge counts only the 2 alive terminals
    assert 'class="active"' in nav  # Sessions highlighted when active


def test_render_sessions_shows_cockpit_with_open_terminal():
    page = dashboard.render_sessions([_fake_term("term-xyz", title="claude")], [])
    assert "/assets/xterm/xterm.js" in page       # cockpit xterm assets
    assert "data-tid='term-xyz'" in page          # a sub-tab/pane for the session
    assert "horusAttachTerm" in page
    assert ">Sessions<" in page                    # page heading


def test_render_sessions_empty_state():
    page = dashboard.render_sessions([], [])
    assert "No in-app terminals yet" in page       # empty cockpit hint
    assert "No tracked agent sessions" in page      # empty registry list
