"""Horus command-line entry point."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from horus import (
    __version__,
    adapters,
    claude_usage,
    closure,
    companion,
    codex_usage,
    config,
    dashboard,
    gitstate,
    initialize,
    launch,
    launcher,
    native_hooks,
    registry,
    routines,
    skills,
    templates,
)
from horus.continuity import HORUS_DIR, SESSIONS_DIR, check_project
from horus.instructions import check_drift, reconcile

_LEVEL_TAG = {"ok": "[ ok ]", "warn": "[warn]", "fail": "[fail]"}


def _skill_targets(value: str) -> tuple[str, ...]:
    return ("claude", "codex") if value == "all" else (value,)


def _print_findings(findings) -> bool:
    """Print findings; return True if all good (no warn/fail)."""
    healthy = True
    for f in findings:
        print(f"  {_LEVEL_TAG.get(f.level, '[????]')} {f.message}")
        if f.level in ("warn", "fail"):
            healthy = False
    return healthy


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    print(f"Initializing Horus continuity in {root}")
    actions = initialize.init_project(
        root,
        assume_yes=args.yes,
        no_input=args.no_input,
        with_skills=not args.no_skills,
        skill_targets=_skill_targets(args.skill_target),
    )
    for a in actions:
        print(f"  [{a.status}] {a.message}")
    skipped = [a for a in actions if a.status == "skipped"]
    if skipped:
        print(f"\n{len(skipped)} item(s) skipped. Rerun with --yes to apply.")
    print("\nDone.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    rc = 0

    if args.target in ("project", "all"):
        print(f"doctor project: {root}")
        if not _print_findings(check_project(root) + skills.skill_findings(root, targets=("claude", "codex"))):
            rc = 1
        print()

    if args.target in ("instructions", "all"):
        print(f"doctor instructions: {root}")
        agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
        if not agents.exists() or not claude.exists():
            missing = [p.name for p in (agents, claude) if not p.exists()]
            print(f"  {_LEVEL_TAG['fail']} missing file(s): {', '.join(missing)}")
            rc = 1
        else:
            report = check_drift(
                agents.read_text(encoding="utf-8"), "AGENTS.md",
                claude.read_text(encoding="utf-8"), "CLAUDE.md",
            )
            if report.status == "aligned":
                print(f"  {_LEVEL_TAG['ok']} {report.detail}")
            elif report.status == "missing":
                print(f"  {_LEVEL_TAG['fail']} {report.detail}")
                rc = 1
            else:
                print(f"  {_LEVEL_TAG['warn']} managed blocks drifted:")
                for line in report.detail.splitlines():
                    print(f"      {line}")
                rc = 1
        print()

    return rc


def cmd_dashboard(args: argparse.Namespace) -> int:
    dashboard.serve(host=args.host, port=args.port)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Headless peer of the dashboard overview: git freshness + latest session."""
    projects = config.load_projects()
    if not projects:
        print("No projects registered (run `horus init` inside a project).")
        return 0
    for path in projects:
        p = dashboard.load_project(path)
        git = gitstate.summary(p.get("git")) or "not a git repo"
        latest = p.get("latest")
        if latest:
            label = latest.get("summary") or latest.get("file", "")
            sess = f"{latest.get('date', '')} — {label}".strip(" —")
        else:
            sess = "no sessions"
        print(f"{p['name']}\n  git:  {git}\n  last: {sess}")
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    """List tracked agent sessions, reconciling live state against real PIDs first."""
    reg = registry.Registry.default()
    reg.reconcile()  # correct records left "running" by a crashed/closed run
    if args.prune:
        removed = reg.prune()
        print(f"Pruned {len(removed)} finished session(s).")
        return 0
    records = sorted(reg.all(), key=lambda r: r.updated_at, reverse=True)
    if not records:
        print("No tracked sessions.")
        return 0
    for r in records:
        proj = Path(r.project).name
        rc = "" if r.returncode is None else f" rc={r.returncode}"
        print(f"{r.status:<8} {r.agent:<7} {r.account or '-':<14} {proj:<24} pid={r.pid or '-'} {r.session_id}{rc}")
    return 0


def cmd_focus(args: argparse.Namespace) -> int:
    """Raise a running session's terminal window (the dashboard can't, being read-only).

    Matches a session id by prefix (like git short hashes). Best-effort: Windows-only
    window raising, subject to the OS foreground lock and to how the session's terminal
    is hosted (see ``launcher.focus_window_for_pid``).
    """
    reg = registry.Registry.default()
    reg.reconcile()
    matches = [r for r in reg.all() if r.session_id.startswith(args.session_id)]
    if not matches:
        print(f"No session matching {args.session_id!r}. Run `horus sessions` to list them.")
        return 2
    if len(matches) > 1:
        print(f"{args.session_id!r} is ambiguous ({len(matches)} sessions); use more of the id.")
        return 2
    rec = matches[0]
    if rec.status != "running":
        print(f"Session {rec.session_id[:8]} is {rec.status}, not running — nothing to focus.")
        return 1
    if launcher.focus_window_for_pid(rec.pid):
        print(f"Focused {rec.agent} session {rec.session_id[:8]} (pid {rec.pid}).")
        return 0
    print(
        f"Could not raise the window for pid {rec.pid}. It may be hosted in a shared "
        "terminal process, or the OS blocked the foreground change. Try the taskbar, "
        f"or reopen with `claude --resume {rec.session_id}` in {Path(rec.project).name}."
    )
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Spawn (or resume) an agent session through an adapter, tracked in the registry.

    Streams the session's events to stdout and records it so it shows up in
    `horus sessions` and the dashboard's Live sessions card.
    """
    root = Path(args.path).resolve()
    try:
        adapter = adapters.get_adapter(args.agent)
    except KeyError as exc:
        print(exc)
        return 2

    spec = adapters.SpawnSpec(
        prompt=args.prompt,
        project_dir=root,
        account=args.account,
        posture=adapters.PermissionPosture(args.posture),
        model=args.model,
    )
    reg = registry.Registry.default()
    try:
        run = adapter.resume(args.resume, spec) if args.resume else adapter.spawn(spec)
    except adapters.AccountMismatch as exc:
        print(f"Refusing to run: {exc}")
        return 2

    for ev in registry.track(reg, run):
        if ev.type is adapters.EventType.SESSION_STARTED:
            print(f"... session {ev.session_id}")
        elif ev.type is adapters.EventType.ASSISTANT_TEXT and ev.text:
            print(ev.text)
        elif ev.type is adapters.EventType.TOOL_USE:
            print(f"  [tool] {ev.tool}")
        elif ev.type is adapters.EventType.ERROR:
            print(f"  [error] {ev.text or ''}")

    s = run.session
    print(f"\n{s.status} — session {s.session_id} (account {s.account or '-'})")
    return 0 if s.status == "exited" else 1


def cmd_open(args: argparse.Namespace) -> int:
    """Open an *attended* agent session in its own terminal window, tracked as running.

    The interactive counterpart to `horus run`: launches the CLI's TUI (the user
    types in it) under a chosen account + project, and registers it so it shows as
    a live `running` session in `horus sessions` and the dashboard. Shares the
    launch path with the dashboard's Control-tab buttons (`horus.launch`).
    """
    result = launch.launch_interactive(
        agent=args.agent,
        project_dir=args.path,
        account=args.account,
        posture=args.posture,
        model=args.model,
        prompt=args.prompt or "",
    )
    if not result.ok:
        print(f"Refusing to open: {result.error}")
        return 2
    print(f"Opened {result.agent} session in {result.project.name} as {result.account or 'ambient'} "
          f"(pid {result.pid}, session {result.session_id}).")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if config.unregister_project(root):
        print(f"Removed from registry: {root}")
        return 0
    print(f"Not in registry: {root}")
    return 1


def cmd_prune(args: argparse.Namespace) -> int:
    removed = config.prune_projects()
    if not removed:
        print("Nothing to prune; all registered projects still have a .horus/ directory.")
        return 0
    print(f"Pruned {len(removed)} stale project(s):")
    for p in removed:
        print(f"  - {p}")
    return 0


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "session"


def cmd_session(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    sessions = root / HORUS_DIR / SESSIONS_DIR
    if not (root / HORUS_DIR).is_dir():
        print(f"No {HORUS_DIR}/ here (run `horus init` first).")
        return 1
    sessions.mkdir(parents=True, exist_ok=True)

    # Timestamp (not just date): multiple sessions a day must not collide or lose
    # their order. Account tag anchors which Claude user the session ran under.
    now = datetime.now()
    path = sessions / f"{now:%Y-%m-%d-%H%M%S}-{_slugify(args.title)}.md"
    if path.exists():
        print(f"Already exists: {path}")
        return 1
    # Record the alias, never the raw email: session content distills into the
    # committed lanes, so the real identifier must not land in the summary.
    account = args.account or config.alias_for(claude_usage.current_account()) or "unknown"
    path.write_text(
        templates.session_summary(
            title=args.title,
            date=now.strftime("%Y-%m-%dT%H:%M:%S"),
            project=root.name,
            agent=args.agent,
            account=account,
            environment=args.environment,
        ),
        encoding="utf-8",
    )
    print(f"Created {path}")
    return 0


def cmd_account(args: argparse.Namespace) -> int:
    # Account detection is Claude-specific for now (reads ~/.claude.json); other
    # agents fall through to "not detected" until they get their own reader.
    identifier = claude_usage.current_account() if args.agent == "claude" else None

    if args.alias:
        if not identifier:
            print(f"No {args.agent} account detected; nothing to alias (is the agent logged in?).")
            return 1
        config.set_account_alias(identifier, args.alias)
        print(f"Aliased {args.agent} account -> {args.alias}")
        return 0

    if args.set_dir is not None:
        # Map an alias to its CLAUDE_CONFIG_DIR for per-account isolation. Use the
        # explicit --alias-name, else the current account's resolved alias.
        target = args.alias_name or config.alias_for(identifier)
        if not target:
            print("No account to map (pass --alias-name, or log in so an alias can be resolved).")
            return 1
        config.set_account_config_dir(target, args.set_dir)
        print(f"Mapped account {target!r} -> CLAUDE_CONFIG_DIR {args.set_dir}")
        return 0

    if not identifier:
        print(f"No {args.agent} account detected (is the agent logged in?).")
        return 1
    alias = config.alias_for(identifier)
    print(f"agent:   {args.agent}")
    print(f"account: {identifier}")
    print(f"alias:   {alias}")
    config_dirs = config.load_account_config_dirs()
    if alias in config_dirs:
        print(f"config:  {config_dirs[alias]}")
    if not config.load_account_aliases().get(identifier):
        print("(auto-generated alias; set a friendly one with `horus account --set <name>`)")
    if config_dirs:
        print(f"isolated accounts: {', '.join(sorted(config_dirs))}")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    print(f"Closure check: {root}\n")
    findings = closure.closure_status(root, usage_threshold=args.usage_threshold)
    healthy = _print_findings(findings)

    if args.commit:
        did, detail = closure.commit_continuity(root, args.message, push=args.push)
        print(f"\n--commit: {detail}")
        if did:
            # The commit clears the "uncommitted continuity" warning.
            healthy = not any(
                f.level in ("warn", "fail")
                for f in findings
                if "uncommitted continuity" not in f.message
            )

    print("\n" + templates.CLOSURE_PROMPT)
    if healthy:
        print("Continuity captured — ready to start a fresh session from `.horus/`.")
        return 0
    print("Action needed before closing — see the warnings above.")
    return 1


def _read_hook_stdin() -> dict:
    """Parse the JSON a native app pipes to a hook command (empty when run by hand)."""
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _usage_check_claude(args: argparse.Namespace) -> int:
    report = claude_usage.latest_usage()
    findings = claude_usage.usage_findings(threshold=args.threshold, report=report)

    if not args.hook:
        healthy = _print_findings(findings)
        return 0 if healthy else 1

    # Hook mode: drive the session into the closure routine when over budget.
    if not claude_usage.is_over_threshold(args.threshold, report):
        return 0
    hook_input = _read_hook_stdin()
    if hook_input.get("stop_hook_active"):  # we already triggered a Stop continuation
        return 0
    session_id = str(hook_input.get("session_id", "unknown"))
    if native_hooks.closure_already_fired(session_id):  # re-arm window: avoid loops/nagging
        return 0
    native_hooks.mark_closure_fired(session_id)

    instruction = templates.USAGE_CLOSURE_INSTRUCTION
    event = hook_input.get("hook_event_name", "Stop")
    if event == "UserPromptSubmit":
        # Pre-task: inject the closure directive as context BEFORE the agent starts the
        # requested work, so an over-budget session closes instead of beginning it.
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": instruction}
        }))
    else:  # Stop: block the stop and feed the directive back as the next instruction.
        print(json.dumps({"decision": "block", "reason": instruction}))
    return 0


def cmd_usage_check(args: argparse.Namespace) -> int:
    if args.target == "claude":
        return _usage_check_claude(args)

    root = _resolve_dir(args.path)
    if root is None:
        return 2
    findings = codex_usage.usage_findings(root, threshold=args.threshold)
    actionable = [f for f in findings if f.level in ("warn", "fail")]
    if args.hook:
        for f in actionable:
            print(f"{_LEVEL_TAG.get(f.level, '[????]')} {f.message}")
        return 0
    healthy = _print_findings(findings)
    return 0 if healthy else 1


def cmd_hook_install(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    if args.target == "codex":
        action = native_hooks.install_codex_usage_hook(root, threshold=args.threshold)
        print(f"[{action.status}] {action.message}")
        print("Codex may ask you to review/trust this project hook with /hooks before it runs.")
        return 0
    if args.target == "claude":
        action = native_hooks.install_claude_usage_hook(root, threshold=args.threshold)
        print(f"[{action.status}] {action.message}")
        print("Reads the 5h/weekly limit from the OAuth /usage endpoint; at threshold it")
        print("drives the session into the Horus closure routine (one continuation per session).")
        return 0
    print(f"unsupported hook target: {args.target}")
    return 2


def cmd_app(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    if not getattr(args, "no_detach", False) and companion.relaunch_without_console():
        # Re-spawned under pythonw.exe so no console window lingers; the detached
        # child carries the GUI from here.
        return 0
    return companion.run_companion(
        root,
        host=args.host,
        port=args.port,
        start_dashboard=not args.no_dashboard,
        open_on_start=args.open,
        usage_threshold=args.usage_threshold,
    )


def _resolve_dir(path_str: str) -> Path | None:
    """Resolve --path and require it to be an existing directory. A mistyped path
    must fail loudly, not silently report 'nothing here' and exit 0."""
    root = Path(path_str).resolve()
    if not root.is_dir():
        print(f"error: path is not an existing directory: {root}")
        return None
    return root


def _skill_nudge(root: Path) -> None:
    """Point at the richer in-app skill when it isn't installed/current."""
    stale = []
    for target in ("claude", "codex"):
        stale.extend(f"{target}:{s.name}" for s in skills.missing_or_stale(root, target=target))
    if stale:
        names = ", ".join(stale)
        print(
            f"\ntip: a context-aware version runs inside Claude Code/Codex as '{names}' "
            "skill (it sees this session, not just the files). Install with `horus skill install`."
        )


def cmd_consolidate(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    print(f"Consolidation check: {root}\n")
    findings = routines.consolidate_signals(root)
    healthy = _print_findings(findings)
    print("\n" + templates.CONSOLIDATE_PROMPT)
    if healthy:
        print("Lanes already consolidated — nothing to route or prune.")
    else:
        print("Consolidation candidates above — the in-loop agent applies the routine.")
    _skill_nudge(root)
    return 0


def cmd_distill_history(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    source = routines.find_source_log(root, args.source)
    print(f"Distill-history check: {root}\n")
    _print_findings(routines.distill_signals(root, source))
    print("\n" + templates.DISTILL_HISTORY_PROMPT)
    return 0


def cmd_infer(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    print(f"Infer check: {root}\n")
    _print_findings(routines.infer_signals(root))
    print("\n" + templates.INFER_PROMPT)
    _skill_nudge(root)
    return 0


def cmd_skill(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    scope = "user" if args.user else "project"
    targets = _skill_targets(args.target)
    print(f"Installing Horus skills ({scope} scope, target={args.target}): {root if not args.user else '~'}")
    actions = skills.install_skills(root, user=args.user, force=args.force, targets=targets)
    for a in actions:
        print(f"  [{a.status}] {a.message}")
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
    if not agents.exists() or not claude.exists():
        missing = [p.name for p in (agents, claude) if not p.exists()]
        print(f"Cannot reconcile; missing file(s): {', '.join(missing)}")
        return 1

    if args.source == "claude":
        src, src_name, tgt, tgt_name = claude, "CLAUDE.md", agents, "AGENTS.md"
    else:
        src, src_name, tgt, tgt_name = agents, "AGENTS.md", claude, "CLAUDE.md"

    result = reconcile(
        src.read_text(encoding="utf-8"), src_name,
        tgt.read_text(encoding="utf-8"), tgt_name,
    )
    if result.status == "no-source-block":
        print(f"{src_name} has no managed block to project from.")
        return 1
    if result.status == "already-aligned":
        print(f"Already aligned: {tgt_name} matches {src_name}.")
        return 0
    tgt.write_text(result.new_target_text, encoding="utf-8")
    print(f"Synced {src_name} -> {tgt_name}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="horus", description=__doc__)
    parser.add_argument("--version", action="version", version=f"horus {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="scaffold .horus/ and managed instruction blocks")
    p_init.add_argument("path", nargs="?", default=".", help="project root (default: cwd)")
    p_init.add_argument("--yes", "-y", action="store_true", help="auto-confirm block injection")
    p_init.add_argument("--no-input", action="store_true", help="never prompt; skip injection")
    p_init.add_argument("--no-skills", action="store_true", help="don't scaffold agent skills")
    p_init.add_argument(
        "--skill-target",
        choices=("all", "claude", "codex"),
        default="all",
        help="which agent skill target to scaffold (default: all)",
    )
    p_init.set_defaults(func=cmd_init)

    p_doctor = sub.add_parser("doctor", help="check continuity and instruction health")
    p_doctor.add_argument(
        "target",
        nargs="?",
        choices=("project", "instructions", "all"),
        default="all",
        help="what to check (default: all)",
    )
    p_doctor.add_argument("--path", default=".", help="project root (default: cwd)")
    p_doctor.set_defaults(func=cmd_doctor)

    p_dash = sub.add_parser("dashboard", help="serve the read-only multi-project dashboard")
    p_dash.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    p_dash.add_argument("--port", type=int, default=8765, help="bind port (default: 8765)")
    p_dash.set_defaults(func=cmd_dashboard)

    p_status = sub.add_parser("status", help="print git freshness + latest session for all registered projects")
    p_status.set_defaults(func=cmd_status)

    for name in ("app", "mascot"):
        p_app = sub.add_parser(name, help="show the always-on-top Horus companion")
        p_app.add_argument("--path", default=".", help="project root (default: cwd)")
        p_app.add_argument("--host", default="127.0.0.1", help="dashboard host (default: 127.0.0.1)")
        p_app.add_argument("--port", type=int, default=8765, help="dashboard port (default: 8765)")
        p_app.add_argument("--no-dashboard", action="store_true", help="don't start the dashboard if it is offline")
        p_app.add_argument("--open", action="store_true", help="open the dashboard immediately")
        p_app.add_argument(
            "--no-detach",
            action="store_true",
            help="keep the launching console attached (Windows) instead of re-launching windowless",
        )
        p_app.add_argument(
            "--usage-threshold",
            type=float,
            default=90.0,
            help="usage percentage used by the companion close check (default: 90)",
        )
        p_app.set_defaults(func=cmd_app)

    p_forget = sub.add_parser("forget", help="remove a project from the dashboard registry")
    p_forget.add_argument("path", nargs="?", default=".", help="project root (default: cwd)")
    p_forget.set_defaults(func=cmd_forget)

    p_prune = sub.add_parser("prune", help="drop registered projects whose .horus/ is gone")
    p_prune.set_defaults(func=cmd_prune)

    p_sessions = sub.add_parser("sessions", help="list tracked agent sessions (reconciles live state)")
    p_sessions.add_argument("--prune", action="store_true", help="drop finished/dead sessions instead of listing")
    p_sessions.set_defaults(func=cmd_sessions)

    p_focus = sub.add_parser("focus", help="raise a running session's terminal window (best-effort, Windows)")
    p_focus.add_argument("session_id", help="session id (or a unique prefix)")
    p_focus.set_defaults(func=cmd_focus)

    p_run = sub.add_parser("run", help="spawn (or resume) an agent session, tracked in the registry")
    p_run.add_argument("prompt", help="the prompt to send the agent")
    p_run.add_argument("--agent", default="claude", help="adapter to use (claude | fake; default: claude)")
    p_run.add_argument("--account", default=None, help="account alias to run under (uses its isolated config dir)")
    p_run.add_argument("--model", default=None, help="model alias (e.g. haiku, sonnet, opus)")
    p_run.add_argument(
        "--posture",
        default="default",
        choices=[p.value for p in adapters.PermissionPosture],
        help="permission posture (default: default)",
    )
    p_run.add_argument("--resume", metavar="SESSION_ID", help="resume an existing session by id")
    p_run.add_argument("--path", default=".", help="project root to run in (default: cwd)")
    p_run.set_defaults(func=cmd_run)

    p_open = sub.add_parser("open", help="open an interactive agent session in its own terminal (tracked)")
    p_open.add_argument("path", nargs="?", default=".", help="project root to open in (default: cwd)")
    p_open.add_argument("--agent", default="claude", help="adapter to use (claude | fake; default: claude)")
    p_open.add_argument("--account", default=None, help="account alias to run under (uses its isolated config dir)")
    p_open.add_argument("--model", default=None, help="model alias (e.g. haiku, sonnet, opus)")
    p_open.add_argument(
        "--posture",
        default="default",
        choices=[p.value for p in adapters.PermissionPosture],
        help="permission posture (default: default)",
    )
    p_open.add_argument(
        "--prompt",
        default=None,
        help="initial prompt to seed the interactive session (default: fresh, unseeded)",
    )
    p_open.set_defaults(func=cmd_open)

    p_session = sub.add_parser("session", help="create a new session summary from the template")
    session_sub = p_session.add_subparsers(dest="session_cmd", required=True)
    p_session_new = session_sub.add_parser("new", help="create a new session summary")
    p_session_new.add_argument("title", help="short session title")
    p_session_new.add_argument("--path", default=".", help="project root (default: cwd)")
    p_session_new.add_argument("--agent", default="claude")
    p_session_new.add_argument("--account", default=None, help="account tag (default: auto-detect the logged-in Claude account)")
    p_session_new.add_argument("--environment", default="host")
    p_session_new.set_defaults(func=cmd_session)

    p_account = sub.add_parser("account", help="show the detected agent account, alias, and isolation dir")
    p_account.add_argument("--agent", default="claude", help="which agent's account to inspect (default: claude)")
    p_account.add_argument("--set", dest="alias", metavar="ALIAS", help="set the public alias for the detected account")
    p_account.add_argument("--set-dir", metavar="PATH", help="map an account alias to its CLAUDE_CONFIG_DIR (isolation)")
    p_account.add_argument("--alias-name", metavar="ALIAS", help="with --set-dir: which alias to map (default: current account's)")
    p_account.set_defaults(func=cmd_account)

    p_close = sub.add_parser("close", help="verify continuity (git-aware) and print the closure ritual")
    p_close.add_argument("--path", default=".", help="project root (default: cwd)")
    p_close.add_argument("--commit", action="store_true", help="stage+commit the continuity files")
    p_close.add_argument("--push", action="store_true", help="with --commit, also push to origin")
    p_close.add_argument("--message", "-m", help="commit message for --commit")
    p_close.add_argument(
        "--usage-threshold",
        type=float,
        default=90.0,
        help="warn when Codex context or rate-limit usage reaches this percent (default: 90)",
    )
    p_close.set_defaults(func=cmd_close)

    p_usage = sub.add_parser("usage", help="inspect native app usage signals")
    usage_sub = p_usage.add_subparsers(dest="usage_cmd", required=True)
    p_usage_check = usage_sub.add_parser("check", help="check whether usage is near a closure threshold")
    p_usage_check.add_argument("--path", default=".", help="project root (default: cwd)")
    p_usage_check.add_argument(
        "--target", choices=("codex", "claude"), default="codex",
        help="which app's usage to read (default: codex). claude reads the OAuth /usage endpoint",
    )
    p_usage_check.add_argument(
        "--threshold",
        type=float,
        default=90.0,
        help="warn when context or rate-limit usage reaches this percent (default: 90)",
    )
    p_usage_check.add_argument(
        "--hook",
        action="store_true",
        help="hook mode: print only actionable warnings and always exit 0",
    )
    p_usage_check.set_defaults(func=cmd_usage_check)

    p_hook = sub.add_parser("hook", help="install native app hooks")
    hook_sub = p_hook.add_subparsers(dest="hook_cmd", required=True)
    p_hook_install = hook_sub.add_parser("install", help="install a native app hook")
    p_hook_install.add_argument("--path", default=".", help="project root (default: cwd)")
    p_hook_install.add_argument("--target", choices=("codex", "claude"), required=True, help="native app target")
    p_hook_install.add_argument(
        "--threshold",
        type=float,
        default=90.0,
        help="usage percentage that triggers the closure routine (default: 90)",
    )
    p_hook_install.set_defaults(func=cmd_hook_install)

    p_consol = sub.add_parser(
        "consolidate",
        help="route/prune/distill the .horus/ lanes (prints the routine for the in-loop agent)",
    )
    p_consol.add_argument("--path", default=".", help="project root (default: cwd)")
    p_consol.set_defaults(func=cmd_consolidate)

    p_distill = sub.add_parser(
        "distill-history",
        help="compress a large log into the curated history.md (prints the routine for the in-loop agent)",
    )
    p_distill.add_argument("--path", default=".", help="project root (default: cwd)")
    p_distill.add_argument(
        "--source", help="source log to compress (default: auto-detect docs/HISTORY.md, CHANGELOG.md, …)"
    )
    p_distill.set_defaults(func=cmd_distill_history)

    p_infer = sub.add_parser(
        "infer",
        help="bootstrap/refresh .horus/ from the project's docs (prints the routine for the in-loop agent)",
    )
    p_infer.add_argument("--path", default=".", help="project root (default: cwd)")
    p_infer.set_defaults(func=cmd_infer)

    p_skill = sub.add_parser("skill", help="manage Horus agent skills (.claude/skills/ and .agents/skills/)")
    skill_sub = p_skill.add_subparsers(dest="skill_cmd", required=True)
    p_skill_install = skill_sub.add_parser("install", help="install/update the bundled skills")
    p_skill_install.add_argument("--path", default=".", help="project root (default: cwd)")
    p_skill_install.add_argument("--user", action="store_true", help="install to the user-scope skills directory instead of the project")
    p_skill_install.add_argument("--force", action="store_true", help="overwrite even if present/unversioned")
    p_skill_install.add_argument(
        "--target",
        choices=("all", "claude", "codex"),
        default="all",
        help="which agent skill target to install (default: all)",
    )
    p_skill_install.set_defaults(func=cmd_skill)

    p_recon = sub.add_parser("reconcile", help="sync the managed instruction block across files")
    p_recon.add_argument("target", nargs="?", choices=("instructions",), default="instructions")
    p_recon.add_argument("--path", default=".", help="project root (default: cwd)")
    p_recon.add_argument(
        "--from", dest="source", choices=("agents", "claude"), default="agents",
        help="canonical source file (default: agents)",
    )
    p_recon.set_defaults(func=cmd_reconcile)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Output may include emoji/Unicode from project files; avoid crashing on
    # consoles with a narrow encoding (e.g. Windows cp1252).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
