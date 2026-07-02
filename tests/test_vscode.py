"""Tests for the static VS Code task projection (`horus vscode-task`)."""

from __future__ import annotations

from horus import vscode
from horus.cli import main


def test_write_tasks_creates_file(tmp_path):
    action = vscode.write_tasks(tmp_path)

    assert action.status == "created"
    text = vscode.tasks_path(tmp_path).read_text(encoding="utf-8")
    assert text == vscode.TASKS_JSON
    # The tasks are generic and secret-free: continuity comes from `horus resume`
    # at run time, agents run ambient (no account env), nothing machine-specific.
    assert 'claude \\"$(horus resume)\\"' in text
    assert 'codex \\"$(horus resume)\\"' in text
    assert "CLAUDE_CONFIG_DIR" not in text and "CODEX_HOME" not in text


def test_write_tasks_idempotent_on_own_file(tmp_path):
    vscode.write_tasks(tmp_path)
    action = vscode.write_tasks(tmp_path)
    assert action.status == "up-to-date"


def test_write_tasks_never_touches_foreign_file(tmp_path):
    path = vscode.tasks_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"version": "2.0.0", "tasks": []}', encoding="utf-8")

    action = vscode.write_tasks(tmp_path)

    assert action.status == "kept"
    assert path.read_text(encoding="utf-8") == '{"version": "2.0.0", "tasks": []}'


def test_remove_tasks_only_removes_byte_identical_file(tmp_path):
    vscode.write_tasks(tmp_path)
    action = vscode.remove_tasks(tmp_path)
    assert action.status == "removed"
    assert not vscode.tasks_path(tmp_path).exists()
    assert not (tmp_path / ".vscode").exists()  # emptied dir pruned

    # An edited file is the user's now.
    path = vscode.tasks_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(vscode.TASKS_JSON + "\n// user edit", encoding="utf-8")
    action = vscode.remove_tasks(tmp_path)
    assert action.status == "kept"
    assert path.exists()


def test_remove_tasks_preserves_sibling_vscode_files(tmp_path):
    vscode.write_tasks(tmp_path)
    settings = tmp_path / ".vscode" / "settings.json"
    settings.write_text("{}", encoding="utf-8")

    vscode.remove_tasks(tmp_path)

    assert settings.exists()
    assert (tmp_path / ".vscode").is_dir()


def test_cli_vscode_task_requires_horus_dir(tmp_path, capsys):
    rc = main(["vscode-task", "--path", str(tmp_path)])
    assert rc == 1
    assert "horus init" in capsys.readouterr().out


def test_cli_vscode_task_creates_and_reports(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    from horus import initialize
    initialize.init_project(tmp_path, assume_yes=True)
    capsys.readouterr()

    rc = main(["vscode-task", "--path", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 0
    assert "[created]" in out and "Ctrl+Shift+B" in out
    assert vscode.tasks_path(tmp_path).exists()


def test_cli_vscode_task_prints_snippet_for_foreign_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    from horus import initialize
    initialize.init_project(tmp_path, assume_yes=True)
    path = vscode.tasks_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    capsys.readouterr()

    rc = main(["vscode-task", "--path", str(tmp_path)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "[kept]" in out and "Horus: resume Claude session" in out
    assert path.read_text(encoding="utf-8") == "{}"


def test_offboard_removes_own_tasks_but_keeps_edited(tmp_path, monkeypatch):
    from horus import offboard
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    vscode.write_tasks(tmp_path)

    dry = offboard.offboard_project(tmp_path, apply=False)
    assert any(a.status == "would-remove" and "tasks.json" in a.message for a in dry)
    assert vscode.tasks_path(tmp_path).exists()  # dry run touches nothing

    done = offboard.offboard_project(tmp_path, apply=True)
    assert any(a.status == "removed" and "tasks.json" in a.message for a in done)
    assert not vscode.tasks_path(tmp_path).exists()

    # Edited file: neither reported nor removed.
    path = vscode.tasks_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    done = offboard.offboard_project(tmp_path, apply=True)
    assert not any("tasks.json" in a.message for a in done)
    assert path.exists()
