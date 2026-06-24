"""Tests for deterministic project-state inference and its init integration."""

from horus import infer, initialize, templates


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_infer_title_description_and_tasks(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Cool Project\n\nA tool that does cool things across many files.\n\n"
        "## Roadmap\n\n- [x] bootstrap\n- [ ] add widget\n- write docs\n",
        encoding="utf-8",
    )
    inf = infer.infer(tmp_path)
    assert inf.title == "Cool Project"
    assert "cool things" in inf.description
    texts = [t.text for t in inf.tasks]
    assert "bootstrap" in texts and "add widget" in texts
    assert "write docs" in texts  # plain bullet under a Roadmap heading
    assert inf.current_focus == "add widget"  # first open task


def test_infer_emoji_status_bullets(tmp_path):
    (tmp_path / "PROJECT_STATUS.md").write_text(
        "# Status\n\n"
        "## Open items\n\n"
        "- ✅ shipped the ingester\n"
        "- ⬜ migrate remaining dims\n"
        "- 🚧 prod metadata flip in progress\n",
        encoding="utf-8",
    )
    inf = infer.infer(tmp_path)
    by_text = {t.text: t.state for t in inf.tasks}
    assert by_text.get("shipped the ingester") == "done"
    assert by_text.get("migrate remaining dims") == "todo"
    assert by_text.get("prod metadata flip in progress") == "partial"
    # Focus = first actionable (partial preferred), not the done item.
    assert inf.current_focus == "prod metadata flip in progress"


def test_infer_strips_managed_block(tmp_path):
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        "# Guide\n\nReal project description here.\n\n"
        + templates.shared_block("AGENTS.md")
        + "\n",
        encoding="utf-8",
    )
    inf = infer.infer(tmp_path)
    assert "Real project description" in inf.description
    # Nothing from the managed block should leak in as a task.
    assert all("`.horus/`" not in t.text for t in inf.tasks)


def test_infer_status_from_status_line(tmp_path):
    (tmp_path / "STATUS.md").write_text("status: active\n\n# Status\n\nGoing well.\n", encoding="utf-8")
    assert infer.infer(tmp_path).status == "active"


def test_infer_empty_project(tmp_path):
    inf = infer.infer(tmp_path)
    assert inf.title == tmp_path.name
    assert not inf.has_content()
    assert inf.status == "planning"


def test_init_populates_from_sources(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text(
        "# Seeded\n\nDescription mined by init.\n\n## TODO\n\n- [ ] ship it\n",
        encoding="utf-8",
    )
    actions = initialize.init_project(tmp_path, assume_yes=True)
    assert any(a.status == "info" and "inferred" in a.message for a in actions)

    project_md = (tmp_path / ".horus" / "project.md").read_text(encoding="utf-8")
    roadmap_md = (tmp_path / ".horus" / "roadmap.md").read_text(encoding="utf-8")
    assert "Description mined by init." in project_md
    assert "Seeded by Horus from" in project_md
    assert "- [ ] ship it" in roadmap_md
    assert "First task." not in roadmap_md  # placeholder replaced


def test_init_no_infer_uses_placeholders(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    (tmp_path / "README.md").write_text("# X\n\nShould be ignored.\n", encoding="utf-8")
    initialize.init_project(tmp_path, assume_yes=True, infer_sources=False)
    project_md = (tmp_path / ".horus" / "project.md").read_text(encoding="utf-8")
    assert "One-paragraph description" in project_md
    assert "Should be ignored." not in project_md


def test_is_placeholder(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True, infer_sources=False)
    assert infer.is_placeholder(tmp_path / ".horus" / "project.md")
    (tmp_path / ".horus" / "project.md").write_text(
        '---\ncurrent_focus: "Real focus"\n---\n# Real\n\nReal content.\n', encoding="utf-8"
    )
    assert not infer.is_placeholder(tmp_path / ".horus" / "project.md")
