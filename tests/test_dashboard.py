"""Tests for dashboard data gathering and HTML rendering (no socket)."""

from horus import dashboard, initialize


def _init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_load_project_reads_frontmatter_and_health(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    data = dashboard.load_project(str(tmp_path))
    assert data["exists"] is True
    assert data["status"] == "planning"
    assert isinstance(data["findings"], list) and data["findings"]


def test_gather_and_index_render(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)

    projects = dashboard.gather_projects()
    assert len(projects) == 1
    html_out = dashboard.render_index(projects)
    assert "demo" in html_out
    assert "/project?i=0" in html_out


def test_index_empty_state(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    html_out = dashboard.render_index([])
    assert "No projects registered" in html_out


def test_project_detail_renders_sections(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    data = dashboard.load_project(str(tmp_path))
    html_out = dashboard.render_project(data)
    assert "Continuity health" in html_out
    assert "Roadmap" in html_out


def test_next_step_and_latest_surface(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    # Roadmap template has an open "First task." -> it should be the next step.
    data = dashboard.load_project(str(tmp_path))
    assert data["next_step"]["text"] == "First task."
    assert data["progress"]["total"] >= 1

    # Add a session summary; it should become the "latest".
    sessions = tmp_path / ".horus" / "sessions"
    (sessions / "2026-06-25-newer.md").write_text(
        '---\ndate: 2026-06-25\nsummary: "Newer change"\n---\n# x\n', encoding="utf-8"
    )
    (sessions / "2026-06-24-older.md").write_text(
        '---\ndate: 2026-06-24\nsummary: "Older change"\n---\n# x\n', encoding="utf-8"
    )
    data = dashboard.load_project(str(tmp_path))
    assert data["latest"]["summary"] == "Newer change"

    html_out = dashboard.render_index([data])
    assert "NEXT" in html_out
    assert "First task." in html_out
    assert "Newer change" in html_out


def test_completed_roadmap_shows_complete(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    # Replace roadmap body with all-done tasks.
    roadmap_md = tmp_path / ".horus" / "roadmap.md"
    roadmap_md.write_text(
        "---\nstatus: active\ncurrent_focus: \"x\"\n---\n# Roadmap\n\n- [x] all done\n",
        encoding="utf-8",
    )
    data = dashboard.load_project(str(tmp_path))
    assert data["next_step"] is None
    assert "roadmap complete" in dashboard.render_project(data)
