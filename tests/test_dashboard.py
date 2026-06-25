"""Tests for dashboard data gathering and HTML rendering (no socket)."""

from horus import dashboard, initialize


def _init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_dashboard_server_is_single_instance():
    # The leak fix: only one dashboard may hold a port. Default ThreadingHTTPServer
    # allows address reuse (multiple binds on Windows); ours must not.
    assert dashboard._SingleInstanceServer.allow_reuse_address is False


def test_serve_refuses_when_port_already_bound(monkeypatch, capsys):
    class Taken(dashboard.ThreadingHTTPServer):
        def __init__(self, *a, **k):
            raise OSError("address in use")

    monkeypatch.setattr(dashboard, "_SingleInstanceServer", Taken)
    dashboard.serve(port=8765)  # must not raise
    out = capsys.readouterr().out
    assert "already running" in out


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


def test_next_action_and_latest_surface(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    # The single NEXT is agent-authored (roadmap.md next_action), not inferred.
    (tmp_path / ".horus" / "roadmap.md").write_text(
        '---\nstatus: active\nnext_action: "Wire the adapter contract"\n---\n'
        "# Roadmap\n\n- [ ] First task.\n",
        encoding="utf-8",
    )
    sessions = tmp_path / ".horus" / "sessions"
    (sessions / "2026-06-25-newer.md").write_text(
        '---\ndate: 2026-06-25\nsummary: "Newer change"\n---\n# x\n', encoding="utf-8"
    )
    (sessions / "2026-06-24-older.md").write_text(
        '---\ndate: 2026-06-24\nsummary: "Older change"\n---\n# x\n', encoding="utf-8"
    )
    data = dashboard.load_project(str(tmp_path))
    assert data["next_action"] == "Wire the adapter contract"
    assert data["latest"]["summary"] == "Newer change"

    html_out = dashboard.render_index([data])
    assert "NEXT" in html_out
    assert "Wire the adapter contract" in html_out  # authored, highlighted
    assert "Newer change" in html_out


def test_resume_prompt_prefers_written_then_falls_back(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    data = dashboard.load_project(str(tmp_path))

    # No next_prompt set -> generic paste-able fallback naming the project + next step.
    fallback = dashboard._resume_prompt_text(data)
    assert tmp_path.name in fallback and ".horus/" in fallback
    assert "horus session new" not in fallback  # not a CLI trigger

    # Authored next_prompt wins, and renders with a copy button.
    data["next_prompt"] = "Paste me into Claude to resume."
    assert dashboard._resume_prompt_text(data) == "Paste me into Claude to resume."
    idx = dashboard.render_index([data])
    assert "Resume prompt" in idx and "horusCopy(this)" in idx and "Paste me into Claude" in idx


def test_remaining_items_render_as_checkbox_list(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "roadmap.md").write_text(
        "---\nstatus: active\nnext_action: \"doing alpha\"\n---\n# Roadmap\n\n## Now\n\n"
        "- [~] doing alpha\n- [ ] open beta\n- [ ] open gamma\n- [ ] open delta\n- [x] done eps\n",
        encoding="utf-8",
    )
    data = dashboard.load_project(str(tmp_path))
    html_out = dashboard.render_index([data])
    assert "doing alpha" in html_out  # authored NEXT highlighted
    assert html_out.count("&#9744;") >= 3  # remaining open items as empty checkboxes
    assert "done eps" not in html_out  # completed excluded


def test_progress_links_to_roadmap_breakdown(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    roadmap_md = tmp_path / ".horus" / "roadmap.md"
    roadmap_md.write_text(
        "---\nstatus: active\ncurrent_focus: \"x\"\n---\n# Roadmap\n\n"
        "## Now\n\n- [x] shipped\n- [ ] todo one\n- [~] doing two\n",
        encoding="utf-8",
    )
    data = dashboard.load_project(str(tmp_path))

    # Index card: progress count links through to the detail roadmap anchor.
    idx = dashboard.render_index([data])
    assert "/project?i=0#roadmap" in idx

    # Detail: anchored roadmap with grouped open/completed breakdown.
    det = dashboard.render_project(data)
    assert "id='roadmap'" in det
    assert "Open &amp; in progress (2)" in det
    assert "Completed (1)" in det
    assert "todo one" in det and "doing two" in det and "shipped" in det


def test_dashboard_surfaces_features_and_history(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "features.md").write_text(
        "---\nstatus: active\n---\n# Features\n\n## Shipped\n\n"
        "| Capability | Since | Notes |\n|---|---|---|\n| Widget engine | 0.1 | core |\n",
        encoding="utf-8",
    )
    (tmp_path / ".horus" / "history.md").write_text(
        "---\nstatus: active\n---\n# History\n\n## the big outage\n\nlesson learned.\n",
        encoding="utf-8",
    )
    data = dashboard.load_project(str(tmp_path))
    assert data["feature_counts"]["shipped"] == 1

    det = dashboard.render_project(data)
    assert "id='features'" in det and "Widget engine" in det
    assert "id='history'" in det and "the big outage" in det
    assert "<table>" in det  # capability ledger rendered as a table

    idx = dashboard.render_index([data])
    # New column layout: features show as named buckets (Idea / In progress / Shipped).
    assert "Main features" in idx and "Widget engine" in idx
    assert "Last session summary" in idx


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
    assert data["next_action"] == ""
    assert "roadmap complete" in dashboard.render_project(data)
