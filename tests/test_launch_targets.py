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


# --- in-app terminal panel is embedded where launches land -------------------
import types


def _fake_term(tid="term-abc", title="claude", alive=True):
    return types.SimpleNamespace(term_id=tid, title=title, alive=alive)


def test_terminal_section_empty_without_terminals():
    assert dashboard._terminal_section(None) == ""
    assert dashboard._terminal_section([]) == ""


def test_terminal_section_embeds_xterm_and_pane_for_live_terminal():
    section = dashboard._terminal_section([_fake_term("term-abc")])
    assert "/assets/xterm/xterm.js" in section          # assets loaded
    assert "horusAttachTerm" in section                 # attach JS present
    assert "data-tid='term-abc'" in section             # a pane for the PTY
    assert "EventSource('/pty/stream" in section          # SSE wiring
    # the bootstrap reads ?tab= to activate the launched session
    assert "URLSearchParams(location.search).get('tab')" in section
