"""Horus command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
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
    frontmatter,
    gitstate,
    github_catalog,
    initialize,
    integration,
    launch,
    launcher,
    native_hooks,
    offboard,
    overhead,
    registry,
    remote_start,
    routines,
    skills,
    templates,
    upgrade,
    vscode,
)
from horus.continuity import HORUS_DIR, SESSIONS_DIR, check_project
from horus.doctor_machine import machine_findings
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
        findings = (
            check_project(root)
            + skills.skill_findings(root, targets=("claude", "codex"))
            + integration.continuity_pr_findings(root)
        )
        if not _print_findings(findings):
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
                print("      run `horus upgrade-project --apply --no-hooks --no-skills` to refresh Horus-managed blocks")
                rc = 1
        print()

    if args.target in ("machine", "all"):
        print(f"doctor machine: {root}")
        findings = machine_findings(root)
        _print_findings(findings)
        if any(f.level == "fail" for f in findings):
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


def cmd_discover(args: argparse.Namespace) -> int:
    if args.source != "github":
        print(f"Unsupported discovery source: {args.source}")
        return 2
    if args.save:
        created = config.register_github_owner(args.owner)
        print(f"{'Added' if created else 'Already tracking'} GitHub owner: {args.owner}")
    try:
        result = github_catalog.discover(args.owner, local_projects=config.load_projects(), limit=args.limit)
    except RuntimeError as exc:
        print(f"GitHub discovery failed: {exc}")
        return 1
    projects = result.projects
    if not projects:
        print(f"No Horus-enabled GitHub repos found for {args.owner}.")
    else:
        for project in projects:
            where = f"local: {project.local_path}" if project.local_path else f"remote: {project.clone_url}"
            next_action = f" — {project.next_action}" if project.next_action else ""
            print(f"{project.full_name} ({where}){next_action}")
    if result.untracked:
        print(f"(plus {len(result.untracked)} untracked repos)")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    if args.source != "github":
        print(f"Unsupported refresh source: {args.source}")
        return 2
    owners = config.load_github_owners() if args.all else [args.owner]
    owners = [o for o in owners if o]
    if not owners:
        print("No GitHub owner specified or saved. Use `horus refresh github <owner>` or `--all`.")
        return 2
    exit_code = 0
    local = config.load_projects()
    for owner in owners:
        result = github_catalog.force_refresh(owner, local_projects=local, limit=args.limit)
        if result.ok:
            when = f" at {result.fetched_at}" if result.fetched_at else ""
            print(f"Refreshed {owner}: {result.count} Horus-enabled repo(s){when}.")
        else:
            print(f"Refresh failed for {owner}: {result.error}")
            exit_code = 1
    return exit_code


def cmd_start(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace_root).expanduser() if args.workspace_root else None
    if args.set_workspace_root and workspace is None:
        print("Remote start failed: --set-workspace-root requires --workspace-root")
        return 2
    if args.set_workspace_root and workspace is not None:
        saved = config.set_workspace_root(workspace)
        workspace = Path(saved)
        print(f"Workspace root set to: {saved}")
    try:
        result = remote_start.start_github_project(args.target, workspace_root=workspace, limit=args.limit)
    except (RuntimeError, ValueError) as exc:
        print(f"Remote start failed: {exc}")
        return 1

    print(f"{'Cloned' if result.cloned else 'Using local clone'}: {result.path}")
    print(f"{'Registered' if result.registered else 'Already registered'} in Horus project registry.")
    updated = [a for a in result.upgrade_actions if a.status in {"created", "updated"}]
    skipped = [a for a in result.upgrade_actions if a.status == "skipped"]
    if updated:
        print(f"Refreshed {len(updated)} Horus-managed projection(s).")
    if skipped:
        print(f"Skipped {len(skipped)} unowned projection(s).")
    print("\nResume prompt:")
    print(routines.resume_prompt(result.path))
    print(f"\nOpen it with: horus open \"{result.path}\"")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not (root / HORUS_DIR).is_dir():
        print(f"No {HORUS_DIR}/ here (run `horus init` first).")
        return 1
    print(routines.resume_prompt(root))
    return 0


def cmd_onboard(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace_root).expanduser() if getattr(args, "workspace_root", None) else None
    try:
        result = remote_start.onboard_github_project(args.target, workspace_root=workspace, limit=args.limit)
    except (RuntimeError, ValueError) as exc:
        print(f"Onboard failed: {exc}")
        return 1

    print(f"{'Cloned' if result.cloned else 'Using local clone'}: {result.path}")
    created = [a for a in result.init_actions if a.status in {"created", "updated"}]
    print(f"Initialized {len(created)} Horus file(s).")
    print(f"{'Registered' if result.registered else 'Already registered'} in Horus project registry.")

    integ = result.integration
    if integ.ok:
        print(f"Integration: {integ.detail}")
        if integ.pr_url:
            print(f"PR: {integ.pr_url}")
    else:
        print(f"warning: integration did not complete — {integ.detail}")
        print(f"  Manual follow-up: cd \"{result.path}\" and push/open a PR manually.")

    print(f"\nOpen it with: horus open \"{result.path}\"")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if args.config_cmd == "workspace-root":
        if args.path:
            print(config.set_workspace_root(Path(args.path)))
        else:
            print(config.load_workspace_root())
        return 0
    print(f"Unsupported config command: {args.config_cmd}")
    return 2


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


def cmd_vscode_task(args: argparse.Namespace) -> int:
    """Install the static VS Code tasks (Ctrl+Shift+B → agent seeded with `horus resume`)."""
    root = Path(args.path).resolve()
    if not (root / HORUS_DIR).is_dir():
        print(f"No {HORUS_DIR}/ here (run `horus init` first) — the task seeds from it.")
        return 1
    action = vscode.write_tasks(root)
    print(f"[{action.status}] {action.message}")
    if action.status == "kept":
        print("\nAdd this to your .vscode/tasks.json 'tasks' array:\n")
        print(vscode.TASKS_JSON)
        return 1
    if action.status == "created":
        print("In VS Code: Ctrl+Shift+B runs \"Horus: resume Claude session\" in the integrated terminal.")
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


def _phase_filename(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-._")
    return slug or "phase"


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


def _read_horus_doc(root: Path, name: str) -> frontmatter.Document:
    path = root / HORUS_DIR / name
    if not path.is_file():
        return frontmatter.Document({}, "")
    return frontmatter.parse(path.read_text(encoding="utf-8"))


def cmd_execution(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    hdir = root / HORUS_DIR
    if not hdir.is_dir():
        print(f"No {HORUS_DIR}/ here (run `horus init` first).")
        return 1

    if args.execution_cmd == "prompt":
        roadmap_doc = _read_horus_doc(root, "roadmap.md")
        execution_doc = _read_horus_doc(root, "execution.md")
        print(
            templates.execution_supervisor_prompt(
                target=args.target,
                project=root.name,
                next_action=roadmap_doc.front_matter.get("next_action", ""),
                execution_recommendation=roadmap_doc.front_matter.get("execution_recommendation", ""),
                execution_status=execution_doc.front_matter.get("status", ""),
                current_feature=execution_doc.front_matter.get("current_feature", ""),
            )
        )
        return 0

    if args.execution_cmd == "handoff":
        temp_dir = hdir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / f"{_phase_filename(args.phase)}.md"
        if path.exists() and not args.force:
            print(f"Already exists: {path} (use --force to overwrite)")
            return 1

        execution_doc = _read_horus_doc(root, "execution.md")
        model_tier = args.model_tier or execution_doc.front_matter.get("worker_tier", "") or "standard"
        title = args.title or f"Phase {args.phase}"
        path.write_text(
            templates.execution_handoff_note(
                phase=args.phase,
                title=title,
                date=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                agent=args.agent,
                model_tier=model_tier,
            ),
            encoding="utf-8",
        )
        print(f"Created {path}")
        return 0

    print(f"Unsupported execution command: {args.execution_cmd}")
    return 2


def cmd_account(args: argparse.Namespace) -> int:
    from horus import codex_usage as _codex_usage  # local import to keep the top lean

    agent = args.agent
    if agent == "codex":
        identifier = _codex_usage.current_account()
    else:
        identifier = claude_usage.current_account()

    if args.alias:
        if not identifier:
            print(f"No {agent} account detected; nothing to alias (is the agent logged in?).")
            return 1
        config.set_account_alias(identifier, args.alias)
        print(f"Aliased {agent} account -> {args.alias}")
        return 0

    if args.set_dir is not None:
        # Map an alias to its CLAUDE_CONFIG_DIR for per-account isolation.
        target = args.alias_name or config.alias_for(identifier)
        if not target:
            print("No account to map (pass --alias-name, or log in so an alias can be resolved).")
            return 1
        config.set_account_config_dir(target, args.set_dir)
        print(f"Mapped account {target!r} -> CLAUDE_CONFIG_DIR {args.set_dir}")
        return 0

    if getattr(args, "set_codex_home", None) is not None:
        # Map an alias to its CODEX_HOME for per-account Codex isolation.
        target = args.alias_name or config.alias_for(identifier)
        if not target:
            print("No account to map (pass --alias-name, or log in so an alias can be resolved).")
            return 1
        config.set_account_codex_home(target, args.set_codex_home)
        print(f"Mapped account {target!r} -> CODEX_HOME {args.set_codex_home}")
        return 0

    if not identifier:
        print(f"No {agent} account detected (is the agent logged in?).")
        return 1
    alias = config.alias_for(identifier)
    print(f"agent:   {agent}")
    print(f"account: {identifier}")
    print(f"alias:   {alias}")
    if agent == "codex":
        codex_homes = config.load_account_codex_homes()
        if alias in codex_homes:
            print(f"home:    {codex_homes[alias]}")
        if not config.load_account_aliases().get(identifier):
            print("(auto-generated alias; set a friendly one with `horus account --agent codex --set <name>`)")
        if codex_homes:
            print(f"isolated accounts: {', '.join(sorted(codex_homes))}")
    else:
        config_dirs = config.load_account_config_dirs()
        if alias in config_dirs:
            print(f"config:  {config_dirs[alias]}")
        if not config.load_account_aliases().get(identifier):
            print("(auto-generated alias; set a friendly one with `horus account --set <name>`)")
        if config_dirs:
            print(f"isolated accounts: {', '.join(sorted(config_dirs))}")
    return 0


def _close_merge_hook(root: Path) -> int:
    """PreToolUse gate: block a `gh pr merge` while the continuity lanes are stale,
    diverting the session into closure first. Closure authoring needs the in-session
    context that's gone after merge, so this fires at the merge boundary.

    Allows everything that isn't a merge (return 0, no output). When the merge would
    land stale lanes, emits a PreToolUse `deny` decision so Claude blocks the call and
    feeds the closure instruction back to the agent. Best-effort: any trouble reading
    the lanes errs toward allowing the merge (never wedges the user)."""
    hook_input = _read_hook_stdin()
    tool = hook_input.get("tool_name") or hook_input.get("toolName") or ""
    tool_input = hook_input.get("tool_input") or hook_input.get("toolInput") or {}
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    if tool != "Bash" or "gh pr merge" not in command:
        return 0  # not a merge — let it through

    try:
        stale = any(f.level in ("warn", "fail") for f in closure.freshness_gate(root))
    except Exception:
        return 0  # never block the merge on a checker error
    if not stale:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Horus closure check passed: .horus lanes are already fresh; allowing `gh pr merge`.",
            }
        }))
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": templates.MERGE_CLOSURE_INSTRUCTION,
        }
    }))
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()

    if getattr(args, "hook", False):
        # PreToolUse merge-gate mode (reads the tool call from stdin).
        return _close_merge_hook(root)

    if getattr(args, "check", False):
        # Gate mode (scriptable / CI): only dashboard-freshness signals, verdict + exit
        # code, no ritual prompt and no usage/drift noise.
        print(f"Closure freshness check: {root}\n")
        healthy = _print_findings(closure.freshness_gate(root))
        print("\nFresh — the dashboard reflects this session." if healthy
              else "\nStale — update the lanes (run the horus-consolidate skill) before closing/merging.")
        return 0 if healthy else 1

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


def _is_host_restart_command(command: str, host_pid: str) -> bool:
    """True when a hosted session's Bash command would kill/restart its own host.

    Conservative — only clear matches block, so a benign command is never wedged.
    The recognised spellings are OS-flavoured *data* (POSIX kill verbs + Windows
    taskkill/Stop-Process), not platform code, so this stays cross-OS by design."""
    lowered = command.lower()
    # Relaunching the Horus app/dashboard from inside its own host.
    if re.search(r"\bhorus\b.*\b(app|dashboard)\b", lowered) or re.search(
        r"-m\s+horus\s+(app|dashboard)\b", lowered
    ):
        return True
    # A kill verb aimed at the host PID specifically.
    kill_verb = r"(taskkill|stop-process|\bkill\b|pkill|killall)"
    if host_pid and re.search(rf"{kill_verb}.*\b{re.escape(host_pid)}\b", lowered):
        return True
    # A kill verb aimed at the process that *is* the host: the Python interpreter, or
    # the host identified by name (`horus` / `dashboard`).
    if re.search(rf"{kill_verb}.*(\bpython(w)?(\.exe)?\b|\bhorus\b|\bdashboard\b)", lowered):
        return True
    return False


def _guard_host_hook(root: Path) -> int:
    """PreToolUse gate: refuse a Bash command that would kill/restart the Horus
    dashboard process *when run from inside a Horus-hosted PTY session*.

    The footgun (history.md): an in-app agent restarted the app it was hosted in and
    killed itself mid-task. ``pty_host`` marks hosted sessions with
    ``HORUS_HOSTED_SESSION`` + ``HORUS_PTY_HOST_PID`` in the env, which this hook (a
    child of the agent's shell) inherits. Outside a hosted session it does nothing, so
    normal terminals are unaffected. Errs toward *allowing* (never wedge the user)."""
    if os.environ.get("HORUS_HOSTED_SESSION") != "1":
        return 0  # not inside a Horus-hosted PTY — leave everything alone
    hook_input = _read_hook_stdin()
    tool = hook_input.get("tool_name") or hook_input.get("toolName") or ""
    tool_input = hook_input.get("tool_input") or hook_input.get("toolInput") or {}
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    if tool != "Bash" or not command:
        return 0
    host_pid = os.environ.get("HORUS_PTY_HOST_PID", "")
    if not _is_host_restart_command(command, host_pid):
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": templates.HOSTED_RESTART_INSTRUCTION,
        }
    }))
    return 0


def cmd_guard_host(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if getattr(args, "hook", False):
        return _guard_host_hook(root)
    # Non-hook invocation: report whether this shell is inside a Horus-hosted session.
    if os.environ.get("HORUS_HOSTED_SESSION") == "1":
        pid = os.environ.get("HORUS_PTY_HOST_PID", "?")
        print(f"Inside a Horus-hosted PTY session (host process PID {pid}).")
        print("Do not restart/kill the Horus app from here — it would kill this session.")
    else:
        print("Not inside a Horus-hosted PTY session.")
    return 0


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

    event = hook_input.get("hook_event_name", "Stop")
    if event == "UserPromptSubmit":
        # Pre-task: inject usage *context* before the agent acts on the user's prompt.
        # Advisory only — it must defer to the user's explicit request (and push), never
        # replace it with a closure-only commit.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": templates.USAGE_CLOSURE_ADVISORY,
            }
        }))
    else:  # Stop: block the stop and ask the user how to proceed (close now vs push ahead).
        print(json.dumps({"decision": "block", "reason": templates.USAGE_CLOSURE_PROMPT}))
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
        if not actionable:
            return 0
        hook_input = _read_hook_stdin()
        if hook_input.get("stop_hook_active") or hook_input.get("stopHookActive"):
            return 0
        session_id = str(hook_input.get("session_id") or hook_input.get("sessionId") or "unknown")
        if native_hooks.closure_already_fired(session_id):
            return 0
        native_hooks.mark_closure_fired(session_id)

        event = hook_input.get("hook_event_name") or hook_input.get("hookEventName") or "Stop"
        if event == "UserPromptSubmit":
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": templates.USAGE_CLOSURE_ADVISORY,
                }
            }))
        else:
            print(json.dumps({"decision": "block", "reason": templates.USAGE_CLOSURE_PROMPT}))
        return 0
    healthy = _print_findings(findings)
    return 0 if healthy else 1


def cmd_hook_install(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    kind = getattr(args, "kind", "usage")
    if args.target == "codex":
        if kind in ("usage", "all"):
            action = native_hooks.install_codex_usage_hook(root, threshold=args.threshold)
            print(f"[{action.status}] {action.message}")
        if kind in ("merge", "all"):
            action = native_hooks.install_codex_merge_hook(root)
            print(f"[{action.status}] {action.message}")
            print("PreToolUse gate on `gh pr merge`: blocks the merge while the .horus lanes")
            print("are stale and diverts the session to horus-consolidate first.")
        if kind in ("guard", "all"):
            action = native_hooks.install_codex_guard_hook(root)
            print(f"[{action.status}] {action.message}")
            print("PreToolUse gate: inside a Horus-hosted PTY session, blocks a Bash command")
            print("that would restart/kill the dashboard process hosting the session.")
        print("Codex may ask you to review/trust this project hook with /hooks before it runs.")
        return 0
    if args.target == "claude":
        if kind in ("usage", "all"):
            action = native_hooks.install_claude_usage_hook(root, threshold=args.threshold)
            print(f"[{action.status}] {action.message}")
            print("Reads the 5h/weekly limit from the OAuth /usage endpoint; at threshold it")
            print("drives the session into the Horus closure routine (one continuation per session).")
        if kind in ("merge", "all"):
            action = native_hooks.install_claude_merge_hook(root)
            print(f"[{action.status}] {action.message}")
            print("PreToolUse gate on `gh pr merge`: blocks the merge while the .horus lanes")
            print("are stale and diverts the session to horus-consolidate first. Clears once")
            print("`horus close --check` passes, so a re-run of the merge proceeds.")
        if kind in ("guard", "all"):
            action = native_hooks.install_claude_guard_hook(root)
            print(f"[{action.status}] {action.message}")
            print("PreToolUse gate: inside a Horus-hosted PTY session, blocks a Bash command")
            print("that would restart/kill the dashboard process hosting the session (so an")
            print("in-app agent can't kill itself). No effect outside a hosted session.")
        return 0
    print(f"unsupported hook target: {args.target}")
    return 2


def cmd_upgrade_project(args: argparse.Namespace) -> int:
    if args.all:
        if args.path != ".":
            print("error: --all cannot be combined with --path")
            return 2
        return _cmd_upgrade_project_all(args)

    root = _resolve_dir(args.path)
    if root is None:
        return 2
    targets = _skill_targets(args.target)
    actions = upgrade.upgrade_project(
        root,
        apply=args.apply,
        targets=targets,
        hooks=not args.no_hooks,
        skills_=not args.no_skills,
        instructions=not args.no_instructions,
    )
    mode = "Applying" if args.apply else "Checking"
    print(f"{mode} Horus project projections in {root}\n")
    for action in actions:
        print(f"  [{action.status}] {action.message}")
    if not args.apply:
        pending = [a for a in actions if a.status == "would-update"]
        if pending:
            print("\nDry run only. Re-run with `--apply` to write these managed updates.")
            return 1
        skipped = [a for a in actions if a.status == "skipped"]
        if skipped:
            print("\nSome artifacts were skipped because Horus does not own them.")
            return 1
    return 0


def _cmd_upgrade_project_all(args: argparse.Namespace) -> int:
    """`upgrade-project --all`: propagate a CLI upgrade to every registered project
    in one step, instead of the operator running `--apply` in each repo by hand.

    A registry entry can point at a path that only exists on another machine (the
    registry file is user-global, not repo-local), so a missing path is a skip, not
    a failure.
    """
    projects = config.load_projects()
    if not projects:
        print("No projects registered (run `horus init` inside a project).")
        return 0

    targets = _skill_targets(args.target)
    mode = "Applying" if args.apply else "Checking"
    print(f"{mode} Horus project projections across {len(projects)} registered project(s)\n")

    processed = 0
    skipped_projects = 0
    total_items = 0
    any_pending = False
    for path_str in projects:
        root = Path(path_str)
        if not root.is_dir():
            print(f"  [skip] {path_str} (registered path not found on this machine)")
            skipped_projects += 1
            continue

        processed += 1
        print(root)
        actions = upgrade.upgrade_project(
            root,
            apply=args.apply,
            targets=targets,
            hooks=not args.no_hooks,
            skills_=not args.no_skills,
            instructions=not args.no_instructions,
        )
        for action in actions:
            print(f"  [{action.status}] {action.message}")
        if args.apply:
            total_items += sum(1 for a in actions if a.status in ("updated", "created"))
        else:
            pending = [a for a in actions if a.status in ("would-update", "skipped")]
            total_items += len(pending)
            if pending:
                any_pending = True
        print()

    verb = "updated" if args.apply else "pending"
    print(f"Summary: {processed} project(s) processed, {skipped_projects} skipped, {total_items} item(s) {verb}.")
    if not args.apply and any_pending:
        return 1
    return 0


def cmd_offboard(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    actions = offboard.offboard_project(root, apply=args.apply, purge=args.purge)
    mode = "Offboarding" if args.apply else "Checking offboard (dry run)"
    print(f"{mode} Horus from {root}\n")
    for action in actions:
        print(f"  [{action.status}] {action.message}")
    if not args.apply:
        pending = [a for a in actions if a.status == "would-remove"]
        if pending:
            extra = "" if args.purge else " Add `--purge` to also delete `.horus/`."
            print(f"\nDry run only. Re-run with `--apply` to remove these.{extra}")
            return 1
    return 0


def cmd_overhead(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    if args.baseline:
        return _cmd_overhead_baseline(args, root)
    print(f"Horus token overhead estimate: {root}\n")
    print("Static prompt footprint (rough estimate: chars / 4):")
    for item in overhead.static_footprint():
        print(f"  {item.estimated_tokens:5d} tokens  {item.name}")
    print("\nObserved local usage (upper-bound attribution, not a counterfactual):")
    summaries: list[overhead.UsageSummary] = []
    if args.agent in ("all", "codex"):
        home = Path(args.codex_home).expanduser() if args.codex_home else None
        summaries.append(overhead.codex_overhead(root, home=home))
    if args.agent in ("all", "claude"):
        home = Path(args.claude_home).expanduser() if args.claude_home else None
        summaries.append(overhead.claude_overhead(root, home=home))
    for summary in summaries:
        pct = _percent(summary.horus.total_tokens, summary.total.total_tokens)
        print(
            f"  {summary.agent}: {summary.horus_turns}/{summary.turns} Horus-related turns; "
            f"{summary.horus.total_tokens}/{summary.total.total_tokens} raw tokens ({pct:.1f}%)"
        )
        if summary.horus_turns:
            h = summary.horus
            print(
                "      "
                f"input={h.input_tokens}, cached={h.cached_input_tokens + h.cache_read_input_tokens}, "
                f"cache_write={h.cache_creation_input_tokens}, output={h.output_tokens}, "
                f"reasoning={h.reasoning_output_tokens}"
            )
    if args.sessions:
        print("\nTracked session usage (local logs joined by session id):")
        reg = registry.Registry.default()
        reg.reconcile()
        supported = {"claude", "codex"} if args.agent == "all" else {args.agent}
        records = [r for r in reg.all() if r.agent in supported and Path(r.project).resolve() == root]
        codex_home = Path(args.codex_home).expanduser() if args.codex_home else None
        claude_home = Path(args.claude_home).expanduser() if args.claude_home else None
        rows = overhead.session_usages(records, codex_home=codex_home, claude_home=claude_home)
        if not rows:
            print("  no tracked sessions for this project")
        for row in rows:
            sid = row.session_id[:8]
            if not row.matched:
                print(f"  {row.agent} {sid} {row.status}: {row.note}")
                continue
            print(
                f"  {row.agent} {sid} {row.status}: "
                f"{row.turns} turn(s), {row.total.total_tokens} raw tokens"
            )
    return 0


def _parse_baseline_session(value: str, *, default_agent: str) -> tuple[str, str]:
    if ":" in value:
        agent, session_id = value.split(":", 1)
        agent = agent.strip().lower()
    else:
        agent, session_id = default_agent, value
    session_id = session_id.strip()
    if agent not in ("claude", "codex") or not session_id:
        raise argparse.ArgumentTypeError("expected SESSION_ID or AGENT:SESSION_ID where AGENT is claude or codex")
    return agent, session_id


def _baseline_recipe() -> str:
    return """Controlled A/B baseline recipe:
  1. Use the same repo, commit, account, model, permission posture, and task prompt.
  2. Run A without Horus projection: no .horus context, no Horus-managed instruction block, no Horus hooks.
  3. Run B with the normal Horus-enabled project.
  4. Capture only the native session ids, then compare them:
     horus overhead --baseline --without-horus codex:<A_SESSION> --with-horus codex:<B_SESSION>
     Add --without-horus-path /path/to/clean-copy if A ran in a separate clone.

The comparison is aggregate-only: Horus reports matched sessions, turns, tokens, and delta; it does not print transcript content."""


def _cmd_overhead_baseline(args: argparse.Namespace, root: Path) -> int:
    print(f"Horus controlled A/B token baseline: {root}\n")
    print(_baseline_recipe())
    default_agent = "" if args.agent == "all" else args.agent
    try:
        without_specs = [_parse_baseline_session(v, default_agent=default_agent) for v in args.without_horus]
        with_specs = [_parse_baseline_session(v, default_agent=default_agent) for v in args.with_horus]
    except argparse.ArgumentTypeError as exc:
        print(f"\nerror: {exc}")
        return 2
    if not without_specs and not with_specs:
        return 0
    if not without_specs or not with_specs:
        print("\nerror: pass at least one --without-horus and one --with-horus session id to compare.")
        return 2

    codex_home = Path(args.codex_home).expanduser() if args.codex_home else None
    claude_home = Path(args.claude_home).expanduser() if args.claude_home else None
    without_root = Path(args.without_horus_path).resolve() if args.without_horus_path else root
    with_root = Path(args.with_horus_path).resolve() if args.with_horus_path else root
    comparison = overhead.baseline_comparison(
        without_specs,
        with_specs,
        root,
        without_project_root=without_root,
        with_project_root=with_root,
        codex_home=codex_home,
        claude_home=claude_home,
    )

    print("\nObserved aggregate comparison:")
    _print_baseline_group(comparison.without_horus)
    _print_baseline_group(comparison.with_horus)
    delta = comparison.incremental
    base = comparison.without_horus.total.total_tokens
    pct = _percent(delta.total_tokens, base)
    print(f"  incremental: {delta.total_tokens} raw tokens ({pct:+.1f}% vs without Horus)")
    print(
        "      "
        f"input={delta.input_tokens}, cached={delta.cached_input_tokens + delta.cache_read_input_tokens}, "
        f"cache_write={delta.cache_creation_input_tokens}, output={delta.output_tokens}, "
        f"reasoning={delta.reasoning_output_tokens}"
    )

    unmatched = [s for g in (comparison.without_horus, comparison.with_horus) for s in g.sessions if not s.matched]
    return 1 if unmatched else 0


def _print_baseline_group(group: overhead.BaselineGroup) -> None:
    matched = sum(1 for s in group.sessions if s.matched)
    print(
        f"  {group.label}: {matched}/{len(group.sessions)} session(s) matched; "
        f"{group.turns} turn(s), {group.total.total_tokens} raw tokens"
    )
    for row in group.sessions:
        sid = row.session_id[:8]
        if row.matched:
            print(f"      {row.agent} {sid}: {row.turns} turn(s), {row.total.total_tokens} raw tokens")
        else:
            print(f"      {row.agent} {sid}: {row.note}")


def _percent(part: int, total: int) -> float:
    return (part / total * 100.0) if total else 0.0


def cmd_app(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    if not getattr(args, "no_detach", False) and companion.relaunch_without_console():
        # Re-spawned under pythonw.exe so no console window lingers; the detached
        # child carries the GUI from here.
        return 0
    open_mode = companion.resolve_open_mode(app_window=args.app_window, tab=args.tab)
    return companion.run_companion(
        root,
        host=args.host,
        port=args.port,
        start_dashboard=not args.no_dashboard,
        open_on_start=not args.no_open,
        open_mode=open_mode,
        mascot_style=args.mascot_style,
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


def cmd_workflow(args: argparse.Namespace) -> int:
    """Show or update the git-integration workflow policy."""
    # Collect only the keys the user actually passed (each is None when absent).
    integration = getattr(args, "integration", None)
    commit = getattr(args, "commit_policy", None)
    merge = getattr(args, "merge", None)

    # --show (or bare invocation with no flags): just print.
    if integration is None and commit is None and merge is None:
        policy = config.load_workflow_policy()
        for k, v in policy.items():
            print(f"{k} = {v}")
        return 0

    # At least one key to set.
    try:
        policy = config.set_workflow_policy(
            integration=integration,
            commit=commit,
            merge=merge,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    print("Workflow policy updated:")
    for k, v in policy.items():
        print(f"  {k} = {v}")
    return 0


def cmd_ignore(args: argparse.Namespace) -> int:
    """Manage the per-machine repo ignore list."""
    if args.list:
        repos = config.load_ignored_repos()
        if not repos:
            print("No ignored repos.")
        else:
            for r in repos:
                print(r)
        return 0
    if not args.repo:
        print("error: specify a repo (owner/repo) or use --list to show ignored repos.")
        return 2
    # Strip a leading ``github:`` prefix exactly as _normalize_ignored_repo does.
    raw = args.repo
    key = raw.strip()
    if key.lower().startswith("github:"):
        key = key[len("github:"):]
    if config.ignore_repo(key):
        print(f"Ignoring {key}")
    else:
        print(f"Already ignored: {key}")
    return 0


def cmd_unignore(args: argparse.Namespace) -> int:
    """Remove a repo from the per-machine ignore list."""
    raw = args.repo
    key = raw.strip()
    if key.lower().startswith("github:"):
        key = key[len("github:"):]
    if config.unignore_repo(key):
        print(f"Unignored {key}")
    else:
        print(f"Was not ignored: {key}")
    return 0


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
        choices=("project", "instructions", "machine", "all"),
        default="all",
        help="what to check (default: all)",
    )
    p_doctor.add_argument("--path", default=".", help="project root (default: cwd)")
    p_doctor.set_defaults(func=cmd_doctor)

    p_upgrade = sub.add_parser("upgrade-project", help="refresh repo-local Horus projected artifacts")
    p_upgrade.add_argument("--path", default=".", help="project root (default: cwd)")
    p_upgrade.add_argument("--apply", action="store_true", help="write updates (default is dry-run/report)")
    p_upgrade.add_argument(
        "--all",
        action="store_true",
        help="apply to every registered project instead of --path",
    )
    p_upgrade.add_argument(
        "--target",
        choices=("all", "claude", "codex"),
        default="all",
        help="which agent target projections to refresh (default: all)",
    )
    p_upgrade.add_argument("--no-hooks", action="store_true", help="skip native hook refresh")
    p_upgrade.add_argument("--no-skills", action="store_true", help="skip skill refresh")
    p_upgrade.add_argument("--no-instructions", action="store_true", help="skip AGENTS/CLAUDE managed-block refresh")
    p_upgrade.set_defaults(func=cmd_upgrade_project)

    p_offboard = sub.add_parser(
        "offboard",
        help="remove Horus's projected artifacts from a project (inverse of init)",
    )
    p_offboard.add_argument("--path", default=".", help="project root (default: cwd)")
    p_offboard.add_argument("--apply", action="store_true", help="perform the removal (default is dry-run/report)")
    p_offboard.add_argument(
        "--purge",
        action="store_true",
        help="also delete the .horus/ lanes (the durable memory); kept by default",
    )
    p_offboard.set_defaults(func=cmd_offboard)

    p_overhead = sub.add_parser("overhead", help="estimate Horus prompt and observed token overhead")
    p_overhead.add_argument("--path", default=".", help="project root (default: cwd)")
    p_overhead.add_argument(
        "--agent",
        choices=("all", "claude", "codex"),
        default="all",
        help="which local agent logs to inspect (default: all)",
    )
    p_overhead.add_argument("--codex-home", help="CODEX_HOME to inspect (default: ambient ~/.codex)")
    p_overhead.add_argument("--claude-home", help="Claude config dir to inspect (default: ambient ~/.claude)")
    p_overhead.add_argument(
        "--sessions",
        action="store_true",
        help="also report per tracked-session token usage by joining local logs on session id",
    )
    p_overhead.add_argument(
        "--baseline",
        action="store_true",
        help="print/run the controlled A/B baseline recipe for with-vs-without Horus session ids",
    )
    p_overhead.add_argument(
        "--without-horus",
        action="append",
        default=[],
        metavar="AGENT:SESSION",
        help="native baseline session id to compare (repeatable; AGENT may be omitted when --agent is claude/codex)",
    )
    p_overhead.add_argument(
        "--with-horus",
        action="append",
        default=[],
        metavar="AGENT:SESSION",
        help="Horus-enabled session id to compare (repeatable; AGENT may be omitted when --agent is claude/codex)",
    )
    p_overhead.add_argument(
        "--without-horus-path",
        help="project root used by --without-horus sessions when they ran in a separate clean clone",
    )
    p_overhead.add_argument(
        "--with-horus-path",
        help="project root used by --with-horus sessions (default: --path)",
    )
    p_overhead.set_defaults(func=cmd_overhead)

    p_dash = sub.add_parser("dashboard", help="serve the read-only multi-project dashboard")
    p_dash.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    p_dash.add_argument("--port", type=int, default=8765, help="bind port (default: 8765)")
    p_dash.set_defaults(func=cmd_dashboard)

    p_status = sub.add_parser("status", help="print git freshness + latest session for all registered projects")
    p_status.set_defaults(func=cmd_status)

    p_discover = sub.add_parser("discover", help="discover remote Horus projects")
    p_discover.add_argument("source", choices=["github"], help="remote catalog source")
    p_discover.add_argument("owner", help="GitHub user or org to scan")
    p_discover.add_argument("--save", action="store_true", help="show this owner in the dashboard remote catalog")
    p_discover.add_argument("--limit", type=int, default=100, help="maximum repos to scan (default: 100)")
    p_discover.set_defaults(func=cmd_discover)

    p_refresh = sub.add_parser("refresh", help="force-refresh remote cached data")
    p_refresh.add_argument("source", choices=["github"], help="remote source to refresh")
    p_refresh.add_argument("owner", nargs="?", help="GitHub user or org to refresh")
    p_refresh.add_argument("--all", action="store_true", help="refresh all saved GitHub owners")
    p_refresh.add_argument("--limit", type=int, default=100, help="maximum repos to scan per owner (default: 100)")
    p_refresh.set_defaults(func=cmd_refresh)

    p_start = sub.add_parser("start", help="clone/register a remote Horus project and print its resume prompt")
    p_start.add_argument("target", help="remote target, e.g. github:owner/repo")
    p_start.add_argument("--workspace-root", help="clone root for remote projects (default: configured root or ~/projects)")
    p_start.add_argument(
        "--set-workspace-root",
        action="store_true",
        help="save --workspace-root as the machine-local default before starting",
    )
    p_start.add_argument("--limit", type=int, default=100, help="maximum owner repos to scan when resolving GitHub target")
    p_start.set_defaults(func=cmd_start)

    p_onboard = sub.add_parser(
        "onboard",
        help="initialize Horus in an untracked GitHub repo (clone → horus init → PR via policy)",
    )
    p_onboard.add_argument("target", help="GitHub repo to onboard, e.g. github:owner/repo")
    p_onboard.add_argument(
        "--workspace-root",
        help="clone root for the repo if it has no local path (default: configured root or ~/projects)",
    )
    p_onboard.add_argument(
        "--limit",
        type=int,
        default=100,
        help="maximum owner repos to scan when resolving the GitHub target (default: 100)",
    )
    p_onboard.set_defaults(func=cmd_onboard)

    p_config = sub.add_parser("config", help="inspect or update machine-local Horus config")
    config_sub = p_config.add_subparsers(dest="config_cmd", required=True)
    p_workspace = config_sub.add_parser("workspace-root", help="show or set the remote clone workspace root")
    p_workspace.add_argument("path", nargs="?", help="new workspace root")
    p_workspace.set_defaults(func=cmd_config)

    for name in ("app", "mascot"):
        p_app = sub.add_parser(name, help="show the always-on-top Horus companion")
        p_app.add_argument("--path", default=".", help="project root (default: cwd)")
        p_app.add_argument("--host", default="127.0.0.1", help="dashboard host (default: 127.0.0.1)")
        p_app.add_argument("--port", type=int, default=8765, help="dashboard port (default: 8765)")
        p_app.add_argument("--no-dashboard", action="store_true", help="don't start the dashboard if it is offline")
        p_app.add_argument("--no-open", action="store_true", help="just show the mascot; don't pre-open the dashboard window during startup")
        p_app.add_argument(
            "--app-window",
            action="store_true",
            help="force the owned Chrome/Edge app window (dedicated profile; reused/raised on click) "
                 "even off Windows",
        )
        p_app.add_argument(
            "--tab",
            action="store_true",
            help="force a normal browser tab instead of the owned app window "
                 "(owned is the default on Windows; tab is the default elsewhere)",
        )
        p_app.add_argument(
            "--mascot-style",
            choices=("auto", "foreground", "layered"),
            default="auto",
            help="mascot artwork style: auto uses foreground on Windows and layered on other desktops",
        )
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

    p_vscode = sub.add_parser(
        "vscode-task",
        help="write .vscode/tasks.json tasks that start claude/codex seeded with `horus resume` (Ctrl+Shift+B)",
    )
    p_vscode.add_argument("--path", default=".", help="project root (default: cwd)")
    p_vscode.set_defaults(func=cmd_vscode_task)

    p_resume = sub.add_parser("resume", help="print the minimum-context fresh-session handoff for this project")
    p_resume.add_argument("--path", default=".", help="project root (default: cwd)")
    p_resume.set_defaults(func=cmd_resume)

    p_session = sub.add_parser("session", help="create a new session summary from the template")
    session_sub = p_session.add_subparsers(dest="session_cmd", required=True)
    p_session_new = session_sub.add_parser("new", help="create a new session summary")
    p_session_new.add_argument("title", help="short session title")
    p_session_new.add_argument("--path", default=".", help="project root (default: cwd)")
    p_session_new.add_argument("--agent", default="claude")
    p_session_new.add_argument("--account", default=None, help="account tag (default: auto-detect the logged-in Claude account)")
    p_session_new.add_argument("--environment", default="host")
    p_session_new.set_defaults(func=cmd_session)

    p_execution = sub.add_parser("execution", help="work with the optional .horus/execution.md plan")
    execution_sub = p_execution.add_subparsers(dest="execution_cmd", required=True)
    p_execution_prompt = execution_sub.add_parser("prompt", help="print a target-aware supervisor prompt")
    p_execution_prompt.add_argument("--path", default=".", help="project root (default: cwd)")
    p_execution_prompt.add_argument(
        "--target",
        choices=("generic", "claude", "codex"),
        default="generic",
        help="agent target to shape the prompt for (default: generic)",
    )
    p_execution_prompt.set_defaults(func=cmd_execution)

    p_execution_handoff = execution_sub.add_parser(
        "handoff",
        help="create a .horus/temp/ worker handoff note for one phase",
    )
    p_execution_handoff.add_argument("phase", help="phase id, e.g. 1A")
    p_execution_handoff.add_argument("--path", default=".", help="project root (default: cwd)")
    p_execution_handoff.add_argument("--title", default="", help="human-readable phase title")
    p_execution_handoff.add_argument("--agent", default="worker", help="worker agent label")
    p_execution_handoff.add_argument("--model-tier", default="", help="frontier | standard | economy")
    p_execution_handoff.add_argument("--force", action="store_true", help="overwrite an existing handoff note")
    p_execution_handoff.set_defaults(func=cmd_execution)

    p_account = sub.add_parser("account", help="show the detected agent account, alias, and isolation dir")
    p_account.add_argument("--agent", default="claude", help="which agent's account to inspect (default: claude)")
    p_account.add_argument("--set", dest="alias", metavar="ALIAS", help="set the public alias for the detected account")
    p_account.add_argument("--set-dir", metavar="PATH", help="map an account alias to its CLAUDE_CONFIG_DIR (isolation)")
    p_account.add_argument("--set-codex-home", metavar="PATH", help="map an account alias to its CODEX_HOME (Codex isolation)")
    p_account.add_argument("--alias-name", metavar="ALIAS", help="with --set-dir / --set-codex-home: which alias to map (default: current account's)")
    p_account.set_defaults(func=cmd_account)

    p_close = sub.add_parser("close", help="verify continuity (git-aware) and print the closure ritual")
    p_close.add_argument("--path", default=".", help="project root (default: cwd)")
    p_close.add_argument(
        "--check", action="store_true",
        help="gate mode: print the freshness verdict and exit non-zero if the lanes are stale (for scripts/CI)",
    )
    p_close.add_argument(
        "--hook", action="store_true",
        help="PreToolUse hook mode: read a tool call from stdin and block `gh pr merge` while the lanes are stale",
    )
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

    p_guard = sub.add_parser(
        "guard-host",
        help="guard a Horus-hosted PTY session from restarting/killing its own host",
    )
    p_guard.add_argument("--path", default=".", help="project root (default: cwd)")
    p_guard.add_argument(
        "--hook", action="store_true",
        help="PreToolUse hook mode: read a Bash tool call from stdin and block a "
             "command that would kill/restart the host while inside a hosted session",
    )
    p_guard.set_defaults(func=cmd_guard_host)

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
        "--kind", choices=("usage", "merge", "guard", "all"), default="usage",
        help="which hook(s): usage = quota→closure (default); merge = Claude PreToolUse "
             "gate on `gh pr merge`; guard = Claude PreToolUse gate that stops a hosted "
             "session restarting/killing its own host; all = every applicable hook. "
             "merge and guard are Claude-only.",
    )
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

    p_workflow = sub.add_parser(
        "workflow",
        help="show or update the git-integration workflow policy",
    )
    p_workflow.add_argument(
        "--show",
        action="store_true",
        help="print the current policy (default when no flags given)",
    )
    p_workflow.add_argument(
        "--integration",
        choices=list(config.WORKFLOW_CHOICES["integration"]),
        default=None,
        help="integration mode (default: branch-pr-automerge)",
    )
    p_workflow.add_argument(
        "--commit",
        dest="commit_policy",
        choices=list(config.WORKFLOW_CHOICES["commit"]),
        default=None,
        help="commit mode: auto (default) or manual",
    )
    p_workflow.add_argument(
        "--merge",
        choices=list(config.WORKFLOW_CHOICES["merge"]),
        default=None,
        help="merge mode: auto (default) or review",
    )
    p_workflow.set_defaults(func=cmd_workflow)

    p_ignore = sub.add_parser(
        "ignore",
        help="manage the per-machine repo ignore list (hides repos from the dashboard remote catalog)",
    )
    p_ignore.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="repo full-name to ignore, e.g. owner/repo or github:owner/repo",
    )
    p_ignore.add_argument(
        "--list",
        action="store_true",
        help="list currently ignored repos instead of adding one",
    )
    p_ignore.set_defaults(func=cmd_ignore)

    p_unignore = sub.add_parser(
        "unignore",
        help="remove a repo from the per-machine ignore list",
    )
    p_unignore.add_argument(
        "repo",
        help="repo full-name to un-ignore, e.g. owner/repo or github:owner/repo",
    )
    p_unignore.set_defaults(func=cmd_unignore)

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
