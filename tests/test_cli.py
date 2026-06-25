"""Integration tests driving commands through the CLI entry point."""

from horus.cli import main
from horus.instructions import check_drift


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_session_new_creates_file_from_template(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])

    rc = main(["session", "new", "My Title", "--path", str(tmp_path)])
    assert rc == 0
    files = list((tmp_path / ".horus" / "sessions").glob("*-my-title.md"))
    assert files, "session file not created"
    text = files[0].read_text(encoding="utf-8")
    assert "My Title" in text
    assert "status: in-progress" in text


def test_session_new_refuses_without_horus(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["session", "new", "X", "--path", str(tmp_path)]) == 1


def test_close_runs_and_returns_status(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["close", "--path", str(tmp_path)]) in (0, 1)


def test_reconcile_cli_resolves_drift(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])

    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        claude.read_text(encoding="utf-8").replace("project continuity", "DRIFTED"),
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    assert check_drift(
        agents.read_text(encoding="utf-8"), "AGENTS.md",
        claude.read_text(encoding="utf-8"), "CLAUDE.md",
    ).status == "drift"

    assert main(["reconcile", "instructions", "--path", str(tmp_path)]) == 0
    assert check_drift(
        agents.read_text(encoding="utf-8"), "AGENTS.md",
        claude.read_text(encoding="utf-8"), "CLAUDE.md",
    ).status == "aligned"


def test_consolidate_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["consolidate", "--path", str(tmp_path)]) == 0


def test_distill_history_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["distill-history", "--path", str(tmp_path)]) == 0


def test_infer_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["infer", "--path", str(tmp_path)]) == 0


def test_skill_install_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    assert not (tmp_path / ".claude").exists()  # --no-skills opted out at init
    assert main(["skill", "install", "--path", str(tmp_path)]) == 0
    assert (tmp_path / ".claude" / "skills" / "horus-consolidate" / "SKILL.md").exists()


def test_forget_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["forget", str(tmp_path)]) == 0
    assert main(["forget", str(tmp_path)]) == 1  # already gone
