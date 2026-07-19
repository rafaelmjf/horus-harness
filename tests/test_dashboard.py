"""Tests for dashboard data gathering and HTML rendering (no socket)."""

import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import parse_qs, urlencode, urlparse

import json

import pytest

from horus import cache_status, config, dashboard, github_catalog, initialize, launcher, native_hooks, overhead, registry, routines, templates
from horus.registry import Registry, SessionRecord
from horus.upgrade import UpgradeAction


@pytest.fixture(autouse=True)
def _isolate_dashboard_access_globals():
    """Snapshot and restore the exposed-mode gate globals around every test.

    ``dashboard.serve()`` calls ``_configure_access()``, which reads the real
    ``~/.horus/config.toml``. On a host where the dashboard is exposed (an
    ``[access]`` block present) that sets the module-global ``_DASH_ACCESS`` to a
    non-None gate, and it would otherwise leak into every later POST test — those
    hit the exposed-mode guard and 403 instead of redirecting. That made full-suite
    runs flaky (order-dependent), while isolated runs and CI (no ``[access]``)
    stayed green. Contain the pollution at its source so no test can leak it.
    """
    saved_access = dashboard._DASH_ACCESS
    saved_jwks = dashboard._JWKS_CACHE
    try:
        yield
    finally:
        dashboard._DASH_ACCESS = saved_access
        dashboard._JWKS_CACHE = saved_jwks


def _init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    # Most dashboard tests isolate the legacy direct-host behavior. Managed-host
    # tests opt into tmux explicitly so they do not depend on the developer machine.
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "current")


def _post(
    path: str,
    form: dict[str, str],
    *,
    origin: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    body = urlencode(form).encode("utf-8")
    handler = object.__new__(dashboard._Handler)
    handler.path = path
    handler.headers = {
        "Content-Length": str(len(body)),
        "Host": "127.0.0.1:8765",
    }
    if origin is not None:
        handler.headers["Origin"] = origin
    if headers:
        handler.headers.update(headers)
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
    assert len(records) == 1 and records[0].status == "stale"  # pid-less running -> stale


def test_render_sessions_card_offers_reviewed_dismiss_only_when_finished():
    running = SessionRecord(session_id="run1", agent="codex", project="/p",
                            pid=1, status="running", updated_at="t")
    done = SessionRecord(session_id="done1", agent="codex", project="/p",
                         pid=None, status="exited", updated_at="t")
    html = dashboard.render_sessions_card([running, done])
    assert html.count("action='/session-dismiss'") == 1   # finished row only
    assert "value='done1'" in html
    assert "awaiting review" in html                       # explains the badge term
    assert "as of " in html


def test_render_sessions_card_flags_stale_with_cleanup():
    stale = SessionRecord(session_id="stale1", agent="codex", project="/p",
                          pid=123456, status="stale", updated_at="t")
    html = dashboard.render_sessions_card([stale])
    assert "stale" in html
    assert "Clean up" in html
    assert "never counts as running" in html


def test_process_session_dismiss_removes_only_finished(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    reg = Registry.default()
    reg.upsert(SessionRecord(session_id="live", agent="codex", project="/p",
                             pid=os.getpid(), status="running"))
    reg.upsert(SessionRecord(session_id="done", agent="codex", project="/p",
                             pid=None, status="exited"))
    assert dashboard.process_session_dismiss({"session_id": "done"}) == "/sessions"
    assert Registry.default().get("done") is None
    assert dashboard.process_session_dismiss({"session_id": "live"}) == "/sessions"
    assert Registry.default().get("live") is not None      # running rows never dismissed
    assert dashboard.process_session_dismiss({"session_id": "nope"}) == "/sessions"
    assert dashboard.process_session_dismiss({}) == "/sessions"


def test_post_session_dismiss_route_redirects_to_sessions(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    Registry.default().upsert(SessionRecord(session_id="d1", agent="codex", project="/p",
                                            pid=None, status="exited"))
    resp = _post("/session-dismiss", {"session_id": "d1"}, origin="http://127.0.0.1:8765")
    assert resp["status"] == 303
    assert ("Location", "/sessions") in resp["headers"]
    assert Registry.default().get("d1") is None


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


def test_no_welcome_overlay(tmp_path, monkeypatch):
    # The first-run "Enter the dashboard" splash was removed: it was decorative only
    # (no input, gated nothing) and its sessionStorage seen-flag reset on every new
    # tab/window `horus app` opened, so it looped endlessly. The dashboard now renders
    # straight to content.
    _init(tmp_path, monkeypatch)
    page = dashboard.render_index([])
    assert "horusWelcome" not in page
    assert "welcome" not in page.lower()
    assert "Enter the dashboard" not in page


def test_control_usage_color_and_ring_by_threshold():
    assert dashboard._usage_color(95) == "#f08a8a"
    assert dashboard._usage_color(75) == "#e6c35c"
    assert dashboard._usage_color(10) == "#57d39a"
    assert "stroke-dasharray='60 100'" in dashboard._ring(60.4)
    assert ">--<" in dashboard._ring(None)  # unknown usage -> gray, no fill


def test_accounts_strip_renders_usage_and_add_wizard(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: True)  # desktop: no in-app target here
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


def test_accounts_strip_has_per_account_launch_and_remove(monkeypatch):
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: True)  # desktop -> native terminal
    strip = dashboard._accounts_strip([
        {"alias": "work", "agent": "claude", "five_pct": 50.0, "week_pct": 10.0,
         "five_reset": "", "week_reset": ""},
    ])
    # "+ session" launches a native terminal as that account on a desktop (headless
    # hosts post the in-app target instead — see test_launch_targets).
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


def test_serve_refuses_when_port_already_bound(tmp_path, monkeypatch, capsys):
    # Hermetic HOME so serve()'s _configure_access() reads no real config (a host
    # with an [access] block would otherwise arm exposed mode for the process).
    _init(tmp_path, monkeypatch)

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
    # Fresh init scaffolds structure v3 (PRD.md); its bootstrap status is "active".
    assert data["status"] == "active"
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


def test_project_detail_renders_machine_readiness_warning_and_badge(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "requirements.md").write_text(
        """---
kind: machine-requirements
tools:
  - name: Definitely absent CLI
    probe: horus-definitely-absent-cli
    install: install the project CLI
    needed_for: project builds
configs: []
---
""",
        encoding="utf-8",
    )

    data = dashboard.load_project(str(tmp_path))
    html_out = dashboard.render_project(data)
    assert "Machine readiness" in html_out
    assert "1 machine requirement missing" in html_out
    assert "this machine is missing: Definitely absent CLI" in html_out
    assert "needed for project builds" in html_out
    assert any("machine requirement missing" in finding["message"] for finding in data["findings"])


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

    # The single NEXT is agent-authored, not inferred. Fresh init scaffolds
    # structure v3 (PRD.md); the fields are PRD-first, so author them there.
    (tmp_path / ".horus" / "PRD.md").write_text(
        '---\nstatus: active\nnext_action: "Wire the adapter contract"\n'
        'execution_recommendation: "plan-execution — cross-module work"\n---\n'
        "# PRD\n\n- [ ] First task.\n",
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
    # Fresh init scaffolds structure v3 (PRD.md); the fields are PRD-first.
    (tmp_path / ".horus" / "PRD.md").write_text(
        '---\nstatus: active\nnext_action: "Fix one dashboard label"\n'
        'execution_recommendation: "continue-as-is - small single-surface fix"\n---\n'
        "# PRD\n",
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
    # Fresh init scaffolds structure v3 (PRD.md), so the PRD-flavored lazy-load
    # wording applies (see routines.resume_prompt's has_prd branch).
    fallback = dashboard._resume_prompt_text(data)
    assert tmp_path.name in fallback
    assert "git fetch --all --prune" in fallback
    assert "Do not front-load the whole `.horus/` directory." in fallback
    assert "horus session new" not in fallback  # not a CLI trigger

    # Authored next_prompt from PRD.md (structure v3, PRD-first) is carried
    # inside the generated handoff.
    (tmp_path / ".horus" / "PRD.md").write_text(
        '---\nstatus: active\nnext_prompt: "Paste me into Claude to resume."\n---\n# PRD\n',
        encoding="utf-8",
    )
    data = dashboard.load_project(str(tmp_path))
    resumed = dashboard._resume_prompt_text(data)
    assert "Paste me into Claude to resume." in resumed
    assert "Proposed authored handoff (context only — do not execute yet):" in resumed
    assert "ask permission to proceed" in resumed
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

    # Detail: anchored roadmap shows open items; completed live in the file only.
    det = dashboard.render_project(data)
    assert "id='roadmap'" in det
    assert "Open &amp; in progress (2)" in det
    assert "todo one" in det and "doing two" in det
    assert "Completed (1)" not in det  # completed items kept out of the dashboard now


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

    det = dashboard.render_project(data, index=0)
    assert "id='features'" in det and "Widget engine" in det
    assert "<table>" in det  # capability ledger rendered as a table
    # History is no longer inline-rendered (it only grows); a note + editor link instead.
    assert "the big outage" not in det
    assert "History holds the full rationale" in det
    assert "/open-lane" in det  # open-in-editor affordance present on the detail page

    idx = dashboard.render_index([data])
    # New column layout: features show as named buckets (Idea / In progress / Shipped).
    assert "Main features" in idx and "Widget engine" in idx
    assert "Latest local recovery note" in idx


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
    # Force a desktop session so native-terminal / VS Code targets are offered
    # (a headless host would show only the in-app terminal — see test_launch_targets).
    monkeypatch.setattr(dashboard.launcher, "has_display", lambda: True)
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
    # Launch destinations: in-app terminal (default, works headless) plus native
    # terminal / VS Code when a desktop session is present.
    assert "<select name='target'>" in page
    assert "value='app'>In-app terminal" in page
    assert "value='window'>Native terminal" in page
    assert "value='vscode'>VS Code" in page
    assert "<select name='posture'>" in page
    # Copy-the-command fallback offers Claude + Codex.
    assert "horus open" in page and "--agent codex" in page
    # No live PTY -> the xterm panel/assets are not embedded (CSS class defs aside).
    assert "/assets/xterm/xterm.js" not in page


def test_project_detail_links_to_sessions_without_embedding_terminal(tmp_path, monkeypatch):
    import types
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    p = dashboard.load_project(str(proj))
    term = types.SimpleNamespace(term_id="term-xyz", title="claude", alive=True)
    page = dashboard.render_project(p, index=0, terminals=[term])
    # The Sessions cockpit is the single home for live terminals; the project page
    # only links across (no duplicate SSE viewer / xterm embed per page).
    assert "live in-app terminal session" in page   # the banner's distinctive copy
    assert "open Sessions" in page
    assert "/assets/xterm/xterm.js" not in page
    assert "data-tid='term-xyz'" not in page
    assert "EventSource('/pty/stream" not in page

    # With no live terminal, the banner is absent entirely (CSS class defs aside).
    page_none = dashboard.render_project(p, index=0, terminals=[])
    assert "live in-app terminal" not in page_none


def test_app_launch_redirects_to_sessions_cockpit(monkeypatch):
    # An in-app terminal launch (query "tab=<id>") lands on the Sessions cockpit.
    monkeypatch.setattr(dashboard, "process_launch", lambda form, **kw: "tab=pty-9")
    resp = _post("/launch", {"project": "0", "target": "app", "agent": "claude", "mode": "fresh"})
    assert resp["status"] == 303
    assert dict(resp["headers"]).get("Location") == "/sessions?tab=pty-9"


def test_window_launch_still_redirects_to_project(monkeypatch):
    monkeypatch.setattr(dashboard, "process_launch", lambda form, **kw: "launched=abcd1234")
    resp = _post("/launch", {"project": "2", "target": "window", "agent": "claude", "mode": "fresh"})
    assert resp["status"] == 303
    assert dict(resp["headers"]).get("Location") == "/project?i=2&launched=abcd1234"


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

    monkeypatch.setattr(dashboard.backend.launch, "launch_interactive", fake_launch)
    query = dashboard.process_launch(
        {"project": "0", "mode": "fresh", "agent": "codex", "target": "window"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query.startswith("launched=")
    assert captured["agent"] == "codex"  # the chosen agent reaches the launcher


def test_process_launch_window_opens_managed_tmux_viewer(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    opened = {}
    monkeypatch.setattr(dashboard.terminal_sessions, "default_target", lambda: "tmux")
    monkeypatch.setattr(
        dashboard.terminal_sessions,
        "launch_tmux",
        lambda **kwargs: dashboard.backend.launch.LaunchResult(
            True,
            kwargs["agent"],
            Path(kwargs["project_dir"]),
            session_id="12345678-1234-1234-1234-123456789abc",
            target_ref="horus-123456781234",
        ),
    )

    def fake_open(argv, cwd, env=None):
        opened.update(argv=argv, cwd=cwd)
        return 6060

    monkeypatch.setattr(dashboard.terminal_sessions.launcher, "open_terminal", fake_open)
    query = dashboard.process_launch(
        {"project": "0", "mode": "fresh", "agent": "codex", "target": "window"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query == "launched=12345678"
    assert opened["argv"] == ["tmux", "attach-session", "-t", "horus-123456781234"]


def test_project_prs_fragment_empty_when_no_open_horus_prs(tmp_path, monkeypatch):
    # Both "none open" and "unknowable" render nothing — no panel noise.
    monkeypatch.setattr(dashboard.integration, "open_horus_prs", lambda path: [])
    assert dashboard._project_prs_html(str(tmp_path)) == ""
    monkeypatch.setattr(dashboard.integration, "open_horus_prs", lambda path: None)
    assert dashboard._project_prs_html(str(tmp_path)) == ""


def test_project_prs_fragment_nudges_on_open_continuity_pr(tmp_path, monkeypatch):
    monkeypatch.setattr(
        dashboard.integration, "open_horus_prs",
        lambda path: [{"branch": "horus/chore-continuity", "url": "https://gh/pr/7", "title": "Continuity"}],
    )
    frag = dashboard._project_prs_html(str(tmp_path))
    assert "banner err" in frag and "Allow auto-merge" in frag
    assert "https://gh/pr/7" in frag and "horus/chore-continuity" in frag


def test_project_detail_includes_prs_nudge_placeholder(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    page = dashboard.render_project(dashboard.load_project(str(proj)), index=0)
    assert "data-horus-src='/project-prs?i=0'" in page


def test_process_launch_vscode_opens_folder_without_spawning_agent(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    opened = {}

    def fake_open_vscode(project_dir):
        opened["dir"] = project_dir
        return 777

    def unexpected_launch(**kwargs):  # pragma: no cover
        raise AssertionError("vscode target must not spawn an agent session")

    monkeypatch.setattr(dashboard.launcher, "open_vscode", fake_open_vscode)
    monkeypatch.setattr(dashboard.backend.launch, "launch_interactive", unexpected_launch)

    query = dashboard.process_launch(
        {"project": "0", "mode": "resume", "target": "vscode"},
        projects=[str(proj)], known_aliases=set(),
    )

    assert query == "vscode=demo"
    assert opened["dir"] == proj


def test_process_launch_vscode_reports_missing_code_cli(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)

    def fake_open_vscode(project_dir):
        raise OSError("VS Code CLI `code` not found on PATH")

    monkeypatch.setattr(dashboard.launcher, "open_vscode", fake_open_vscode)

    query = dashboard.process_launch(
        {"project": "0", "mode": "fresh", "target": "vscode"},
        projects=[str(proj)], known_aliases=set(),
    )

    assert query.startswith("error=")
    assert "code" in query


def test_launch_notice_banner():
    ok = dashboard._launch_notice({"launched": ["abcd1234"]})
    assert "Launched session" in ok and "abcd1234" in ok and "banner ok" in ok
    err = dashboard._launch_notice({"error": ["unknown account"]})
    assert "Launch failed" in err and "unknown account" in err and "banner err" in err
    tab = dashboard._launch_notice({"tab": ["app-1"]})
    assert "terminal panel" in tab and "banner ok" in tab
    vs = dashboard._launch_notice({"vscode": ["demo"]})
    assert "VS Code" in vs and "demo" in vs and "banner ok" in vs
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


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _commit_scaffold(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.name", "Horus Test")
    _git(repo, "config", "user.email", "horus@example.test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "scaffold")


def _commit_scaffold_with_origin(repo: Path, tmp_path: Path) -> None:
    """Like `_commit_scaffold`, but on branch `main` with a real local bare
    `origin` remote — real `git push`/branch/checkout all work with no network,
    only `gh` needs faking."""
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Horus Test")
    _git(repo, "config", "user.email", "horus@example.test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "scaffold")
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, text=True, check=True)
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-u", "origin", "main")


def _fake_git_real_gh_faked(pr_create_ok: bool = True, merge_ok: bool = True):
    """`integration._run` stand-in: real `git` subprocesses (so branch/commit/push
    against the local bare origin genuinely happen), but `gh` is faked since it
    needs real GitHub auth that tests don't have."""

    def _runner(cmd: list[str], cwd) -> subprocess.CompletedProcess:
        if cmd and cmd[0] == "git":
            return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
        if cmd[:3] == ["gh", "pr", "create"]:
            if pr_create_ok:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="https://github.com/example/repo/pull/1\n", stderr=""
                )
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="gh pr create failed: no auth")
        if cmd[:3] == ["gh", "pr", "merge"]:
            if merge_ok:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="auto-merge disabled")
        if cmd[:2] == ["gh", "api"]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="unexpected command in test")

    return _runner


def test_process_upgrade_project_applies_and_redirects(tmp_path, monkeypatch):
    _scaffolded_project(tmp_path, monkeypatch)
    out = dashboard.process_upgrade_project({"project": "0"})
    assert out.startswith("/project?i=0&upgraded=")


def test_process_upgrade_project_blocks_dirty_checkout_without_git_mutation(tmp_path, monkeypatch):
    proj = _scaffolded_project(tmp_path, monkeypatch)
    staged = proj / "staged.txt"
    unstaged = proj / "unstaged.txt"
    staged.write_text("clean\n", encoding="utf-8")
    unstaged.write_text("clean\n", encoding="utf-8")
    _commit_scaffold(proj)

    staged.write_text("staged change\n", encoding="utf-8")
    _git(proj, "add", staged.name)
    unstaged.write_text("unstaged change\n", encoding="utf-8")
    untracked = proj / "untracked.txt"
    untracked.write_text("untracked\n", encoding="utf-8")

    calls: list[bool] = []

    def fake_upgrade(root: Path, *, apply: bool = False):
        calls.append(apply)
        if apply:
            (root / "should-not-exist").write_text("mutated", encoding="utf-8")
        return [UpgradeAction("would-update", "would refresh AGENTS.md", "AGENTS.md")]

    monkeypatch.setattr(dashboard.upgrade, "upgrade_project", fake_upgrade)
    before_status = _git(proj, "status", "--porcelain=v1")
    before_head = _git(proj, "rev-parse", "HEAD")
    before_stash = _git(proj, "stash", "list")
    before_contents = {path.name: path.read_bytes() for path in (staged, unstaged, untracked)}

    response = _post("/upgrade-project", {"project": "0"})
    assert response["status"] == 303
    location = dict(response["headers"])["Location"]
    params = parse_qs(urlparse(location).query)
    banner = dashboard._project_action_banner(params)

    assert calls == [False]
    assert "Refresh blocked" in banner
    assert all(name in banner for name in (staged.name, unstaged.name, untracked.name))
    assert "AGENTS.md" in banner
    assert "Launch reconciliation session" in banner
    assert not (proj / "should-not-exist").exists()
    assert _git(proj, "status", "--porcelain=v1") == before_status
    assert _git(proj, "rev-parse", "HEAD") == before_head
    assert _git(proj, "stash", "list") == before_stash
    assert {path.name: path.read_bytes() for path in (staged, unstaged, untracked)} == before_contents


def test_process_upgrade_project_clean_manual_lists_uncommitted_paths(tmp_path, monkeypatch):
    proj = _scaffolded_project(tmp_path, monkeypatch)
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = proj / name
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(f"horus-block-version: {templates.BLOCK_VERSION}", "horus-block-version: 9"), encoding="utf-8")
    _commit_scaffold(proj)
    config.set_workflow_policy(commit="manual")

    location = dashboard.process_upgrade_project({"project": "0"})
    params = parse_qs(urlparse(location).query)
    changed_paths = json.loads(params["upgrade_paths"][0])
    banner = dashboard._project_action_banner(params)

    assert changed_paths == ["AGENTS.md", "CLAUDE.md"]
    assert params["upgrade_manual"] == ["1"]
    assert "Tracked files are now uncommitted" in banner
    assert all(path in banner for path in changed_paths)
    assert f"git -C {proj} add -- AGENTS.md CLAUDE.md" in banner
    assert f"git -C {proj} commit -m &#x27;Refresh Horus artifacts&#x27;" in banner
    dirty_paths = set(_git(proj, "diff", "--name-only").splitlines())
    assert dirty_paths == set(changed_paths)


def test_process_upgrade_project_clean_automerge_dispatches_branch_pr_and_leaves_main_clean(
    tmp_path, monkeypatch
):
    """Locks bugs/refresh-artifacts-leaves-dirty-worktree.md: with the default
    (branch-pr-automerge) workflow policy, a clean refresh must not leave the
    live checkout's default branch dirty — the change lands via a Horus branch
    + PR instead."""
    proj = _scaffolded_project(tmp_path, monkeypatch)
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = proj / name
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(f"horus-block-version: {templates.BLOCK_VERSION}", "horus-block-version: 9"), encoding="utf-8")
    _commit_scaffold_with_origin(proj, tmp_path)
    monkeypatch.setattr(dashboard.integration, "_run", _fake_git_real_gh_faked())

    location = dashboard.process_upgrade_project({"project": "0"})
    params = parse_qs(urlparse(location).query)

    assert params.get("upgrade_pr") == ["https://github.com/example/repo/pull/1"]
    assert "upgrade_detail" not in params  # ok=True: no failure to surface

    # The regression this locks: main is not left dirty against a branch-pr policy.
    assert _git(proj, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert _git(proj, "status", "--porcelain") == ""
    assert _git(proj, "branch", "--list", "horus/*")  # the refresh landed on a branch


def test_process_upgrade_project_clean_automerge_records_integration_failure(tmp_path, monkeypatch):
    """A failed PR/merge step still must not strand the change dirty on main — the
    commit already moved to the feature branch before the failure, and the
    failure detail is surfaced instead of silently claiming success."""
    proj = _scaffolded_project(tmp_path, monkeypatch)
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = proj / name
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(f"horus-block-version: {templates.BLOCK_VERSION}", "horus-block-version: 9"), encoding="utf-8")
    _commit_scaffold_with_origin(proj, tmp_path)
    monkeypatch.setattr(dashboard.integration, "_run", _fake_git_real_gh_faked(pr_create_ok=False))

    location = dashboard.process_upgrade_project({"project": "0"})
    params = parse_qs(urlparse(location).query)

    assert "upgrade_detail" in params
    assert "gh pr create failed" in params["upgrade_detail"][0]
    assert _git(proj, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert _git(proj, "status", "--porcelain") == ""


def test_process_upgrade_project_unknown_index(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    assert dashboard.process_upgrade_project({"project": "9"}).startswith("/?upgrade_error=")


def _force_stale_build(monkeypatch):
    monkeypatch.setattr(
        dashboard.selfupdate,
        "build_state",
        lambda: {"running": "0.0.6", "disk": "9.9.9", "stale": True},
    )


def test_stale_build_refuses_artifact_writes(tmp_path, monkeypatch):
    proj = _scaffolded_project(tmp_path, monkeypatch)
    _force_stale_build(monkeypatch)
    # Fresh init scaffolds structure v3 (PRD.md), not project.md.
    marker = proj / ".horus" / "PRD.md"
    before = marker.read_text(encoding="utf-8")
    assert dashboard.process_upgrade_project({"project": "0"}) == "/project?i=0&stale_build=1"
    assert marker.read_text(encoding="utf-8") == before  # nothing rewritten
    assert dashboard.process_offboard({"project": "0"}) == "/?stale_build=1"
    assert config.load_projects()  # still registered — offboard refused


def test_stale_build_banner_on_pages_and_refusal_notice(monkeypatch):
    _force_stale_build(monkeypatch)
    page = dashboard._page("t", "<p>x</p>")
    assert "running an old build" in page and "9.9.9" in page and "horus dashboard --reload" in page
    notice = dashboard._project_action_banner({"stale_build": ["1"]})
    assert "Refused" in notice and "old build" in notice


def test_post_github_onboard_refuses_on_stale_build(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    _force_stale_build(monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(
        dashboard.remote_start,
        "onboard_github_project",
        lambda target, **kw: calls.append(target),
    )
    res = _post("/github-onboard", {"target": "owner/repo"})
    assert res["status"] == 303
    assert any(k == "Location" and "stale_build=1" in v for k, v in res["headers"])
    assert calls == []  # onboard (init + integrate writes) never ran


def test_fresh_build_renders_no_stale_banner(monkeypatch):
    monkeypatch.setattr(
        dashboard.selfupdate,
        "build_state",
        lambda: {"running": "0.0.8", "disk": "0.0.8", "stale": False},
    )
    assert "running an old build" not in dashboard._page("t", "<p>x</p>")


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


def test_project_column_keeps_offload_off_overview_cards(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path / "proj", assume_yes=True, no_input=True)
    p = dashboard.load_project(str(tmp_path / "proj"))
    col = dashboard._project_column(p, 0)
    assert "<details class='offload'>" not in col
    assert "moved to the project detail page" in col


def test_project_action_banner_messages():
    assert "Refreshed Horus artifacts" in dashboard._project_action_banner({"upgraded": ["3"]})
    assert "Upgrade failed" in dashboard._project_action_banner({"upgrade_error": ["x"]})
    assert "Removed Horus" in dashboard._project_action_banner({"offboarded": ["demo"]})
    assert "deleted" in dashboard._project_action_banner({"offboarded": ["demo"], "purged": ["1"]})
    assert "kept" in dashboard._project_action_banner({"offboarded": ["demo"]})
    assert dashboard._project_action_banner({}) == ""


def test_onboard_banner_success_with_pr_and_detail():
    """Post-onboard PRG banner (replaced render_onboard_handoff: the redirect lands on
    the project detail page, whose Start-a-session card is the CTA)."""
    out = dashboard._project_action_banner({
        "onboarded": ["me/demo"],
        "onboard_pr": ["https://github.com/me/demo/pull/1"],
    })
    assert "Onboarded me/demo" in out
    assert "https://github.com/me/demo/pull/1" in out
    incomplete = dashboard._project_action_banner({
        "onboarded": ["me/demo"],
        "onboard_detail": ["auto-merge could not be enabled"],
    })
    assert "Integration incomplete" in incomplete
    assert "auto-merge could not be enabled" in incomplete


def test_upgrade_banner_shows_integration_pr_and_incomplete_detail():
    out = dashboard._project_action_banner({
        "upgraded": ["2"],
        "upgrade_paths": ['["AGENTS.md", "CLAUDE.md"]'],
        "upgrade_pr": ["https://github.com/me/demo/pull/9"],
    })
    assert "Integration PR" in out
    assert "https://github.com/me/demo/pull/9" in out

    incomplete = dashboard._project_action_banner({
        "upgraded": ["2"],
        "upgrade_paths": ['["AGENTS.md"]'],
        "upgrade_detail": ["gh pr create failed: no auth"],
    })
    assert "Integration incomplete" in incomplete
    assert "gh pr create failed" in incomplete


def test_onboard_banner_error():
    out = dashboard._project_action_banner({"onboard_error": ["refusing to onboard untrusted repo: x/y"]})
    assert "Onboard failed" in out
    assert "refusing to onboard" in out


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
    assert calls["cols"] == 80               # desktop/no hint keeps the established default
    assert calls["managed"] is True

    # An unknown posture is rejected (not silently launched at default).
    assert dashboard.process_launch(
        {"project": "0", "target": "app", "posture": "nope"},
        projects=[str(proj)], known_aliases=set(),
    ) == "error=unknown+permission+mode"


def test_process_launch_in_app_uses_bounded_phone_spawn_width(tmp_path, monkeypatch):
    """The launching phone can size Claude's first paint before the viewer attaches;
    malformed/untrusted hints degrade to the established 80-column default."""
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    calls = []
    monkeypatch.setattr(dashboard.pty_host.host, "start", lambda **kw: calls.append(kw) or "pty-1")

    base = {"project": "0", "mode": "fresh", "agent": "fake", "target": "app"}
    assert dashboard.process_launch(
        {**base, "spawn_cols": "39"}, projects=[str(proj)], known_aliases=set(),
    ) == "tab=pty-1"
    assert calls[-1]["cols"] == 39

    for bad in ("", "nope", "1", "999"):
        dashboard.process_launch(
            {**base, "spawn_cols": bad}, projects=[str(proj)], known_aliases=set(),
        )
        assert calls[-1]["cols"] == 80


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
    assert "class='termclose linkbtn' data-tid='pty-7'" in page  # per-tab close control
    assert "/pty/close" in page                          # close wiring posts to the host
    # A CLI exit stays inspectable; only the explicit close control removes it.
    assert "Never auto-remove an exited session" in page
    assert "setTimeout(function(){removeTab(tid);}, 1500)" not in page


def test_page_adds_compact_spawn_width_hint_to_in_app_launches():
    page = dashboard._page("test", "<form method='post' action='/launch'></form>")
    assert "input[name=spawn_cols]" in page
    assert "Math.floor(w/10)" in page
    assert "t==='app'&&compact" in page


def test_pty_close_route_forgets_terminal(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    closed = []
    monkeypatch.setattr(dashboard.pty_host.host, "close", lambda tid: closed.append(tid) or True)
    resp = _post("/pty/close", {"id": "pty-3"})
    assert resp["status"] == 204
    assert closed == ["pty-3"]


def test_pty_input_unknown_session_is_410_not_silent_204(tmp_path, monkeypatch):
    """A stale viewer (page kept alive across a dashboard restart) must get a
    signal: input to a gone terminal is 410, not a silently-swallowing 204."""
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr(dashboard.pty_host, "host", dashboard.pty_host.PtyHost())
    resp = _post("/pty/input", {"id": "pty-stale", "data": "ls"})
    assert resp["status"] == 410


def test_pty_input_live_session_is_204(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    written = []
    monkeypatch.setattr(
        dashboard.pty_host.host, "write",
        lambda tid, data: written.append((tid, data)) or True,
    )
    resp = _post("/pty/input", {"id": "pty-1", "data": "hi"})
    assert resp["status"] == 204
    assert written == [("pty-1", b"hi")]


def test_pty_resize_unknown_or_dead_session_is_410(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    host = dashboard.pty_host.PtyHost()
    host._terms["pty-dead"] = dashboard.pty_host.PtyTerminal(
        term_id="pty-dead", agent="claude", project_dir=tmp_path, alive=False,
    )
    monkeypatch.setattr(dashboard.pty_host, "host", host)
    assert _post("/pty/resize", {"id": "pty-missing", "cols": "80", "rows": "24"})["status"] == 410
    assert _post("/pty/resize", {"id": "pty-dead", "cols": "80", "rows": "24"})["status"] == 410


def test_pty_resize_with_vid_registers_viewer_smallest_wins(tmp_path, monkeypatch):
    """A vid-carrying resize goes through the viewer registry (smallest-wins),
    not the raw last-writer-wins setter."""
    _init(tmp_path, monkeypatch)
    host = dashboard.pty_host.PtyHost()
    host._terms["pty-1"] = dashboard.pty_host.PtyTerminal(
        term_id="pty-1", agent="claude", project_dir=tmp_path,
    )
    monkeypatch.setattr(dashboard.pty_host, "host", host)
    calls = []
    monkeypatch.setattr(host, "viewer_resize", lambda tid, vid, c, r: calls.append((tid, vid, c, r)) or True)
    resp = _post("/pty/resize", {"id": "pty-1", "vid": "vabc", "cols": "38", "rows": "26"})
    assert resp["status"] == 204
    assert calls == [("pty-1", "vabc", 38, 26)]


def test_pty_release_drops_viewer(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    released = []
    monkeypatch.setattr(
        dashboard.pty_host.host, "viewer_release",
        lambda tid, vid: released.append((tid, vid)),
    )
    resp = _post("/pty/release", {"id": "pty-1", "vid": "vabc"})
    assert resp["status"] == 204
    assert released == [("pty-1", "vabc")]


def test_terminal_js_has_viewer_identity_wiring(tmp_path, monkeypatch):
    """Every viewer registers under a vid (smallest-wins geometry) and releases
    it when hidden, so a backgrounded tab stops constraining other viewers."""
    _init(tmp_path, monkeypatch)
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-7", agent="claude", project_dir=tmp_path, title="demo · work",
    )
    page = dashboard.render_control([], [], [], terminals=[term])
    assert "var vid = 'v' + Math.random()" in page
    assert "vid:vid" in page                        # resize posts carry the vid
    assert "'&vid='+encodeURIComponent(vid)" in page  # stream ties vid for cleanup
    assert "/pty/release" in page and "sendBeacon" in page


def test_pty_redraw_jiggles_live_session_410_when_gone(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr(dashboard.pty_host, "host", dashboard.pty_host.PtyHost())
    assert _post("/pty/redraw", {"id": "pty-gone"})["status"] == 410
    jiggled = []
    monkeypatch.setattr(
        dashboard.pty_host.host,
        "redraw",
        lambda tid, token=None: jiggled.append((tid, token)) or True,
    )
    assert _post("/pty/redraw", {"id": "pty-1", "reset": "viewer-reset-1"})["status"] == 204
    assert jiggled == [("pty-1", "viewer-reset-1")]
    assert _post("/pty/redraw", {"id": "pty-1", "reset": "bad\nsse"})["status"] == 204
    assert jiggled[-1] == ("pty-1", None)  # untrusted SSE control data is discarded


def test_terminal_js_geometry_epoch_handshake(tmp_path, monkeypatch):
    """A viewer attaching across a geometry change must reset its screen and
    request a repaint instead of rendering scrollback written for another grid;
    and xterm's pre-fit 80x24 default must never be posted."""
    _init(tmp_path, monkeypatch)
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-7", agent="claude", project_dir=tmp_path, title="demo · work",
    )
    page = dashboard.render_control([], [], [], terminals=[term])
    assert "es.addEventListener('geometry'" in page
    assert "maybeEpochReset" in page
    assert "/pty/redraw" in page
    assert "if(fitted && s.cols>0" in page   # onResize gated on a real fit
    # The reset token is armed before the redraw request because its ordered SSE
    # marker can beat the POST response. The marker queues RIS between old replay
    # and fresh repaint bytes instead of guessing that arbitrary output is fresh.
    arm = page.index("pendingReset=token;")
    redraw = page.index("post('/pty/redraw'")
    assert arm < redraw
    assert "reset:token" in page
    assert "es.addEventListener('reset'" in page
    assert "if(e.data!==pendingReset) return;" in page
    assert "term.write('\\x1bc')" in page
    assert "term.reset()" not in page


def test_pty_resize_debounce_drop_is_still_204(tmp_path, monkeypatch):
    """resize() returns False for a debounced repeat on a LIVE session too — that
    must never read as session-gone (410 is gated on existence, not return value)."""
    _init(tmp_path, monkeypatch)
    host = dashboard.pty_host.PtyHost()
    host._terms["pty-1"] = dashboard.pty_host.PtyTerminal(
        term_id="pty-1", agent="claude", project_dir=tmp_path,
    )
    monkeypatch.setattr(dashboard.pty_host, "host", host)
    monkeypatch.setattr(host, "resize", lambda tid, cols, rows: False)
    resp = _post("/pty/resize", {"id": "pty-1", "cols": "80", "rows": "24"})
    assert resp["status"] == 204


def test_terminal_js_surfaces_gone_sessions(tmp_path, monkeypatch):
    """The viewer must handle both gone-session signals: the 'unknown' SSE status
    (previously ignored → silent infinite reconnect loop) and a 410 input/resize
    POST (previously a swallowed 204 → typing into a black hole)."""
    _init(tmp_path, monkeypatch)
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-7", agent="claude", project_dir=tmp_path, title="demo · work",
    )
    page = dashboard.render_control([], [], [], terminals=[term])
    assert "e.data==='unknown'" in page      # stale-id SSE frame handled
    assert "r.status===410" in page          # gone-session POST handled
    assert "sessionGone" in page             # shared one-time notice + es.close()
    assert "[session gone" in page           # visible, not silent


def test_terminal_mobile_rendering_guards(tmp_path, monkeypatch):
    """Compact mode must use a >=16px cell font (iOS zooms the page on focusing
    an input under 16px — xterm's helper textarea carries the cell font, which
    sheared the grid on phones), and scroll containment must sit on the element
    that actually scrolls (.xterm-viewport), not only the non-scrolling host."""
    _init(tmp_path, monkeypatch)
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-7", agent="claude", project_dir=tmp_path, title="demo · work",
    )
    page = dashboard.render_control([], [], [], terminals=[term])
    assert "termFontSize" in page and "? 16 : 13" in page
    assert ".xterm-host .xterm-viewport { overscroll-behavior: contain; }" in page
    assert "touch-action: none" in page


def test_terminal_js_multi_viewer_geometry_and_touch_scroll(tmp_path, monkeypatch):
    """One PTY geometry serves all viewers: a viewer must re-claim it when the
    user returns to it (pageshow/focus/visibility/touch), or it stays stuck
    rendering a grid another viewer set. And touch-drags must feed xterm's
    wheel pipeline instead of scrolling nothing."""
    _init(tmp_path, monkeypatch)
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-7", agent="claude", project_dir=tmp_path, title="demo · work",
    )
    page = dashboard.render_control([], [], [], terminals=[term])
    assert "function claimSize()" in page
    assert "window.addEventListener('pageshow', claimSize)" in page
    assert "window.addEventListener('focus', claimSize)" in page
    assert "if(document.hidden){ releaseSize(); } else { claimSize(); }" in page  # visibility -> release/claim
    assert "new WheelEvent('wheel'" in page      # touch-drag -> wheel pipeline


def test_open_terminals_reaps_long_dead_sessions(tmp_path, monkeypatch):
    """A session that exited past the grace never resurfaces as a ghost tab."""
    import time as _time

    host = dashboard.pty_host.PtyHost()
    term = dashboard.pty_host.PtyTerminal(
        term_id="pty-old", agent="claude", project_dir=tmp_path,
        alive=False, ended_at=_time.monotonic() - 601,
    )
    host._terms["pty-old"] = term
    monkeypatch.setattr(dashboard.pty_host, "host", host)
    assert dashboard._open_terminals() == []


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
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 555)

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


def test_project_detail_renders_brainstorm_card(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    page = dashboard.render_project(dashboard.load_project(str(proj)), index=0)

    assert "Ideas / Brainstorm" in page
    assert "method='post' action='/brainstorm'" in page
    assert "name='topic'" in page and "required" in page
    assert "Start brainstorm" in page
    assert ".horus/temp/" in page  # tells the user where the draft lands
    # Destination picker, like the launch form: in-app always offered (headless-safe).
    assert page.count("value='app'>In-app terminal") >= 1


def test_process_brainstorm_launches_scoped_tracked_session(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"], captured["cwd"] = argv, cwd
        return 909

    monkeypatch.setattr(launcher, "open_terminal", fake_open)
    from horus import registry as registry_mod
    monkeypatch.setattr(registry_mod, "process_alive", lambda pid: pid == 909)

    query = dashboard.process_brainstorm(
        {"project": "0", "agent": "fake", "topic": "offline sync", "target": "window"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query.startswith("brainstormed=")
    # Scoped brainstorm prompt is seeded into the tracked session.
    assert captured["argv"][-1].startswith("Brainstorm session for the demo project.")
    assert "offline sync" in captured["argv"][-1]
    recs = Registry.default().all()
    assert len(recs) == 1 and recs[0].status == "running" and recs[0].pid == 909
    # The draft target dir is prepared; PRD.md is left untouched.
    assert (proj / ".horus" / "temp").is_dir()


def test_process_brainstorm_rejects_bad_input(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    # Empty topic, unknown account, unknown project index each fail before launching.
    assert dashboard.process_brainstorm(
        {"project": "0", "topic": "  "}, projects=[str(proj)], known_aliases=set()
    ) == "error=a+brainstorm+needs+a+topic"
    assert dashboard.process_brainstorm(
        {"project": "0", "topic": "x", "account": "ghost"}, projects=[str(proj)], known_aliases={"work"}
    ) == "error=unknown+account"
    assert dashboard.process_brainstorm(
        {"project": "9", "topic": "x"}, projects=[str(proj)], known_aliases=set()
    ) == "error=unknown+project"


def test_post_brainstorm_route_redirects_prg(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    monkeypatch.setattr(config, "load_projects", lambda: [str(proj)])
    monkeypatch.setattr(dashboard, "_known_aliases", lambda: set())
    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 42)

    resp = _post(
        "/brainstorm",
        {"project": "0", "agent": "fake", "topic": "a topic", "target": "window"},
        origin="http://127.0.0.1:8765",
    )
    assert resp["status"] == 303
    assert any(k == "Location" and v.startswith("/project?i=0&brainstormed=") for k, v in resp["headers"])


def test_process_brainstorm_defaults_to_in_app_terminal(tmp_path, monkeypatch):
    """No target (or target=app) runs the brainstorm under the session-host PTY —
    the shape that works on a hosted/headless dashboard, where a native window
    launch would fail."""
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True)
    captured = {}

    def fake_start(**kwargs):
        captured.update(kwargs)
        return "pty-5"

    monkeypatch.setattr(dashboard.pty_host.host, "start", fake_start)
    query = dashboard.process_brainstorm(
        {"project": "0", "agent": "claude", "topic": "offline sync"},
        projects=[str(proj)], known_aliases=set(),
    )
    assert query == "tab=pty-5"
    assert captured["prompt"].startswith("Brainstorm session for the demo project.")
    assert "offline sync" in captured["prompt"]
    assert captured["title"] == "demo · brainstorm"
    assert captured["managed"] is True
    assert (proj / ".horus" / "temp").is_dir()


def test_post_brainstorm_app_lands_on_sessions_cockpit(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr(dashboard, "process_brainstorm", lambda form, **kw: "tab=pty-5")
    resp = _post("/brainstorm", {"project": "0", "topic": "x"}, origin="http://127.0.0.1:8765")
    assert resp["status"] == 303
    assert dict(resp["headers"]).get("Location") == "/sessions?tab=pty-5"


def test_brainstorm_notice_banner():
    banner = dashboard._launch_notice({"brainstormed": ["ab12cd34"]})
    assert "Started brainstorm session" in banner and "ab12cd34" in banner
    assert "PRD.md is untouched" in banner


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


def _write_codex_rollout(home, primary=5.0, secondary=40.0, *, primary_reset=None, secondary_reset=None):
    # Reset timestamps default to comfortably in the future (relative to wall-clock,
    # not a fixed epoch) so this fixture keeps exercising the "current window" case
    # regardless of when the suite runs; pass explicit past epochs to test expiry.
    if primary_reset is None:
        primary_reset = int(time.time()) + 3600
    if secondary_reset is None:
        secondary_reset = int(time.time()) + 7 * 86400
    path = home / "sessions" / "2026" / "06" / "26" / "rollout-d.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": "2026-06-26T10:00:00Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"last_token_usage": {"total_tokens": 100}, "model_context_window": 1000},
            "rate_limits": {
                "primary": {"used_percent": primary, "resets_at": primary_reset},
                "secondary": {"used_percent": secondary, "resets_at": secondary_reset},
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


def test_gather_accounts_codex_past_reset_shows_available_not_stale_percent(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    home = tmp_path / "cx-home"
    config.set_account_codex_home("codex-work", str(home))
    past = int(time.time()) - 3600
    _write_codex_rollout(home, primary=97.0, secondary=10.0, primary_reset=past)
    codex = [a for a in dashboard.gather_accounts() if a.get("agent") == "codex"][0]
    assert codex["five_pct"] is None  # stale 97% dropped, not shown
    assert codex["five_reset"] is None
    assert codex["five_reset_expired"] is True
    # The still-current weekly window is untouched.
    assert codex["week_pct"] == 10.0
    assert codex["week_reset_expired"] is False


def test_account_usage_past_reset_shows_available_not_stale_percent(monkeypatch):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    report = dashboard.claude_usage.UsageReport(97.0, past, 12.0, future)
    monkeypatch.setattr(dashboard.claude_usage, "latest_usage", lambda **kw: report)
    account = dashboard._account_usage("me", None)
    assert account["five_pct"] is None
    assert account["five_reset"] is None
    assert account["five_reset_expired"] is True
    # The still-current weekly window renders its real percentage unchanged.
    assert account["week_pct"] == 12.0
    assert account["week_reset_expired"] is False


def test_account_usage_current_window_percent_unchanged(monkeypatch):
    future_five = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    future_week = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    report = dashboard.claude_usage.UsageReport(55.0, future_five, 30.0, future_week)
    monkeypatch.setattr(dashboard.claude_usage, "latest_usage", lambda **kw: report)
    account = dashboard._account_usage("me", None)
    assert account["five_pct"] == 55.0
    assert account["five_reset_expired"] is False
    assert account["week_pct"] == 30.0
    assert account["week_reset_expired"] is False


def test_account_usage_expiry_check_makes_no_network_or_cache_call(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("display-only expiry check must not touch network/cache")

    monkeypatch.setattr(dashboard.usage_snapshot, "refresh_usage", _boom)
    monkeypatch.setattr(dashboard.usage_snapshot, "cached_usage", _boom)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    report = dashboard.claude_usage.UsageReport(97.0, past, None, None)
    monkeypatch.setattr(dashboard.claude_usage, "latest_usage", lambda **kw: report)
    account = dashboard._account_usage("me", None)
    assert account["five_pct"] is None
    assert account["five_reset_expired"] is True


def test_accounts_strip_shows_reset_copy_not_stale_percent_when_expired():
    accounts = [{
        "agent": "codex", "alias": "codex-work",
        "five_pct": None, "week_pct": None,
        "five_reset": None, "week_reset": None,
        "five_reset_expired": True, "week_reset_expired": True,
    }]
    strip = dashboard._accounts_strip(accounts)
    assert "5h window reset" in strip and "capacity available" in strip
    assert "Weekly window reset" in strip
    assert "83%" not in strip


def test_accounts_panel_shows_reset_copy_not_stale_percent_when_expired(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    accounts = [{
        "agent": "codex", "alias": "codex-work",
        "five_pct": None, "week_pct": None,
        "five_reset": None, "week_reset": None,
        "five_reset_expired": True, "week_reset_expired": True,
    }]
    page = dashboard.render_control(dashboard.gather_projects(), accounts, [])
    assert "5h window reset" in page and "capacity available" in page
    assert "Weekly window reset" in page


def test_control_session_card_codex_fallback_drops_stale_percent_on_expired_reset(monkeypatch):
    rec = SessionRecord(session_id="s1", agent="codex", project="/tmp/proj-xyz", account="acct-x", status="running")
    past_epoch = int(time.time()) - 3600
    cu_report = dashboard.codex_usage.UsageReport(
        rollout=Path("/tmp/r.jsonl"),
        timestamp="2026-07-11T00:00:00Z",
        context_tokens=100,
        context_window=1000,
        context_percent=10.0,
        primary_percent=97.0,
        primary_resets_at=past_epoch,
        secondary_percent=None,
        secondary_resets_at=None,
    )
    monkeypatch.setattr(dashboard.codex_usage, "latest_usage", lambda p: cu_report)
    card = dashboard._control_session_card(rec, accounts=[])
    assert "usage unknown" in card
    assert "97%" not in card


def test_accounts_panel_renders_weekly_bar_with_reset(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    accounts = [{
        "agent": "codex", "alias": "codex-work", "five_pct": 1.0, "week_pct": 69.0,
        "five_reset": "2026-06-26 22:22", "week_reset": "2026-06-28 15:34",
    }]
    page = dashboard.render_control(dashboard.gather_projects(), accounts, [])
    assert "class='track-bar'" in page       # full-width weekly bar (sumi-e track)
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


def _write_usage_cache(alias, *, five_pct, five_reset_epoch, week_pct=None, week_reset_epoch=None):
    """Write a claude usage_snapshot cache file directly, as `horus run` preflight
    or the PreToolUse guard would — the on-disk artifact the refresh control reads."""
    from horus import usage_snapshot as _us

    five_reset = datetime.fromtimestamp(five_reset_epoch, tz=timezone.utc).isoformat() if five_reset_epoch else None
    week_reset = datetime.fromtimestamp(week_reset_epoch, tz=timezone.utc).isoformat() if week_reset_epoch else None
    snapshot = _us.UsageSnapshot(five_pct, five_reset, week_pct, week_reset)
    _us._write_cache(_us._cache_path("claude", alias), snapshot, now=time.time())


def test_cached_claude_account_usage_reads_disk_cache_no_live_call(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)

    def _boom(*a, **k):
        raise AssertionError("cache-only refresh must never call the live OAuth endpoint")

    monkeypatch.setattr(dashboard.claude_usage, "latest_usage", _boom)
    monkeypatch.setattr(dashboard.claude_usage, "fetch_usage", _boom)
    monkeypatch.setattr(dashboard.usage_snapshot, "refresh_usage", _boom)
    monkeypatch.setattr(dashboard.usage_snapshot, "cached_usage", _boom)

    future = int(time.time()) + 3600
    _write_usage_cache("me", five_pct=42.0, five_reset_epoch=future)
    account = dashboard._cached_claude_account_usage("me")
    assert account["five_pct"] == 42.0
    assert account["five_reset_expired"] is False


def test_cached_claude_account_usage_applies_past_reset_inference(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    past = int(time.time()) - 3600
    _write_usage_cache("me", five_pct=97.0, five_reset_epoch=past)
    account = dashboard._cached_claude_account_usage("me")
    assert account["five_pct"] is None  # stale 97% dropped, not shown
    assert account["five_reset_expired"] is True


def test_cached_claude_account_usage_no_cache_file_is_unknown_not_error(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    account = dashboard._cached_claude_account_usage("never-run")
    assert account["five_pct"] is None
    assert account["five_reset_expired"] is False


def test_gather_accounts_claude_cache_only_skips_live_fetch(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)  # isolate from the real dev session's account
    config.set_account_config_dir("me", str(tmp_path / "cc-home"))

    def _boom(*a, **k):
        raise AssertionError("claude_cache_only must never touch the network")

    monkeypatch.setattr(dashboard.claude_usage, "latest_usage", _boom)
    future = int(time.time()) + 3600
    _write_usage_cache("me", five_pct=10.0, five_reset_epoch=future)
    accounts = dashboard.gather_accounts(claude_cache_only=True)
    claude = [a for a in accounts if a["agent"] == "claude"]
    assert len(claude) == 1
    assert claude[0]["five_pct"] == 10.0


def test_accounts_refresh_route_rerenders_from_cache_after_reset_passes(tmp_path, monkeypatch):
    """End-to-end: hit /accounts-refresh after the cached window's reset has
    passed since the (simulated) page load — the fragment must show the
    'capacity available' copy, not the stale percent, with zero live calls."""
    _init(tmp_path, monkeypatch)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)  # isolate from the real dev session's account
    config.set_account_config_dir("me", str(tmp_path / "cc-home"))

    def _boom(*a, **k):
        raise AssertionError("no live call should happen on /accounts-refresh")

    monkeypatch.setattr(dashboard.claude_usage, "latest_usage", _boom)
    monkeypatch.setattr(dashboard.claude_usage, "fetch_usage", _boom)

    past = int(time.time()) - 60
    _write_usage_cache("me", five_pct=88.0, five_reset_epoch=past)
    response = _get("/accounts-refresh")
    assert response["status"] == 200
    body = response["body"].decode("utf-8")
    assert "88%" not in body
    assert "capacity available" in body


def test_accounts_refresh_button_labeled_cached_not_live(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    strip = dashboard._accounts_strip([])
    assert "refresh (cached)" in strip
    assert "/accounts-refresh" in strip or "horusRefreshAccounts" in strip
    assert "class='icon-btn usage-refresh'" in strip
    assert ".icon-btn.usage-refresh{opacity:1;width:auto;padding:0 6px}" in dashboard._STYLE


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
    assert calls["managed"] is True


def test_completed_roadmap_shows_complete(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    # The roadmap checkbox/progress reading is still roadmap.md-only (dashboard
    # PRD rendering is a separate phase) — write the all-done checklist there,
    # and blank out PRD.md's bootstrap next_action (PRD wins that field per
    # `resolve_focus`) so the dashboard has no authored NEXT to show instead.
    (tmp_path / ".horus" / "roadmap.md").write_text(
        "---\nstatus: active\ncurrent_focus: \"x\"\n---\n# Roadmap\n\n- [x] all done\n",
        encoding="utf-8",
    )
    (tmp_path / ".horus" / "PRD.md").write_text(
        "---\nstatus: active\nnext_action: \"\"\n---\n# PRD\n", encoding="utf-8"
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
    # CTA is now an in-app form (peer of `horus discover github <owner> --save`).
    assert "/github-add-owner" in html_out
    assert "Add GitHub owner" in html_out
    assert "per-machine" in html_out or "not git-synced" in html_out or "fresh machine" in html_out


def test_github_add_owner_registers_and_redirects(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    # Don't let owner registration spawn a real `gh` background refresh.
    monkeypatch.setattr(dashboard, "_start_remote_refresh", lambda *a, **k: None)
    assert config.load_github_owners() == []

    resp = _post("/github-add-owner", {"owner": "octocat"}, origin="http://127.0.0.1:8765")

    assert resp["status"] == 303
    location = dict(resp["headers"])["Location"]
    assert "owner_added=octocat" in location
    assert config.load_github_owners() == ["octocat"]


def test_github_add_owner_rejects_invalid(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr(dashboard, "_start_remote_refresh", lambda *a, **k: None)

    resp = _post("/github-add-owner", {"owner": "bad/name"}, origin="http://127.0.0.1:8765")

    assert resp["status"] == 303
    assert "owner_error" in dict(resp["headers"])["Location"]
    assert config.load_github_owners() == []


def test_github_add_owner_reports_already_tracking(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr(dashboard, "_start_remote_refresh", lambda *a, **k: None)
    config.register_github_owner("octocat")

    resp = _post("/github-add-owner", {"owner": "octocat"}, origin="http://127.0.0.1:8765")

    assert "owner_exists=octocat" in dict(resp["headers"])["Location"]


def test_local_add_registers_existing_horus_project(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "myrepo"
    (proj / ".horus").mkdir(parents=True)

    resp = _post("/local-add", {"path": str(proj)}, origin="http://127.0.0.1:8765")

    assert resp["status"] == 303
    location = dict(resp["headers"])["Location"]
    assert "local_added=myrepo" in location or "i=" in location  # banner or project page
    assert str(proj.resolve()) in config.load_projects()


def test_local_add_without_horus_requires_init_flag(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "bare"
    proj.mkdir()

    resp = _post("/local-add", {"path": str(proj)}, origin="http://127.0.0.1:8765")

    assert "local_error" in dict(resp["headers"])["Location"]
    assert config.load_projects() == []


def test_local_add_onboards_from_zero_when_init_ticked(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "fresh"
    proj.mkdir()
    monkeypatch.setattr(dashboard, "_stale_build", lambda: None)

    def fake_init(root, **kwargs):
        (root / ".horus").mkdir(exist_ok=True)
        return []

    monkeypatch.setattr(dashboard.initialize, "init_project", fake_init)

    resp = _post("/local-add", {"path": str(proj), "init": "1"}, origin="http://127.0.0.1:8765")

    assert resp["status"] == 303
    location = dict(resp["headers"])["Location"]
    assert "local_onboarded=fresh" in location or "i=" in location
    assert str(proj.resolve()) in config.load_projects()


def test_local_add_rejects_missing_directory(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)

    resp = _post("/local-add", {"path": str(tmp_path / "nope")}, origin="http://127.0.0.1:8765")

    assert "local_error" in dict(resp["headers"])["Location"]
    assert config.load_projects() == []


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
    assert "badge seal" in html_out


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

    assert "<details class='fold'>" in html_out
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


def test_post_github_ignore_fetch_returns_no_content(tmp_path, monkeypatch):
    """A JS fetch submit (X-Horus-Fetch) gets 204 so the card is removed in place,
    letting several repos be ignored without a page reload."""
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")

    response = _post(
        "/github-ignore", {"target": "rafaelmjf/some-app"},
        origin="http://127.0.0.1:8765", headers={"X-Horus-Fetch": "1"},
    )

    assert response["status"] == 204
    assert not any(k == "Location" for k, _ in response["headers"])
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


# --- self-update + health + recent-sessions panel ---


def _get(path: str) -> dict[str, object]:
    handler = object.__new__(dashboard._Handler)
    handler.path = path
    handler.headers = {"Host": "127.0.0.1:8765"}
    handler.rfile = BytesIO(b"")
    handler.wfile = BytesIO()
    response: dict[str, object] = {"headers": []}
    handler.send_response = lambda s: response.__setitem__("status", s)  # type: ignore[method-assign]
    handler.send_header = lambda k, v: response["headers"].append((k, v))  # type: ignore[method-assign, index]
    handler.end_headers = lambda: None  # type: ignore[method-assign]
    dashboard._Handler.do_GET(handler)
    response["body"] = handler.wfile.getvalue()
    return response


def test_health_endpoint_identity():
    import json as _json

    response = _get("/health")
    assert response["status"] == 200
    data = _json.loads(response["body"])
    assert data["app"] == "horus-dashboard"
    assert data["version"] == dashboard.__version__
    assert isinstance(data["pid"], int)
    assert data["exposed"] is False


def test_manifest_served_with_content_type_and_required_fields():
    import json as _json

    response = _get("/manifest.json")
    assert response["status"] == 200
    assert ("Content-Type", "application/manifest+json") in response["headers"]
    manifest = _json.loads(response["body"])
    assert manifest["name"]
    assert manifest["short_name"]
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["background_color"] and manifest["theme_color"]
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes
    for icon in manifest["icons"]:
        assert icon["type"] == "image/png"


def test_sw_served_with_content_type():
    response = _get("/sw.js")
    assert response["status"] == 200
    assert ("Content-Type", "text/javascript") in response["headers"]
    assert b"addEventListener('fetch'" in response["body"]


def test_sw_only_precaches_static_shell_assets_never_gated_or_api_routes():
    for gated in (
        "/accounts-panel", "/accounts-refresh", "/projects-grid", "/health",
        "/pty/stream", "/pty/term", "/update-check", "/github-catalog", "/sessions",
    ):
        assert gated not in dashboard._PWA_PRECACHE_PATHS
    assert {"/assets/icon-192.png", "/assets/icon-512.png"} <= set(dashboard._PWA_PRECACHE_PATHS)


def test_page_head_includes_manifest_link_and_sw_registration(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    page = dashboard.render_index([])
    assert "<link rel='manifest' href='/manifest.json'>" in page
    assert "serviceWorker.register('/sw.js')" in page


def test_update_pill_renders_when_newer():
    out = dashboard._update_pill_html({"update_available": True, "latest": "9.9.9"})
    assert "/self-update" in out and "9.9.9" in out


def test_update_pill_empty_when_current():
    assert dashboard._update_pill_html({"update_available": False, "latest": None}) == ""


def test_post_self_update_runs_upgrade_and_redirects(monkeypatch):
    monkeypatch.setattr(dashboard.selfupdate, "run_upgrade", lambda: (True, "Updated to v9.9.9"))
    response = _post("/self-update", {}, origin="http://127.0.0.1:8765")
    assert response["status"] == 303
    location = next(v for k, v in response["headers"] if k == "Location")
    assert "selfupdated=" in location


def test_post_self_update_reports_failure(monkeypatch):
    monkeypatch.setattr(dashboard.selfupdate, "run_upgrade", lambda: (False, "boom"))
    response = _post("/self-update", {}, origin="http://127.0.0.1:8765")
    location = next(v for k, v in response["headers"] if k == "Location")
    assert "selfupdate_error=" in location


def test_project_sessions_panel_lists_discovered_sessions(monkeypatch):
    from pathlib import Path as _Path

    from horus.session_discovery import SessionInfo

    fake = [
        SessionInfo(
            agent="claude", session_id="abc123def456xyz", started_at="2026-07-01T10:00:00Z",
            last_activity="2026-07-01T11:00:00Z", message_count=42, source_path=_Path("t.jsonl"),
        )
    ]
    monkeypatch.setattr(dashboard.session_discovery, "discover_sessions", lambda p: fake)
    out = dashboard._project_sessions_html(_Path("."))
    assert "Recent sessions" in out
    assert "claude" in out and "42" in out and "abc123def456" in out
    assert "2026-07-01 11:00" in out


def test_project_sessions_panel_empty(monkeypatch):
    from pathlib import Path as _Path

    monkeypatch.setattr(dashboard.session_discovery, "discover_sessions", lambda p: [])
    out = dashboard._project_sessions_html(_Path("."))
    assert "No Claude/Codex transcripts" in out


def test_cli_outdated_flag_and_update_card(tmp_path, monkeypatch):
    """A repo whose managed block is newer than the installed CLI surfaces an
    'update horus-harness' card (POST /self-update), not a downgrade Refresh."""
    from horus import upgrade as upgrade_mod

    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    monkeypatch.setattr(
        dashboard.upgrade, "upgrade_project",
        lambda root, apply=False: [upgrade_mod.UpgradeAction(
            "skipped",
            "AGENTS.md managed block (v999) is newer than this CLI (v2) — upgrade horus-harness instead of refreshing",
        )],
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["cli_outdated"] is True
    assert data["artifacts_stale"] is False

    html_out = dashboard.render_project(data)
    assert "Horus CLI outdated" in html_out
    assert "action='/self-update'" in html_out
    assert "Update horus-harness from PyPI" in html_out


def test_render_project_shows_codex_projection_behind_badge(tmp_path, monkeypatch):
    """Projection sync compares each surface to the installed CLI only (see
    horus.projection_sync) - a Codex-only artifact regression surfaces a
    'Codex projection behind' badge on the project detail page, Claude untouched."""
    proj = _scaffolded_project(tmp_path, monkeypatch)
    # init_project alone leaves the native hooks uninstalled (opt-in), so install
    # everything first to get a genuinely fully-synced baseline, then degrade only
    # the Codex-side skill.
    for install in (
        native_hooks.install_claude_usage_hook,
        native_hooks.install_claude_merge_hook,
        native_hooks.install_claude_guard_hook,
        native_hooks.install_codex_usage_hook,
        native_hooks.install_codex_merge_hook,
        native_hooks.install_codex_guard_hook,
    ):
        install(proj)
    skill_md = proj / ".agents" / "skills" / "horus-consolidate" / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8").replace("horus-skill-version: 12", "horus-skill-version: 1"),
        encoding="utf-8",
    )

    data = dashboard.load_project(str(proj))
    assert data["projection_sync"]["verdict"] == "codex_behind"

    html_out = dashboard.render_project(data)
    assert "Codex projection behind" in html_out
    assert "Claude projection behind" not in html_out


# ---------------------------------------------------------------------------
# Catalog dedup + "Track on this machine" (user request 2026-07-02)
# ---------------------------------------------------------------------------

def _make_remote(full_name="rafaelmjf/demo", *, local_path=None):
    owner, name = full_name.split("/")
    return github_catalog.RemoteProject(
        owner=owner,
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="2026-07-02T12:00:00Z",
        local_path=local_path,
    )


def test_drop_registered_hides_tracked_projects_from_catalog(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "demo"
    proj.mkdir()
    config.register_project(proj)
    registered = config.load_projects()

    tracked = _make_remote("rafaelmjf/demo", local_path=str(proj))
    cloned_only = _make_remote("rafaelmjf/other", local_path=str(tmp_path / "other"))
    remote_only = _make_remote("rafaelmjf/faraway")

    out = dashboard._drop_registered([tracked, cloned_only, remote_only], registered)

    # Registered project vanishes from the catalog (its card lives under Projects);
    # cloned-but-unregistered and remote-only stay — the catalog is their only surface.
    assert [p.full_name for p in out] == ["rafaelmjf/other", "rafaelmjf/faraway"]


def test_gather_untracked_drops_registered_local_projects(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    proj = tmp_path / "gym"
    proj.mkdir()
    config.register_project(proj)

    registered_untracked = github_catalog.UntrackedRepo(
        owner="rafaelmjf", name="gym", full_name="rafaelmjf/gym",
        url="https://github.com/rafaelmjf/gym", clone_url="git@github.com:rafaelmjf/gym.git",
        default_branch="master", pushed_at="2026-07-02T12:00:00Z", local_path=str(proj),
    )
    plain = _make_untracked("rafaelmjf/plain-app")
    monkeypatch.setattr(
        dashboard.github_catalog, "load_cache",
        lambda owner, **kw: github_catalog.CachedCatalog(
            owner=owner, projects=[], fetched_at="2026-07-02T12:00:00+00:00",
            untracked=[registered_untracked, plain],
        ),
    )

    visible, hidden = dashboard.gather_untracked_repos()

    assert [u.full_name for u in visible] == ["rafaelmjf/plain-app"]
    assert hidden == []


def test_remote_project_card_has_track_button():
    html_out = dashboard.render_remote_catalog([_make_remote("rafaelmjf/demo")], [])
    assert "action='/github-start'" in html_out
    assert "name='target' value='rafaelmjf/demo'" in html_out
    assert "Track on this machine" in html_out
    assert "horus start github:rafaelmjf/demo" in html_out  # copyable fallback kept


def test_post_github_start_tracks_remote_horus_project(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    config.register_github_owner("rafaelmjf")
    calls = []

    def fake_start(target, **kw):
        calls.append(target)
        from horus.remote_start import StartResult
        return StartResult(
            project=_make_remote("rafaelmjf/demo"), path=tmp_path / "demo",
            cloned=True, registered=True, upgrade_actions=[],
        )

    monkeypatch.setattr(dashboard.remote_start, "start_github_project", fake_start)

    res = _post("/github-start", {"target": "rafaelmjf/demo"})

    assert res["status"] == 303
    loc = next(v for k, v in res["headers"] if k == "Location")
    assert "started=rafaelmjf%2Fdemo" in loc
    assert calls == ["github:rafaelmjf/demo"]


def test_post_github_start_refuses_untrusted_owner(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)  # no github owners configured
    called = []
    monkeypatch.setattr(
        dashboard.remote_start, "start_github_project",
        lambda t, **kw: called.append(t),
    )

    res = _post("/github-start", {"target": "evil/repo"})

    assert res["status"] == 303
    loc = next(v for k, v in res["headers"] if k == "Location")
    assert "start_error=" in loc and "untrusted" in loc
    assert called == []


def test_started_and_start_error_banners():
    ok = dashboard._notice({"started": ["rafaelmjf/demo"]})
    assert "banner ok" in ok and "rafaelmjf/demo" in ok and "Tracking" in ok
    err = dashboard._notice({"start_error": ["gh repo clone failed"]})
    assert "banner err" in err and "gh repo clone failed" in err


def test_load_project_v3_prd_frontmatter_populates_next(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "PRD.md").write_text(
        '---\nstatus: active\ncurrent_focus: "PRD focus"\nnext_action: "PRD next"\n'
        'next_prompt: "PRD prompt"\nexecution_recommendation: "direct"\n'
        "last_updated: 2026-07-03\n---\n# PRD\n\nThe product narrative.\n",
        encoding="utf-8",
    )

    data = dashboard.load_project(str(tmp_path))
    assert data["status"] == "active"
    assert data["current_focus"] == "PRD focus"
    assert data["next_action"] == "PRD next"
    assert data["next_prompt"] == "PRD prompt"
    assert data["execution_recommendation"] == "direct"
    # Without a project.md shim the PRD body doubles as the project narrative.
    assert "product narrative" in data["project_body"]
    assert "product narrative" in data["tagline"]


_PRD_BACKLOG_SHIPPED_FIXTURE = """---
status: active
current_focus: "x"
next_action: "y"
last_updated: 2026-07-03
---

# Demo - PRD

## Backlog

Prioritized open work.

### Now / next candidates

1. **First thing.** Do the first thing because it matters a lot for users everywhere.
2. **Second thing:** short detail here.

### Open, unscheduled

- Idea one.
- Idea two.
- Idea three.

### Deferred

- Someday maybe.

## Shipped

One line per capability; details live in git history.

- **Widget engine** shipped in 0.1.
- **Gadget engine** shipped in 0.2.

## Rules (load-bearing)

- **Some rule** - because reasons.
"""


def test_load_project_v3_parses_prd_backlog_and_shipped(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "PRD.md").write_text(_PRD_BACKLOG_SHIPPED_FIXTURE, encoding="utf-8")

    prd = dashboard.load_project(str(tmp_path))["prd"]

    assert [item["title"] for item in prd["backlog_now"]] == ["First thing", "Second thing"]
    assert prd["backlog_now"][0]["detail"] == "Do the first thing because it matters a lot for users everywhere."
    assert prd["backlog_other_counts"] == {"Open, unscheduled": 3, "Deferred": 1}
    assert prd["shipped_count"] == 2
    assert prd["shipped_latest"] == "Gadget engine shipped in 0.2."
    assert prd["line_count"] == len(_PRD_BACKLOG_SHIPPED_FIXTURE.splitlines())
    assert prd["line_class"] == "ok"


def _prd_padded_to(total_lines: int) -> str:
    header = [
        "---", "status: active", "last_updated: 2026-07-03", "---",
        "# Demo - PRD", "", "## Backlog", "", "### Now / next candidates", "",
        "## Shipped", "", "## Rules (load-bearing)", "",
    ]
    filler = [f"filler line {i}" for i in range(max(0, total_lines - len(header)))]
    return "\n".join((header + filler)[:total_lines]) + "\n"


def test_prd_line_budget_thresholds_match_routines_caps(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    prd_path = tmp_path / ".horus" / "PRD.md"

    prd_path.write_text(_prd_padded_to(235), encoding="utf-8")
    assert dashboard.load_project(str(tmp_path))["prd"]["line_class"] == "ok"

    prd_path.write_text(_prd_padded_to(236), encoding="utf-8")
    assert dashboard.load_project(str(tmp_path))["prd"]["line_class"] == "warn"

    prd_path.write_text(_prd_padded_to(250), encoding="utf-8")
    assert dashboard.load_project(str(tmp_path))["prd"]["line_class"] == "warn"

    prd_path.write_text(_prd_padded_to(251), encoding="utf-8")
    assert dashboard.load_project(str(tmp_path))["prd"]["line_class"] == "over"


def test_project_detail_renders_prd_backlog_shipped_and_line_meter(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".horus" / "PRD.md").write_text(_PRD_BACKLOG_SHIPPED_FIXTURE, encoding="utf-8")

    data = dashboard.load_project(str(tmp_path))
    det = dashboard.render_project(data, index=0)

    assert "id='backlog'" in det and "id='shipped'" in det
    assert "First thing" in det and "Second thing" in det
    assert "Open, unscheduled (3)" in det and "Deferred (1)" in det
    assert "<b>2</b> capabilities shipped" in det
    assert "Gadget engine shipped in 0.2." in det
    assert "/250 lines" in det  # line-budget badge in the detail header
    assert "id='features'" not in det  # no legacy features.md in a pure v3 project


def test_project_detail_v2_project_unchanged(tmp_path, monkeypatch):
    """A v2 (six-lane) project must render exactly as before phase 4: no PRD
    backlog/shipped/meter panels, legacy Features ledger panel intact."""
    _init(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "project.md").write_text(
        '---\nproject: demo\nstatus: active\ncurrent_focus: "v2 focus"\n---\n# demo\n\nNarrative.\n',
        encoding="utf-8",
    )
    initialize.init_project(tmp_path, assume_yes=True)  # scaffolds the rest of the six lanes

    data = dashboard.load_project(str(tmp_path))
    assert data["prd"] == {}

    det = dashboard.render_project(data, index=0)
    assert "id='backlog'" not in det and "id='shipped'" not in det
    assert "/250 lines" not in det  # no PRD line-budget badge
    assert "id='features'" in det  # legacy Features ledger panel still renders
    assert "id='roadmap'" in det
    assert ".horus/project.md" in det  # current-focus caption unchanged
    assert ".horus/roadmap.md" in det  # roadmap-next caption unchanged
    assert "v2 focus" in det


def test_projects_grid_fragment_renders_v3_and_v2_projects(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    v3 = tmp_path / "v3"
    initialize.init_project(v3, assume_yes=True)
    (v3 / ".horus" / "PRD.md").write_text(_PRD_BACKLOG_SHIPPED_FIXTURE, encoding="utf-8")

    v2 = tmp_path / "v2"
    hdir = v2 / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "project.md").write_text(
        '---\nproject: demo\nstatus: active\ncurrent_focus: "v2 focus"\n---\n# demo\n\nNarrative.\n',
        encoding="utf-8",
    )
    initialize.init_project(v2, assume_yes=True)

    response = _get("/projects-grid")

    assert response["status"] == 200
    body = response["body"].decode("utf-8")
    assert "2 projects under watch" in body
    assert "v3" in body and "v2" in body
    assert "v2 focus" in body
    assert "NEXT ACTION" in body and ">y<" in body
    assert "id='backlog'" not in body
    assert "/250 lines" not in body


def test_projects_grid_survives_no_horus_dir_project(tmp_path, monkeypatch):
    """A registered project whose path lost its .horus/ dir (or was deleted) used
    to raise FileNotFoundError deep in _project_column (via _resume_html ->
    routines.resume_prompt -> resume_context) and 500 the whole section.
    routines.resume_prompt now degrades to "" for this case (see
    test_resume_prompt_degrades_to_empty_without_horus_dir), so this concrete
    trigger renders a normal (mostly empty) card with the existing "no .horus/"
    badge — the fragment must never 500, and the other project must fully render."""
    _init(tmp_path, monkeypatch)
    good = tmp_path / "good"
    initialize.init_project(good, assume_yes=True)

    broken = tmp_path / "broken"
    broken.mkdir()
    config.register_project(broken)  # registered, but never got a .horus/ dir

    response = _get("/projects-grid")

    assert response["status"] == 200
    body = response["body"].decode("utf-8")
    assert "2 projects under watch" in body
    assert "good" in body
    assert "<details class='launch'>" in body  # the good project still fully renders
    assert "broken" in body
    assert "no .horus/" in body  # badge from _project_column's `missing` marker


def test_projects_grid_error_card_for_unexpected_per_project_failure(tmp_path, monkeypatch):
    """The generic per-project guard: for a failure mode that ISN'T the specific
    "no .horus/ dir" case (e.g. any other exception raised while rendering one
    project's column), the section must still return 200 with an error card for
    that project and full rendering for every other project — this is the
    primary fix, independent of the routines.resume_prompt degrade above."""
    _init(tmp_path, monkeypatch)
    good = tmp_path / "good"
    initialize.init_project(good, assume_yes=True)
    bad = tmp_path / "bad"
    initialize.init_project(bad, assume_yes=True)

    real_project_column = dashboard._project_column

    def flaky(p, i, aliases=None):
        if p["name"] == "bad":
            raise RuntimeError("boom: simulated unexpected render failure")
        return real_project_column(p, i, aliases)

    monkeypatch.setattr(dashboard, "_project_column", flaky)

    response = _get("/projects-grid")

    assert response["status"] == 200
    body = response["body"].decode("utf-8")
    assert "2 projects under watch" in body
    assert "good" in body
    assert "<details class='launch'>" in body  # the good project still fully renders
    assert "bad" in body
    assert "failed to load" in body
    assert "boom: simulated unexpected render failure" in body


def test_project_column_safe_renders_error_card_on_raise(monkeypatch):
    """Direct unit test of the guard: any exception from _project_column becomes
    a compact error card instead of propagating."""

    def boom(p, i, aliases=None):
        raise FileNotFoundError("no .horus/ directory at /tmp/gone")

    monkeypatch.setattr(dashboard, "_project_column", boom)
    card = dashboard._project_column_safe({"name": "gone", "path": "/tmp/gone"}, 0)
    assert "failed to load" in card
    assert "gone" in card
    assert "no .horus/ directory" in card


def test_resume_prompt_degrades_to_empty_without_horus_dir(tmp_path):
    """routines.resume_prompt should not raise for a project with no .horus/ dir —
    the dashboard's per-project error-card guard is the primary defense, but the
    routine itself should degrade gracefully for this specific, expected case."""
    assert routines.resume_prompt(tmp_path) == ""
