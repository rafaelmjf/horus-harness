"""Tests for dashboard data gathering and HTML rendering (no socket)."""

import os
from pathlib import Path

from horus import dashboard, initialize, launcher
from horus.registry import Registry, SessionRecord


def _init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_render_sessions_card_empty():
    html = dashboard.render_sessions_card([])
    assert "Live sessions" in html and "No tracked agent sessions" in html


def test_render_sessions_card_lists_records():
    rec = SessionRecord(
        session_id="abcdef123456", agent="claude", project="/home/u/myproj",
        account="work", pid=4321, status="running", updated_at="2026-06-25T22:00:00",
    )
    html = dashboard.render_sessions_card([rec])
    assert "running" in html and "claude" in html and "work" in html
    assert "myproj" in html            # project basename, not the full path
    assert "abcdef12" in html          # short session id
    assert "health-ok" in html         # running -> green dot


def test_gather_sessions_reconciles(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    reg = Registry.default()
    reg.upsert(SessionRecord(session_id="x", agent="claude", project="/p", pid=None, status="running"))
    records = dashboard.gather_sessions()
    assert len(records) == 1 and records[0].status == "orphaned"  # pid-less running -> orphaned


def test_render_index_includes_sessions_card(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    page = dashboard.render_index([], dashboard.gather_sessions())
    assert "Live sessions" in page


def test_control_usage_color_and_ring_by_threshold():
    assert dashboard._usage_color(95) == "#f08a8a"
    assert dashboard._usage_color(75) == "#e6c35c"
    assert dashboard._usage_color(10) == "#57d39a"
    assert "stroke-dasharray='60 100'" in dashboard._ring(60.4)
    assert ">--<" in dashboard._ring(None)  # unknown usage -> gray, no fill


def test_control_tab_offline_empty_states(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    # No credentials under tmp HOME -> no network, empty accounts; no registry -> no live cards.
    accounts = dashboard.gather_accounts()
    assert accounts == []
    page = dashboard.render_control([], accounts, dashboard.gather_sessions())
    assert "No Claude login detected" in page
    assert "No live sessions" in page
    assert "class=\"active\"" in page  # Control nav highlighted


def test_control_live_session_card_uses_account_usage(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    reg = Registry.default()
    reg.upsert(SessionRecord(
        session_id="abcdef123456", agent="claude", project=str(proj),
        account="work", pid=os.getpid(), status="running",  # live pid -> stays "running"
    ))
    accounts = [{"alias": "work", "five_pct": 62.0, "week_pct": 20.0, "five_reset": "2026-06-26 18:00"}]
    records = dashboard.gather_sessions()
    page = dashboard.render_control(dashboard.gather_projects(), accounts, records)
    # Account ring + the live card's bar both reflect the real percent.
    assert "demo" in page and "work" in page
    assert "5h limit 62%" in page          # session card bar label from the matched account
    assert "horus open" in page            # launch command in the projects panel
    assert "1 live" in page                # header live-session indicator
    assert "horus focus abcdef12" in page          # raise-the-running-window shortcut
    assert "claude --resume abcdef123456" in page  # reopen-in-a-new-window shortcut

    # The indicator rides in the header, so it shows on the index too.
    idx = dashboard.render_index(dashboard.gather_projects(), records)
    assert "1 live" in idx and "class='live-badge'" in idx


def test_live_indicator_absent_when_nothing_running(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    assert dashboard._live_count([]) == 0
    # The CSS rule mentions .live-badge; the rendered anchor does not exist with no live sessions.
    assert "class='live-badge'" not in dashboard.render_index([], [])


def test_control_session_card_only_when_running(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    reg = Registry.default()
    reg.upsert(SessionRecord(
        session_id="dead0001", agent="claude", project="/p",
        account="work", pid=None, status="running",  # pid-less -> reconciles to orphaned
    ))
    page = dashboard.render_control([], [], dashboard.gather_sessions())
    assert "No live sessions" in page  # orphaned is not "live"


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


def test_control_tab_renders_launch_controls(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    accounts = [{"alias": "work", "five_pct": 60.0, "week_pct": 10.0, "five_reset": None}]
    page = dashboard.render_control(dashboard.gather_projects(), accounts, [])

    # Project play -> a POST form with account select + fresh/resume radios.
    assert "method='post' action='/launch'" in page
    assert "name='mode' value='fresh'" in page and "name='mode' value='resume'" in page
    assert "<select name='account'>" in page and ">work</option>" in page
    # Account row -> a one-click fresh-session button.
    assert "+ session" in page
    # Copy-the-command path is still offered as a secondary option.
    assert "horus open" in page


def test_launch_notice_banner():
    ok = dashboard._launch_notice({"launched": ["abcd1234"]})
    assert "Launched session" in ok and "abcd1234" in ok and "banner ok" in ok
    err = dashboard._launch_notice({"error": ["unknown account"]})
    assert "Launch failed" in err and "unknown account" in err and "banner err" in err
    assert dashboard._launch_notice({}) == ""


def test_process_launch_fresh_by_project_index(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"], captured["cwd"] = argv, cwd
        return 555

    monkeypatch.setattr(launcher, "open_terminal", fake_open)

    query = dashboard.process_launch(
        {"project": "0", "mode": "fresh", "agent": "fake"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query.startswith("launched=")
    assert str(proj) == str(captured["cwd"])
    assert captured["argv"][-1] != ""  # fresh: no injected prompt
    recs = Registry.default().all()
    assert len(recs) == 1 and recs[0].status == "running"


def test_process_launch_resume_injects_continuity_prompt(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"] = argv
        return 7

    monkeypatch.setattr(launcher, "open_terminal", fake_open)

    query = dashboard.process_launch(
        {"project": "0", "mode": "resume", "agent": "fake"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query.startswith("launched=")
    # The resume prompt (project name + read-.horus instruction) is seeded into the session.
    assert "demo" in captured["argv"][-1] and ".horus/" in captured["argv"][-1]


def test_process_launch_rejects_unknown_project_and_account(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    assert dashboard.process_launch({"project": "9"}, projects=[], known_aliases=set()) == "error=unknown+project"
    assert dashboard.process_launch(
        {"project": "", "account": "ghost"}, projects=[], known_aliases={"work"}
    ) == "error=unknown+account"


def test_process_launch_account_only_uses_home_dir(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["cwd"] = cwd
        return 8

    monkeypatch.setattr(launcher, "open_terminal", fake_open)

    query = dashboard.process_launch(
        {"account": "work", "mode": "fresh", "agent": "fake"},
        projects=[], known_aliases={"work"},
    )
    assert query.startswith("launched=")
    assert Path(captured["cwd"]) == (tmp_path / "home").resolve()  # account-only -> home dir


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
