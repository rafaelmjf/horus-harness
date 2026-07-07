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
