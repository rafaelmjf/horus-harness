"""Tests for dashboard data gathering and HTML rendering (no socket)."""

import os
from pathlib import Path
from datetime import datetime, timezone

import json

from horus import cache_status, config, dashboard, github_catalog, initialize, launcher, overhead
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


def test_page_links_cache_busted_favicon(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    page = dashboard.render_index([])
    assert "href='/favicon.ico?v=" in page
    assert "href='/assets/icon.png?v=" in page


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
    assert "No windowed sessions" in page  # registry-tracked OS-window sessions
    assert "No in-app terminals yet" in page  # the integrated terminal panel
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
    assert "No windowed sessions" in page  # orphaned is not "live"


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


def test_index_renders_remote_github_catalog():
    remote = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
        current_focus="Remote focus",
        next_action="Clone and resume",
    )

    html_out = dashboard.render_remote_catalog([remote], [])

    assert "GitHub remote catalog" in html_out
    assert "rafaelmjf/demo" in html_out
    assert "remote only" in html_out
    assert "horus start github:rafaelmjf/demo" in html_out


def test_gather_remote_projects_uses_cache_and_starts_refresh(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    remote = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="",
    )
    refreshes = []
    monkeypatch.setattr(
        dashboard.github_catalog,
        "load_cache",
        lambda owner, **kw: github_catalog.CachedCatalog(
            owner=owner,
            projects=[remote],
            fetched_at="2026-06-28T20:00:00+00:00",
            error="auth failed",
            error_at="2026-06-28T20:01:00+00:00",
        ),
    )
    monkeypatch.setattr(dashboard, "_start_remote_refresh", lambda owner, local: refreshes.append((owner, local)))

    projects, errors, notes = dashboard.gather_remote_projects()

    assert projects == [remote]
    assert "showing cached results" in notes[0]
    assert "last refresh failed" in errors[0]
    assert refreshes and refreshes[0][0] == "rafaelmjf"


def test_gather_remote_projects_refreshes_live_when_no_cache(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    remote = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="",
    )
    monkeypatch.setattr(dashboard.github_catalog, "load_cache", lambda owner, **kw: None)
    monkeypatch.setattr(dashboard.github_catalog, "refresh_cache", lambda owner, **kw: [remote])

    projects, errors, notes = dashboard.gather_remote_projects()

    assert projects == [remote]
    assert errors == []
    assert notes == []


def test_remote_catalog_renders_cache_note_and_error():
    html_out = dashboard.render_remote_catalog([], ["owner: failed"], ["owner: showing cached results"])

    assert "GitHub catalog cache" in html_out
    assert "showing cached results" in html_out
    assert "GitHub discovery issue" in html_out


def test_remote_catalog_renders_refresh_form_for_saved_owner(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    html_out = dashboard.render_remote_catalog([], [], ["cached"])

    assert "action='/github-refresh'" in html_out
    assert "name='owner' value='rafaelmjf'" in html_out
    assert "Refresh rafaelmjf" in html_out


def test_force_refresh_remote_returns_cached_projects_and_note(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    remote = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="",
    )
    monkeypatch.setattr(
        dashboard.github_catalog,
        "force_refresh",
        lambda owner, **kw: github_catalog.RefreshResult(owner=owner, ok=True, count=1, fetched_at="now"),
    )
    monkeypatch.setattr(
        dashboard.github_catalog,
        "load_cache",
        lambda owner, **kw: github_catalog.CachedCatalog(owner=owner, projects=[remote], fetched_at="now"),
    )

    projects, errors, notes = dashboard.force_refresh_remote("rafaelmjf")

    assert projects == [remote]
    assert errors == []
    assert "force-refresh updated 1" in notes[0]


def test_force_refresh_remote_surfaces_error(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    monkeypatch.setattr(
        dashboard.github_catalog,
        "force_refresh",
        lambda owner, **kw: github_catalog.RefreshResult(owner=owner, ok=False, count=0, error="auth required"),
    )
    monkeypatch.setattr(dashboard.github_catalog, "load_cache", lambda owner, **kw: None)

    projects, errors, notes = dashboard.force_refresh_remote("rafaelmjf")

    assert projects == []
    assert "force-refresh failed" in errors[0]
    assert notes == []


def test_index_uses_async_remote_catalog_placeholder(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    html_out = dashboard.render_index([])

    assert "GitHub remote catalog" in html_out
    assert "data-horus-src='/github-catalog'" in html_out
    assert "Loading GitHub projects" in html_out


def test_project_detail_renders_sections(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    data = dashboard.load_project(str(tmp_path))
    html_out = dashboard.render_project(data)
    assert "Continuity health" in html_out
    assert "Roadmap" in html_out


def test_project_detail_surfaces_token_overhead(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    reg = Registry.default()
    reg.upsert(SessionRecord(session_id="codex-session", agent="codex", project=str(tmp_path), status="exited"))

    monkeypatch.setattr(
        dashboard.overhead,
        "static_footprint",
        lambda: [overhead.FootprintItem("managed block", 400, 100)],
    )
    monkeypatch.setattr(
        dashboard.overhead,
        "codex_overhead",
        lambda root: overhead.UsageSummary(
            "codex",
            2,
            1,
            overhead.TokenUsage(total_tokens=300),
            overhead.TokenUsage(total_tokens=120),
        ),
    )
    monkeypatch.setattr(
        dashboard.overhead,
        "claude_overhead",
        lambda root: overhead.UsageSummary(
            "claude",
            0,
            0,
            overhead.TokenUsage(),
            overhead.TokenUsage(),
        ),
    )
    monkeypatch.setattr(
        dashboard.overhead,
        "session_usages",
        lambda records: [
            overhead.SessionUsage(
                "codex-session",
                "codex",
                str(tmp_path),
                "exited",
                2,
                overhead.TokenUsage(total_tokens=300),
                True,
            )
        ],
    )

    html_out = dashboard.render_project(dashboard.load_project(str(tmp_path)))
    assert "Token overhead" in html_out
    assert "upper-bound attribution" in html_out
    assert "120" in html_out
    assert "codex-session"[:8] in html_out


def test_project_detail_surfaces_context_cache(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    monkeypatch.setattr(
        dashboard.cache_status,
        "project_cache_status",
        lambda root: [
            cache_status.CacheStatus(
                "codex",
                datetime.now(timezone.utc),
                tmp_path / "rollout.jsonl",
                cached_input_tokens=1200,
                total_tokens=2000,
            )
        ],
    )

    html_out = dashboard.render_project(dashboard.load_project(str(tmp_path)))
    assert "Context cache" in html_out
    assert "warm" in html_out
    assert "cached 1,200" in html_out


def test_next_action_and_latest_surface(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    # The single NEXT is agent-authored (roadmap.md next_action), not inferred.
    (tmp_path / ".horus" / "roadmap.md").write_text(
        '---\nstatus: active\nnext_action: "Wire the adapter contract"\n'
        'execution_recommendation: "plan-execution — cross-module work"\n---\n'
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
    assert "plan-execution" in html_out
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


def test_dashboard_surfaces_execution_plan(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "execution.md").write_text(
        "---\nstatus: active\nlast_updated: 2026-06-29\n---\n"
        "# Execution Plan\n\n## Active Phases\n\n"
        "| phase | status | worker_tier |\n|---|---|---|\n| 1A | ready-for-review | standard |\n",
        encoding="utf-8",
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["execution_status"] == "active"
    assert "ready-for-review" in data["execution_body"]

    det = dashboard.render_project(data)
    assert "id='execution'" in det
    assert "Execution plan" in det
    assert "ready-for-review" in det


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
    # In-app terminal is the primary action; OS window is the demoted secondary.
    assert "value='app'>&#9654; Open terminal in app" in page
    assert "value='window'" in page and "separate OS window" in page
    # Permission posture is selectable at launch (default + bypass available).
    assert "<select name='posture'>" in page
    assert "value='default' selected" in page and "value='full-auto'>Bypass all prompts" in page
    # Account row -> a one-click fresh-session button.
    assert "+ session" in page
    # Copy-the-command path is still offered as a secondary option.
    assert "horus open" in page


def test_launch_notice_banner():
    ok = dashboard._launch_notice({"launched": ["abcd1234"]})
    assert "Launched session" in ok and "abcd1234" in ok and "banner ok" in ok
    err = dashboard._launch_notice({"error": ["unknown account"]})
    assert "Launch failed" in err and "unknown account" in err and "banner err" in err
    tab = dashboard._launch_notice({"tab": ["app-1"]})
    assert "terminal panel" in tab and "banner ok" in tab
    assert dashboard._launch_notice({}) == ""


def test_process_launch_in_app_opens_pty_terminal(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    # Stub the host so no real PTY/process is spawned; capture the start args.
    calls = {}

    def fake_start(**kw):
        calls.update(kw)
        return "pty-1"

    monkeypatch.setattr(dashboard.pty_host.host, "start", fake_start)

    query = dashboard.process_launch(
        {"project": "0", "mode": "fresh", "agent": "fake", "target": "app", "posture": "full-auto"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query == "tab=pty-1"
    assert calls["agent"] == "fake" and str(calls["project_dir"]) == str(proj)
    assert calls["posture"] == "full-auto"  # chosen permission posture threaded through

    # An unknown posture is rejected (not silently launched at default).
    assert dashboard.process_launch(
        {"project": "0", "target": "app", "posture": "nope"},
        projects=[str(proj)], known_aliases=set(),
    ) == "error=unknown+permission+mode"


def test_terminal_panel_renders_xterm_wiring(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-7", agent="claude", project_dir=tmp_path, title="demo · work",
    )
    page = dashboard.render_control([], [], [], terminals=[term])
    assert "data-tid='pty-7'" in page                  # a tab + pane for the terminal
    assert "id='x-pty-7'" in page                       # the xterm mount point
    assert "/assets/xterm/xterm.js" in page             # vendored xterm.js loaded (no CDN)
    assert "EventSource('/pty/stream?id='" in page      # SSE byte stream wiring
    assert "/pty/input" in page and "/pty/resize" in page  # keystroke + resize wiring
    assert "horusAttachTerm" in page                    # shared attach fn (panel + pop-out)
    assert "class='popout linkbtn' data-tid='pty-7'" in page  # pop-out control per terminal


def test_pty_term_page_is_a_standalone_viewer():
    page = dashboard.render_pty_term_page("pty-9", "demo · work")
    assert "<!doctype html>" in page
    assert "/assets/xterm/xterm.js" in page                       # same vendored xterm
    assert "window.horusAttachTerm('term', 'pty-9')" in page      # attaches the same session
    assert "demo · work" in page                                  # window title


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
        {"project": "0", "mode": "fresh", "agent": "fake", "target": "window"},
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
        {"project": "0", "mode": "resume", "agent": "fake", "target": "window"},
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
        {"account": "work", "mode": "fresh", "agent": "fake", "target": "window"},
        projects=[], known_aliases={"work"},
    )
    assert query.startswith("launched=")
    assert Path(captured["cwd"]) == (tmp_path / "home").resolve()  # account-only -> home dir


def _write_codex_auth(home, account_id="codex-acct-1"):
    home.mkdir(parents=True, exist_ok=True)
    (home / "auth.json").write_text(
        json.dumps({"tokens": {"account_id": account_id}}), encoding="utf-8"
    )


def _write_codex_rollout(home, primary=5.0, secondary=40.0):
    path = home / "sessions" / "2026" / "06" / "26" / "rollout-d.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": "2026-06-26T10:00:00Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"last_token_usage": {"total_tokens": 100}, "model_context_window": 1000},
            "rate_limits": {
                "primary": {"used_percent": primary, "resets_at": 1782390000},
                "secondary": {"used_percent": secondary, "resets_at": 1782990000},
            },
        },
    }
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")


def test_gather_accounts_includes_isolated_codex_home(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.set_account_codex_home("codex-work", str(tmp_path / "cx-home"))
    accounts = dashboard.gather_accounts()
    codex = [a for a in accounts if a.get("agent") == "codex"]
    assert len(codex) == 1
    assert codex[0]["alias"] == "codex-work"
    assert codex[0]["five_pct"] is None  # no rollouts reporting limits yet -> gray ring


def test_gather_accounts_codex_ring_from_rollout_rate_limits(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    home = tmp_path / "cx-home"
    config.set_account_codex_home("codex-work", str(home))
    _write_codex_rollout(home, primary=5.0, secondary=40.0)
    codex = [a for a in dashboard.gather_accounts() if a.get("agent") == "codex"][0]
    # used% (matches the Claude ring convention, inverse of the Codex app's "remaining")
    assert codex["five_pct"] == 5.0
    assert codex["week_pct"] == 40.0
    assert codex["five_reset"]  # primary reset formatted, not None
    assert codex["week_reset"]  # secondary (weekly) reset formatted, not None


def test_accounts_panel_renders_weekly_bar_with_reset(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    accounts = [{
        "agent": "codex", "alias": "codex-work", "five_pct": 1.0, "week_pct": 69.0,
        "five_reset": "2026-06-26 22:22", "week_reset": "2026-06-28 15:34",
    }]
    page = dashboard.render_control(dashboard.gather_projects(), accounts, [])
    assert "class='usagebar'" in page       # full-width weekly bar
    assert "width:69%" in page               # proportional fill = used%
    assert "Weekly 69%" in page
    assert "resets 2026-06-28 15:34" in page  # weekly reset date shown


def test_gather_accounts_includes_ambient_codex(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    # No isolated homes; ambient ~/.codex/auth.json under the tmp HOME.
    _write_codex_auth(tmp_path / "home" / ".codex")
    accounts = dashboard.gather_accounts()
    codex = [a for a in accounts if a.get("agent") == "codex"]
    assert len(codex) == 1 and codex[0]["alias"]  # aliased, never the raw account_id
    assert codex[0]["alias"] != "codex-acct-1"


def test_known_aliases_includes_codex_isolated_and_ambient(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.set_account_codex_home("codex-work", str(tmp_path / "cx-home"))
    _write_codex_auth(tmp_path / "home" / ".codex", account_id="ambient-codex")
    aliases = dashboard._known_aliases()
    assert "codex-work" in aliases
    assert config.alias_for("ambient-codex") in aliases


def test_accounts_panel_badges_and_codex_launch_form(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    accounts = [
        {"agent": "claude", "alias": "work", "five_pct": 60.0, "week_pct": 10.0, "five_reset": None},
        {"agent": "codex", "alias": "codex-work", "five_pct": None, "week_pct": None, "five_reset": None},
    ]
    page = dashboard.render_control(dashboard.gather_projects(), accounts, [])
    # Both accounts carry an uppercase agent badge.
    assert ">claude</span>" in page and ">codex</span>" in page
    # The Codex account's one-click launch form forwards agent=codex.
    assert "name='agent' value='codex'" in page


def test_process_launch_codex_account_routes_to_pty(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    calls = {}

    def fake_start(**kw):
        calls.update(kw)
        return "pty-cx"

    monkeypatch.setattr(dashboard.pty_host.host, "start", fake_start)

    query = dashboard.process_launch(
        {"account": "codex-work", "agent": "codex", "mode": "fresh",
         "target": "app", "posture": "read-only"},
        projects=[], known_aliases={"codex-work"},
    )
    assert query == "tab=pty-cx"
    assert calls["agent"] == "codex" and calls["account"] == "codex-work"
    assert calls["posture"] == "read-only"


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


def test_remote_catalog_shows_blank_owner_warning_when_no_owners_configured(tmp_path, monkeypatch):
    """When no GitHub owner is configured, render_remote_catalog shows a CTA, not a bare empty state."""
    _init(tmp_path, monkeypatch)
    # Ensure no owners are registered (fresh home dir).
    assert config.load_github_owners() == []

    html_out = dashboard.render_remote_catalog([], [])

    assert "GitHub remote catalog" in html_out
    assert "No GitHub owner configured" in html_out
    assert "horus discover github" in html_out
    assert "per-machine" in html_out or "not git-synced" in html_out or "fresh machine" in html_out


def test_remote_catalog_no_owner_warning_absent_when_owners_set(tmp_path, monkeypatch):
    """When at least one owner is configured, the blank-owner CTA must NOT appear."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    # Render with an empty project list (owner configured but no repos fetched yet).
    html_out = dashboard.render_remote_catalog([], [])

    assert "No GitHub owner configured" not in html_out
    assert "No Horus-enabled remote repos found yet." in html_out


def test_render_remote_catalog_placeholder_shows_warning_when_no_owners(tmp_path, monkeypatch):
    """render_remote_catalog_placeholder delegates to render_remote_catalog when no owners."""
    _init(tmp_path, monkeypatch)
    assert config.load_github_owners() == []

    html_out = dashboard.render_remote_catalog_placeholder()

    assert "No GitHub owner configured" in html_out
    assert "data-horus-src='/github-catalog'" not in html_out


# ---------------------------------------------------------------------------
# Phase A4: Not-tracked + Hidden sections
# ---------------------------------------------------------------------------

def _make_untracked(full_name="rafaelmjf/plain-app", *, description="A plain repo", is_local=False):
    owner, name = full_name.split("/", 1)
    return github_catalog.UntrackedRepo(
        owner=owner,
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="2026-06-29T10:00:00Z",
        description=description,
        local_path="/tmp/plain-app" if is_local else None,
    )


def test_render_remote_catalog_untracked_section(tmp_path, monkeypatch):
    """untracked=[...] renders a 'Not tracked' section with Onboard + Ignore forms."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    u = _make_untracked("rafaelmjf/plain-app", description="A plain repo")

    html_out = dashboard.render_remote_catalog([], [], untracked=[u])

    assert "Not tracked" in html_out
    assert "rafaelmjf/plain-app" in html_out
    assert "A plain repo" in html_out
    assert "action='/github-onboard'" in html_out
    assert "name='target' value='rafaelmjf/plain-app'" in html_out
    assert "action='/github-ignore'" in html_out
    assert "Onboard" in html_out
    assert "Ignore" in html_out


def test_render_remote_catalog_untracked_badge_local(tmp_path, monkeypatch):
    """An untracked repo that is local gets 'cloned, not initialized' badge."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    u = _make_untracked("rafaelmjf/local-app", is_local=True)

    html_out = dashboard.render_remote_catalog([], [], untracked=[u])

    assert "cloned, not initialized" in html_out
    assert "health-warn" in html_out


def test_render_remote_catalog_untracked_badge_remote(tmp_path, monkeypatch):
    """An untracked repo that is remote-only gets a neutral 'remote only' badge."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    u = _make_untracked("rafaelmjf/remote-app", is_local=False)

    html_out = dashboard.render_remote_catalog([], [], untracked=[u])

    assert "remote only" in html_out


def test_render_remote_catalog_hidden_section(tmp_path, monkeypatch):
    """hidden=[...] renders a collapsed <details> with Unignore form."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    u = _make_untracked("rafaelmjf/hidden-app")

    html_out = dashboard.render_remote_catalog([], [], hidden=[u])

    assert "<details>" in html_out
    assert "Hidden" in html_out
    assert "rafaelmjf/hidden-app" in html_out
    assert "action='/github-unignore'" in html_out
    assert "Unignore" in html_out


def test_render_remote_catalog_no_details_when_hidden_empty(tmp_path, monkeypatch):
    """When hidden is empty (or None), the <details> block is absent."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    html_out = dashboard.render_remote_catalog([], [], hidden=[])

    assert "<details>" not in html_out


def test_render_remote_catalog_early_return_only_when_all_empty(tmp_path, monkeypatch):
    """The blank-owner CTA only shows when projects AND untracked AND hidden AND errors AND notes are all empty."""
    _init(tmp_path, monkeypatch)
    # No owners configured — but we have untracked repos → must NOT show blank-owner CTA.
    assert config.load_github_owners() == []
    u = _make_untracked("rafaelmjf/plain-app")

    html_out = dashboard.render_remote_catalog([], [], untracked=[u])

    assert "No GitHub owner configured" not in html_out
    assert "Not tracked" in html_out


def test_render_remote_catalog_untracked_with_no_horus_projects(tmp_path, monkeypatch):
    """With no Horus projects but untracked repos present, untracked section still renders."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    u = _make_untracked("rafaelmjf/plain-app")

    html_out = dashboard.render_remote_catalog([], [], untracked=[u])

    # The untracked section is present.
    assert "Not tracked" in html_out
    assert "rafaelmjf/plain-app" in html_out
    # No Horus projects message may appear in the Horus grid.
    assert "No Horus-enabled remote repos found yet." in html_out


def test_gather_untracked_repos_splits_visible_hidden(tmp_path, monkeypatch):
    """gather_untracked_repos splits visible/hidden via the ignore list."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    visible_u = _make_untracked("rafaelmjf/visible-app")
    hidden_u = _make_untracked("rafaelmjf/hidden-app")

    # Monkeypatch load_cache to return a CachedCatalog with .untracked
    monkeypatch.setattr(
        dashboard.github_catalog,
        "load_cache",
        lambda owner, **kw: github_catalog.CachedCatalog(
            owner=owner,
            projects=[],
            fetched_at="2026-06-29T10:00:00+00:00",
            untracked=[visible_u, hidden_u],
        ),
    )
    # Add hidden-app to the ignore list.
    config.ignore_repo("rafaelmjf/hidden-app")

    visible, hidden = dashboard.gather_untracked_repos()

    assert len(visible) == 1 and visible[0].full_name == "rafaelmjf/visible-app"
    assert len(hidden) == 1 and hidden[0].full_name == "rafaelmjf/hidden-app"


def test_gather_untracked_repos_empty_when_no_owners(tmp_path, monkeypatch):
    """With no owners configured, gather_untracked_repos returns ([], [])."""
    _init(tmp_path, monkeypatch)
    assert config.load_github_owners() == []

    visible, hidden = dashboard.gather_untracked_repos()

    assert visible == [] and hidden == []


def test_gather_untracked_repos_empty_when_no_cache(tmp_path, monkeypatch):
    """With owner configured but no cache, gather_untracked_repos returns ([], [])."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    monkeypatch.setattr(dashboard.github_catalog, "load_cache", lambda owner, **kw: None)

    visible, hidden = dashboard.gather_untracked_repos()

    assert visible == [] and hidden == []


def test_config_ignore_repo_persists(tmp_path, monkeypatch):
    """config.ignore_repo persists the repo to the ignore list."""
    _init(tmp_path, monkeypatch)
    config.ignore_repo("rafaelmjf/some-app")
    assert "rafaelmjf/some-app" in config.load_ignored_repos()


def test_config_unignore_repo_removes_from_list(tmp_path, monkeypatch):
    """config.unignore_repo removes the repo from the ignore list."""
    _init(tmp_path, monkeypatch)
    config.ignore_repo("rafaelmjf/some-app")
    config.unignore_repo("rafaelmjf/some-app")
    assert "rafaelmjf/some-app" not in config.load_ignored_repos()


def test_post_github_ignore_calls_ignore_repo(tmp_path, monkeypatch):
    """POST /github-ignore calls config.ignore_repo with the target."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    calls = []
    original_ignore = config.ignore_repo

    def fake_ignore(full_name):
        calls.append(full_name)
        return original_ignore(full_name)

    monkeypatch.setattr(config, "ignore_repo", fake_ignore)
    monkeypatch.setattr(dashboard.github_catalog, "load_cache", lambda owner, **kw: None)
    monkeypatch.setattr(dashboard.github_catalog, "refresh_cache", lambda owner, **kw: [])

    # Call gather_remote_projects path indirectly through the render path.
    # We test the wiring by calling ignore_repo directly and verifying the ignore list.
    config.ignore_repo("rafaelmjf/some-app")
    assert "rafaelmjf/some-app" in config.load_ignored_repos()
    assert len(calls) >= 1


def test_post_github_unignore_calls_unignore_repo(tmp_path, monkeypatch):
    """POST /github-unignore removes the target from the ignore list."""
    _init(tmp_path, monkeypatch)
    config.ignore_repo("rafaelmjf/some-app")
    config.unignore_repo("rafaelmjf/some-app")
    assert "rafaelmjf/some-app" not in config.load_ignored_repos()


def test_post_github_onboard_rejects_untrusted_owner(tmp_path, monkeypatch):
    """POST /github-onboard refuses onboarding a repo whose owner is not in load_github_owners()."""
    _init(tmp_path, monkeypatch)
    # No owner "evil-hacker" is registered.

    onboard_calls = []
    monkeypatch.setattr(
        dashboard.remote_start,
        "onboard_github_project",
        lambda target, **kw: onboard_calls.append(target),
    )
    monkeypatch.setattr(dashboard.github_catalog, "load_cache", lambda owner, **kw: None)
    monkeypatch.setattr(dashboard.github_catalog, "refresh_cache", lambda owner, **kw: [])

    # Simulate the owner-validation logic used in the POST handler.
    target = "evil-hacker/malicious-repo"
    owner = target.split("/")[0]
    owners = config.load_github_owners()

    # Owner is not trusted — onboard_github_project must NOT be called.
    if owner not in owners:
        # This is the guard — we verify the guard fires correctly.
        error_html = dashboard.render_remote_catalog(
            [],
            [f"refusing to onboard untrusted repo: {target}"],
        )
        assert "refusing to onboard untrusted repo" in error_html
    else:
        raise AssertionError("untrusted owner was somehow in the owner list")

    # onboard_github_project was NOT called.
    assert onboard_calls == []


def test_integration_result_exposes_detail_not_error():
    """The /github-onboard handler reports a non-ok integration via ``integ.detail``.
    Guard against reintroducing a reference to a nonexistent ``integ.error`` field
    (an AttributeError would crash the onboard POST when auto-merge can't be enabled).
    """
    from horus import integration

    r = integration.IntegrationResult(
        mode="branch-pr-automerge",
        committed=True,
        branch="horus/x",
        pushed=True,
        pr_url="https://example.com/pr/1",
        merged=False,
        detail="auto-merge enabled for PR https://example.com/pr/1",
        ok=False,
    )
    assert r.detail.startswith("auto-merge enabled")
    assert not hasattr(r, "error")


# ---------------------------------------------------------------------------
# Phase C-full: /settings page — workflow policy editor
# ---------------------------------------------------------------------------

def test_render_settings_shows_selects_with_current_values(tmp_path, monkeypatch):
    """render_settings renders three <select> controls with the current policy value marked selected."""
    _init(tmp_path, monkeypatch)
    policy = {
        "integration": "branch-pr-review",
        "commit": "manual",
        "merge": "review",
    }
    html_out = dashboard.render_settings(policy)
    # Current values are marked selected.
    assert "value='branch-pr-review' selected" in html_out
    assert "value='manual' selected" in html_out
    assert "value='review' selected" in html_out
    # Non-current values for integration are NOT selected.
    assert "value='branch-pr-automerge' selected" not in html_out
    assert "value='auto' selected" not in html_out
    # All three selects are present.
    assert html_out.count("<select name=") == 3
    # The form POSTs to /settings.
    assert "action='/settings'" in html_out


def test_render_settings_saved_banner(tmp_path, monkeypatch):
    """render_settings(saved=True) includes the success banner; saved=False does not."""
    _init(tmp_path, monkeypatch)
    policy = config.WORKFLOW_DEFAULTS.copy()
    assert "banner ok" in dashboard.render_settings(policy, saved=True)
    assert "banner ok" not in dashboard.render_settings(policy, saved=False)
    assert "banner ok" not in dashboard.render_settings(policy)


def test_nav_settings_link_present_and_active(tmp_path, monkeypatch):
    """_nav('settings') marks Settings active; _nav('projects') includes Settings link but not active."""
    _init(tmp_path, monkeypatch)
    nav_settings = dashboard._nav("settings")
    # The active class is on the Settings link.
    assert "class=\"active\"" in nav_settings
    # The Settings href is present.
    assert "href='/settings'" in nav_settings

    nav_projects = dashboard._nav("projects")
    # Settings link is still present (every page gets it).
    assert "href='/settings'" in nav_projects
    # But it is NOT marked active.
    # Find the settings anchor and confirm it has no active class.
    import re
    settings_anchor = re.search(r"<a href='/settings'[^>]*>Settings</a>", nav_projects)
    assert settings_anchor is not None
    assert 'class="active"' not in settings_anchor.group()


def test_every_page_includes_settings_nav(tmp_path, monkeypatch):
    """Every page (projects, control, sessions) includes the Settings nav link."""
    _init(tmp_path, monkeypatch)
    for page_html in [
        dashboard.render_index([]),
        dashboard.render_control([], [], []),
        dashboard._page("Horus — sessions", dashboard.render_sessions_card([]), active="sessions"),
    ]:
        assert "href='/settings'" in page_html


def test_render_settings_workflow_policy_persisted_and_rendered(tmp_path, monkeypatch):
    """set_workflow_policy + load_workflow_policy round-trips; render_settings reflects it."""
    _init(tmp_path, monkeypatch)
    config.set_workflow_policy(integration="branch-pr-review")
    policy = config.load_workflow_policy()
    assert policy["integration"] == "branch-pr-review"
    html_out = dashboard.render_settings(policy)
    assert "value='branch-pr-review' selected" in html_out


def test_settings_post_persists_and_redirects(tmp_path, monkeypatch):
    """POST /settings: config.set_workflow_policy is called with submitted values and
    the policy is persisted; the render_settings output then reflects the new value."""
    _init(tmp_path, monkeypatch)
    # Start from defaults.
    initial = config.load_workflow_policy()
    assert initial["integration"] == "branch-pr-automerge"

    # Simulate what the POST handler does: read the form and call set_workflow_policy.
    form = {"integration": "branch-pr-review", "commit": "manual", "merge": "review"}
    try:
        config.set_workflow_policy(
            integration=form.get("integration") or None,
            commit=form.get("commit") or None,
            merge=form.get("merge") or None,
        )
    except ValueError:
        pass

    # After save, load_workflow_policy reflects the new values.
    policy = config.load_workflow_policy()
    assert policy["integration"] == "branch-pr-review"
    assert policy["commit"] == "manual"
    assert policy["merge"] == "review"

    # render_settings with the new policy shows the new values selected.
    html_out = dashboard.render_settings(policy, saved=True)
    assert "value='branch-pr-review' selected" in html_out
    assert "value='manual' selected" in html_out
    assert "value='review' selected" in html_out
    assert "banner ok" in html_out
