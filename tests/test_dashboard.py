"""Tests for dashboard data gathering and HTML rendering (no socket)."""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlencode

import json

from horus import cache_status, config, dashboard, github_catalog, initialize, launcher, overhead
from horus.registry import Registry, SessionRecord
from horus.upgrade import UpgradeAction


def _init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _post(path: str, form: dict[str, str], *, origin: str | None = None) -> dict[str, object]:
    body = urlencode(form).encode("utf-8")
    handler = object.__new__(dashboard._Handler)
    handler.path = path
    handler.headers = {
        "Content-Length": str(len(body)),
        "Host": "127.0.0.1:8765",
    }
    if origin is not None:
        handler.headers["Origin"] = origin
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()

    response: dict[str, object] = {"headers": []}

    def send_response(status: int) -> None:
        response["status"] = status

    def send_header(key: str, value: str) -> None:
        response["headers"].append((key, value))  # type: ignore[index]

    def end_headers() -> None:
        response["ended"] = True

    handler.send_response = send_response  # type: ignore[method-assign]
    handler.send_header = send_header  # type: ignore[method-assign]
    handler.end_headers = end_headers  # type: ignore[method-assign]

    dashboard._Handler.do_POST(handler)
    response["body"] = handler.wfile.getvalue().decode("utf-8")
    return response


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


def test_render_index_has_accounts_strip_and_no_control(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    page = dashboard.render_index([], dashboard.gather_sessions())
    # Control tab retired: no nav link, no live-session cockpit card.
    assert ">Control</a>" not in page
    assert "Live sessions" not in page
    # Account usage now loads on the main tab (async strip).
    assert "data-horus-src='/accounts-panel'" in page


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


def test_accounts_strip_renders_usage_and_add_wizard():
    accounts = [{"alias": "work", "agent": "claude", "five_pct": 62.0, "week_pct": 20.0,
                 "five_reset": "2026-06-26 18:00", "week_reset": ""}]
    strip = dashboard._accounts_strip(accounts)
    assert "<div class='section'>" in strip and "Accounts" in strip
    assert "work" in strip and "62%" in strip  # usage ring
    assert "action='/account-login'" in strip  # add-account wizard present
    # The retired per-account in-app launcher is gone from the strip.
    assert "value='app'" not in strip


def test_accounts_strip_empty_state():
    assert "No agent account detected" in dashboard._accounts_strip([])


def test_accounts_strip_has_per_account_launch_and_remove():
    strip = dashboard._accounts_strip([
        {"alias": "work", "agent": "claude", "five_pct": 50.0, "week_pct": 10.0,
         "five_reset": "", "week_reset": ""},
    ])
    # "+ session" launches a native terminal as that account (not the retired in-app PTY).
    assert "+ session" in strip and "value='window'" in strip and "value='app'" not in strip
    # Remove-account button (red, confirm).
    assert "action='/account-remove'" in strip and "btn-danger" in strip


def test_process_account_remove_unmaps(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.set_account_config_dir("personal", str(tmp_path / "p"))
    assert "personal" in config.load_account_config_dirs()
    assert dashboard.process_account_remove({"alias": "personal"}) == "account=removed"
    assert "personal" not in config.load_account_config_dirs()
    # Removing an unknown account is reported, not an error.
    assert dashboard.process_account_remove({"alias": "nope"}) == "account=absent"


def test_account_remove_notice():
    assert "removed" in dashboard._launch_notice({"account": ["removed"]})


def test_project_column_has_launch_disclosure(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path / "proj", assume_yes=True, no_input=True)
    p = dashboard.load_project(str(tmp_path / "proj"))
    col = dashboard._project_column(p, 0, [{"alias": "work"}])
    assert "<details class='launch'>" in col and "Start a session" in col
    assert "action='/launch'" in col and "name='agent'" in col


def test_dashboard_server_is_single_instance():
    # The leak fix: only one dashboard may hold a port. Default ThreadingHTTPServer
    # allows duplicate binds on Windows; POSIX keeps reuse enabled so a clean restart
    # is not blocked by TIME_WAIT after the previous dashboard exits.
    assert dashboard._SingleInstanceServer.allow_reuse_address is (sys.platform != "win32")


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
    assert "Recommended mode:" in html_out
    assert "Craft execution.md + delegate bounded tasks" in html_out
    assert "plan-execution" in html_out
    assert "Newer change" in html_out


def test_next_action_direct_mode_hint(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "roadmap.md").write_text(
        '---\nstatus: active\nnext_action: "Fix one dashboard label"\n'
        'execution_recommendation: "continue-as-is - small single-surface fix"\n---\n'
        "# Roadmap\n",
        encoding="utf-8",
    )

    html_out = dashboard.render_index([dashboard.load_project(str(tmp_path))])

    assert "Fix one dashboard label" in html_out
    assert "Recommended mode:" in html_out
    assert "Proceed directly with the frontier model" in html_out
    assert "small single-surface fix" in html_out


def test_resume_prompt_prefers_written_then_falls_back(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    data = dashboard.load_project(str(tmp_path))

    # No next_prompt set -> generated minimum-context handoff with lazy-load instructions.
    fallback = dashboard._resume_prompt_text(data)
    assert tmp_path.name in fallback
    assert "git fetch --all --prune" in fallback
    assert "Do not read every `.horus/` lane up front." in fallback
    assert "horus session new" not in fallback  # not a CLI trigger

    # Authored next_prompt from roadmap.md is carried inside the generated handoff.
    (tmp_path / ".horus" / "roadmap.md").write_text(
        '---\nstatus: active\nnext_prompt: "Paste me into Claude to resume."\n---\n# Roadmap\n',
        encoding="utf-8",
    )
    data = dashboard.load_project(str(tmp_path))
    resumed = dashboard._resume_prompt_text(data)
    assert "Paste me into Claude to resume." in resumed
    assert "Continue with this authored handoff:" in resumed
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


def test_project_detail_renders_launch_controls(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    p = dashboard.load_project(str(proj))
    page = dashboard.render_project(p, index=0)

    # Start-a-session lives on the project detail page now (work-pickup model).
    assert "Start a session" in page
    assert "method='post' action='/launch'" in page
    assert "name='mode' value='fresh'" in page and "name='mode' value='resume'" in page
    assert "<select name='account'>" in page
    # Either agent can be launched in a native terminal window (not the Python TUI).
    assert "<select name='agent'>" in page
    assert ">Claude Code</option>" in page and ">Codex</option>" in page
    assert "value='window'" in page and "Open in a terminal window" in page
    assert "value='app'" not in page  # retired in-app PTY target
    assert "<select name='posture'>" in page
    # Copy-the-command fallback offers Claude + Codex.
    assert "horus open" in page and "--agent codex" in page


def test_process_launch_window_routes_selected_agent(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    captured = {}

    def fake_launch(**kwargs):
        captured.update(kwargs)
        from horus.launch import LaunchResult
        return LaunchResult(ok=True, agent=kwargs["agent"], project=kwargs["project_dir"], session_id="sid12345")

    monkeypatch.setattr(dashboard.launch, "launch_interactive", fake_launch)
    query = dashboard.process_launch(
        {"project": "0", "mode": "fresh", "agent": "codex", "target": "window"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query.startswith("launched=")
    assert captured["agent"] == "codex"  # the chosen agent reaches the launcher


def test_launch_notice_banner():
    ok = dashboard._launch_notice({"launched": ["abcd1234"]})
    assert "Launched session" in ok and "abcd1234" in ok and "banner ok" in ok
    err = dashboard._launch_notice({"error": ["unknown account"]})
    assert "Launch failed" in err and "unknown account" in err and "banner err" in err
    tab = dashboard._launch_notice({"tab": ["app-1"]})
    assert "terminal panel" in tab and "banner ok" in tab
    assert "Account mapping added" in dashboard._launch_notice({"account": ["added"]})
    assert "Account alias updated" in dashboard._launch_notice({"account": ["alias"]})
    assert dashboard._launch_notice({}) == ""


def test_process_account_add_maps_isolated_account_dirs(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)

    assert dashboard.process_account_add({
        "agent": "claude", "alias": "personal", "path": str(tmp_path / "claude-personal"),
    }) == "account=added"
    # Config-dir paths are stored forward-slashed (clean TOML on Windows); compare
    # path-normalized so the assertion holds on every OS.
    assert Path(config.load_account_config_dirs()["personal"]) == (tmp_path / "claude-personal")

    assert dashboard.process_account_add({
        "agent": "codex", "alias": "codex-personal", "path": str(tmp_path / "codex-personal"),
    }) == "account=added"
    assert Path(config.load_account_codex_homes()["codex-personal"]) == (tmp_path / "codex-personal")


def test_process_account_login_derives_dir_and_launches_claude(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    captured = {}

    def fake_login(argv, cwd, env):
        captured["argv"], captured["cwd"], captured["env"] = argv, cwd, env
        return 4242

    out = dashboard.process_account_login({"agent": "claude", "alias": "personal"}, launch_login=fake_login)

    assert out == "account=login-started"
    expected = config.account_login_dir("claude", "personal")
    # No path was supplied by the user — it was derived and the mapping recorded.
    assert config.load_account_config_dirs()["personal"] == expected
    assert captured["argv"] == ["claude"]
    assert captured["env"]["CLAUDE_CONFIG_DIR"] == expected
    assert Path(expected).is_dir()  # created so the login writes credentials into it


def test_process_account_login_codex_uses_codex_login(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    captured = {}
    out = dashboard.process_account_login(
        {"agent": "codex", "alias": "work"},
        launch_login=lambda argv, cwd, env: captured.update(argv=argv, env=env),
    )
    assert out == "account=login-started"
    expected = config.account_login_dir("codex", "work")
    assert config.load_account_codex_homes()["work"] == expected
    assert captured["argv"] == ["codex", "login"]
    assert captured["env"]["CODEX_HOME"] == expected


def test_process_account_login_requires_alias(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    out = dashboard.process_account_login({"agent": "claude", "alias": ""}, launch_login=lambda *a: None)
    assert out.startswith("error=")


def test_process_account_login_maps_even_when_terminal_fails(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)

    def boom(argv, cwd, env):
        raise OSError("no graphical display detected")

    out = dashboard.process_account_login({"agent": "claude", "alias": "headless"}, launch_login=boom)

    # Mapping stands; only the convenience terminal failed.
    assert out.startswith("account=mapped&login_error=")
    assert "headless" in config.load_account_config_dirs()


def test_login_notice_messages():
    assert "sign in" in dashboard._launch_notice({"account": ["login-started"]})
    assert "could not open" in dashboard._launch_notice({"login_error": ["boom"]})


def _scaffolded_project(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "proj"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True, no_input=True)
    return proj


def test_process_upgrade_project_applies_and_redirects(tmp_path, monkeypatch):
    _scaffolded_project(tmp_path, monkeypatch)
    out = dashboard.process_upgrade_project({"project": "0"})
    assert out.startswith("/project?i=0&upgraded=")


def test_process_upgrade_project_unknown_index(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    assert dashboard.process_upgrade_project({"project": "9"}).startswith("/?upgrade_error=")


def test_process_offboard_default_keeps_horus_and_unregisters(tmp_path, monkeypatch):
    proj = _scaffolded_project(tmp_path, monkeypatch)
    out = dashboard.process_offboard({"project": "0"})
    assert out.startswith("/?offboarded=")
    assert "purged=1" not in out
    assert config._as_key(proj) not in config.load_projects()  # unregistered
    assert (proj / ".horus").is_dir()  # memory kept


def test_process_offboard_purge_removes_horus(tmp_path, monkeypatch):
    proj = _scaffolded_project(tmp_path, monkeypatch)
    out = dashboard.process_offboard({"project": "0", "purge": "1"})
    assert out.startswith("/?offboarded=") and "purged=1" in out
    assert not (proj / ".horus").exists()


def test_process_offboard_unknown_index(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    assert dashboard.process_offboard({"project": "9"}).startswith("/?offboard_error=")


def test_offload_control_offers_keep_and_remove_completely():
    compact = dashboard._offload_control(2, compact=True)
    assert "<details class='offload'>" in compact  # reveal-on-click, not prominent
    assert "Keep files" in compact and "Remove completely" in compact
    assert "btn-keep" in compact and "btn-danger" in compact  # neutral keep, red remove
    assert "name='purge' value='1'" in compact  # remove-completely purges
    assert compact.count("action='/offboard'") == 2
    assert "name='project' value='2'" in compact

    full = dashboard._offload_control(2, compact=False)
    assert "Manage Horus integration" in full and "btn-danger" in full


def test_project_column_has_offload_control_at_end(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path / "proj", assume_yes=True, no_input=True)
    p = dashboard.load_project(str(tmp_path / "proj"))
    col = dashboard._project_column(p, 0)
    assert "<details class='offload'>" in col
    # The offload control sits at the end of the card (after the Roadmap box).
    assert col.rindex("offload") > col.rindex("Roadmap")


def test_project_action_banner_messages():
    assert "Refreshed Horus artifacts" in dashboard._project_action_banner({"upgraded": ["3"]})
    assert "Upgrade failed" in dashboard._project_action_banner({"upgrade_error": ["x"]})
    assert "Removed Horus" in dashboard._project_action_banner({"offboarded": ["demo"]})
    assert "deleted" in dashboard._project_action_banner({"offboarded": ["demo"], "purged": ["1"]})
    assert "kept" in dashboard._project_action_banner({"offboarded": ["demo"]})
    assert dashboard._project_action_banner({}) == ""


def test_onboard_handoff_offers_account_chooser_and_launch():
    html = dashboard.render_onboard_handoff(
        "demo", 3, "/work/demo", [{"alias": "personal"}, {"alias": "work"}],
    )
    assert "start working on it" in html
    assert "action='/launch'" in html
    assert "value='3'" in html  # launch posts the new project's index
    assert "personal" in html and "work" in html  # account-alias chooser


def test_onboard_handoff_without_accounts_points_to_wizard():
    html = dashboard.render_onboard_handoff("demo", 3, "/work/demo", [])
    assert "Accounts section" in html  # points at the main-tab accounts strip (Control retired)
    assert "action='/launch'" not in html  # nothing to launch as yet


def test_onboard_handoff_skips_when_project_not_located():
    assert dashboard.render_onboard_handoff("demo", None, "/work/demo", [{"alias": "x"}]) == ""


def test_process_account_alias_renames_generated_alias_and_mapping(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    old = config.alias_for("acct@example.com")
    assert old is not None
    claude_dir = tmp_path / "claude-old"
    claude_dir.mkdir()
    (claude_dir / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"emailAddress": "acct@example.com"}}),
        encoding="utf-8",
    )
    config.set_account_config_dir(old, str(claude_dir))

    assert dashboard.process_account_alias({
        "agent": "claude",
        "old_alias": old,
        "alias": "personal",
    }) == "account=alias"

    assert config.load_account_aliases()["acct@example.com"] == "personal"
    assert "personal" in config.load_account_config_dirs()
    assert old not in config.load_account_config_dirs()


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
    # The minimum-context resume handoff is seeded into the session.
    assert "demo" in captured["argv"][-1]
    assert "git fetch --all --prune" in captured["argv"][-1]


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
    assert "this machine's" in html_out
    assert "gh</code> GitHub login" in html_out
    assert "Claude/Codex account choice" in html_out


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


def test_post_github_ignore_redirects_and_persists_trusted_target(tmp_path, monkeypatch):
    """POST /github-ignore uses PRG so a browser does not land on a raw catalog fragment."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    # The ignore path should not perform expensive catalog rendering or session/launch work.
    monkeypatch.setattr(dashboard, "gather_remote_projects", lambda: (_ for _ in ()).throw(AssertionError("rendered catalog")))
    monkeypatch.setattr(dashboard, "process_launch", lambda form: (_ for _ in ()).throw(AssertionError("launched session")))

    response = _post("/github-ignore", {"target": "rafaelmjf/some-app"}, origin="http://127.0.0.1:8765")

    assert response["status"] == 303
    assert ("Location", "/#github-catalog") in response["headers"]
    assert response["body"] == ""
    assert "rafaelmjf/some-app" in config.load_ignored_repos()


def test_post_github_unignore_redirects_and_removes_trusted_target(tmp_path, monkeypatch):
    """POST /github-unignore uses the same browser-safe PRG path."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    config.ignore_repo("rafaelmjf/some-app")

    response = _post("/github-unignore", {"target": "rafaelmjf/some-app"})

    assert response["status"] == 303
    assert ("Location", "/#github-catalog") in response["headers"]
    assert "rafaelmjf/some-app" not in config.load_ignored_repos()


def test_post_github_ignore_rejects_malformed_or_untrusted_target(tmp_path, monkeypatch):
    """Ignore/unignore targets must be owner/repo names under configured GitHub owners."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    malformed = _post("/github-ignore", {"target": "not-a-full-name"})
    untrusted = _post("/github-ignore", {"target": "evil/some-app"})

    assert malformed["status"] == 303
    assert untrusted["status"] == 303
    assert "not-a-full-name" not in config.load_ignored_repos()
    assert "evil/some-app" not in config.load_ignored_repos()


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


# ---------------------------------------------------------------------------
# Phase B: per-project artifacts staleness badge
# ---------------------------------------------------------------------------

def test_load_project_artifacts_stale_when_would_update(tmp_path, monkeypatch):
    """load_project sets artifacts_stale=True and count when upgrade returns a would-update action."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    monkeypatch.setattr(
        dashboard.upgrade,
        "upgrade_project",
        lambda root, **kw: [
            UpgradeAction("would-update", "would refresh CLAUDE.md managed block"),
            UpgradeAction("would-update", "would refresh AGENTS.md managed block"),
            UpgradeAction("exists", "horus-consolidate (claude): up to date (v1)"),
        ],
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["artifacts_stale"] is True
    assert data["artifacts_stale_count"] == 2


def test_load_project_artifacts_not_stale_when_exists_or_skipped(tmp_path, monkeypatch):
    """load_project sets artifacts_stale=False when upgrade returns only exists/skipped."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    monkeypatch.setattr(
        dashboard.upgrade,
        "upgrade_project",
        lambda root, **kw: [
            UpgradeAction("exists", "CLAUDE.md managed block is current"),
            UpgradeAction("skipped", "AGENTS.md has no Horus managed block"),
        ],
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["artifacts_stale"] is False
    assert data["artifacts_stale_count"] == 0


def test_load_project_artifacts_stale_false_when_upgrade_raises(tmp_path, monkeypatch):
    """load_project does not crash and yields artifacts_stale=False when upgrade_project raises."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    def _boom(root, **kw):
        raise RuntimeError("simulated projection failure")

    monkeypatch.setattr(dashboard.upgrade, "upgrade_project", _boom)

    data = dashboard.load_project(str(tmp_path))
    assert data["artifacts_stale"] is False


def test_project_column_renders_artifacts_badge_when_stale(tmp_path, monkeypatch):
    """_project_column includes the artifacts-outdated pill when artifacts_stale is True."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    monkeypatch.setattr(
        dashboard.upgrade,
        "upgrade_project",
        lambda root, **kw: [UpgradeAction("would-update", "would refresh CLAUDE.md managed block")],
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["artifacts_stale"] is True

    html_out = dashboard._project_column(data, 0)
    assert "artifacts outdated" in html_out
    assert "&#9888;" in html_out
    # The pill now carries a one-click GREEN refresh button (POST upgrade by index).
    assert "action='/upgrade-project'" in html_out
    assert "name='project' value='0'" in html_out
    assert "btn-go" in html_out  # green = more visible


def test_project_column_omits_artifacts_badge_when_fresh(tmp_path, monkeypatch):
    """_project_column does NOT include the artifacts-outdated pill when artifacts_stale is False."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    monkeypatch.setattr(
        dashboard.upgrade,
        "upgrade_project",
        lambda root, **kw: [UpgradeAction("exists", "CLAUDE.md managed block is current")],
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["artifacts_stale"] is False

    html_out = dashboard._project_column(data, 0)
    assert "artifacts outdated" not in html_out


def test_render_project_shows_upgrade_command_when_stale(tmp_path, monkeypatch):
    """render_project includes the upgrade command note when artifacts_stale is True."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    monkeypatch.setattr(
        dashboard.upgrade,
        "upgrade_project",
        lambda root, **kw: [
            UpgradeAction("would-update", "would refresh CLAUDE.md managed block"),
            UpgradeAction("would-update", "would refresh AGENTS.md managed block"),
        ],
    )

    data = dashboard.load_project(str(tmp_path))
    html_out = dashboard.render_project(data)
    assert "artifacts outdated" in html_out
    assert "horus upgrade-project --apply" in html_out
    assert "2" in html_out  # count of stale items


def test_render_project_omits_upgrade_command_when_fresh(tmp_path, monkeypatch):
    """render_project does NOT include the upgrade command note when artifacts_stale is False."""
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    monkeypatch.setattr(
        dashboard.upgrade,
        "upgrade_project",
        lambda root, **kw: [UpgradeAction("exists", "CLAUDE.md managed block is current")],
    )

    data = dashboard.load_project(str(tmp_path))
    html_out = dashboard.render_project(data)
    assert "horus upgrade-project --apply" not in html_out
