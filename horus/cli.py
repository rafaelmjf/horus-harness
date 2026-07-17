"""Horus command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from horus import (
    __version__,
    adapters,
    backend,
    backlog,
    backlog_migrate,
    brainstorm,
    capabilities,
    claude_usage,
    closure,
    companion,
    codex_usage,
    config,
    dashboard,
    datums,
    delivery,
    envelope,
    fetchcheck,
    fleet_backlog,
    fleet_review,
    frontmatter,
    gitstate,
    github_catalog,
    initialize,
    integration,
    launcher,
    machine_requirements,
    mergewatch,
    native_hooks,
    offboard,
    overhead,
    registry,
    reinstall,
    remote_start,
    rescue,
    resume_preflight,
    routines,
    run_executor,
    runlog,
    skills,
    templates,
    terminal_app,
    terminal_sessions,
    upgrade,
    usage_snapshot,
    versioning,
    verify_inventory,
    vscode,
    worktree,
)
from horus.continuity import HORUS_DIR, SESSIONS_DIR, Finding, check_project
from horus.doctor_machine import machine_findings
from horus.instructions import block_version, check_drift, reconcile

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


def _enforce_version_floor(root: Path | None) -> int | None:
    """Refuse a state-mutating command when the running CLI is older than the
    project's recorded `horus_min_version` (Lever B). Returns an exit code to return,
    or None to proceed. `HORUS_IGNORE_VERSION_FLOOR=1` bypasses the gate."""
    if root is None:  # unresolved path — let the caller's own None-check report it
        return None
    if os.environ.get("HORUS_IGNORE_VERSION_FLOOR") == "1":
        return None
    message = versioning.enforce(root, __version__)
    if message is None:
        return None
    print(f"error: {message}", file=sys.stderr)
    return 4


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
    print(f"Initializing Horus continuity in {root}")
    actions = initialize.init_project(
        root,
        assume_yes=args.yes,
        no_input=args.no_input,
        with_skills=not args.no_skills,
        with_hooks=not args.no_hooks,
        skill_targets=_skill_targets(args.skill_target),
    )
    for a in actions:
        print(f"  [{a.status}] {a.message}")
    skipped = [a for a in actions if a.status == "skipped"]
    if skipped:
        print(f"\n{len(skipped)} item(s) skipped. Rerun with --yes to apply.")
    print("\nDone.")
    return 0


def _account_isolation_findings() -> list[Finding]:
    """Advisory checks that every known account has its own isolated config dir.

    Two agent CLIs sharing one CLAUDE_CONFIG_DIR / CODEX_HOME race on its JSON state
    and corrupt it, so an account on the shared ambient dir — or two accounts on one
    dir — is a latent footgun. Warnings only (machine health is not broken), each with
    the remediation command. No known accounts yet -> nothing to say."""
    aliases = sorted(set(config.load_account_aliases().values()))
    if not aliases:
        return []
    claude_dirs = config.load_account_config_dirs()
    codex_homes = config.load_account_codex_homes()
    findings: list[Finding] = []
    for alias in aliases:
        if alias not in claude_dirs and alias not in codex_homes:
            findings.append(Finding(
                "warn",
                f"account {alias!r} is not isolated — it uses the shared ambient config dir. "
                f"While logged into it, run `horus account --isolate --alias-name {alias}` "
                "(add `--agent codex` for a Codex account) to give it its own dir.",
            ))
    for label, mapping in (("CLAUDE_CONFIG_DIR", claude_dirs), ("CODEX_HOME", codex_homes)):
        by_dir: dict[str, list[str]] = {}
        for alias, path in mapping.items():
            try:
                key = str(Path(path).expanduser().resolve())
            except OSError:
                key = str(path)
            by_dir.setdefault(key, []).append(alias)
        for path, sharers in sorted(by_dir.items()):
            if len(sharers) > 1:
                findings.append(Finding(
                    "warn",
                    f"accounts {', '.join(sorted(sharers))} share one {label} ({path}) — "
                    "two agent processes on one config dir corrupt it; give each its own dir.",
                ))
    if not findings:
        findings.append(Finding("ok", f"{len(aliases)} account(s) isolated"))
    return findings


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    rc = 0

    if args.target in ("project", "all"):
        print(f"doctor project: {root}")
        requirements = machine_requirements.inspect(root)
        findings = (
            check_project(root)
            + machine_requirements.findings(requirements)
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
            agents_text = agents.read_text(encoding="utf-8")
            claude_text = claude.read_text(encoding="utf-8")
            report = check_drift(agents_text, "AGENTS.md", claude_text, "CLAUDE.md")
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
            # Currency: a block behind the installed template is an advisory (not a
            # failure) — the instructions still work but should be migrated.
            for name, raw in (("AGENTS.md", agents_text), ("CLAUDE.md", claude_text)):
                v = block_version(raw)
                if v is None or v < templates.BLOCK_VERSION:
                    shown = f"v{v}" if v is not None else "an unversioned block"
                    print(f"  {_LEVEL_TAG['warn']} {name} has {shown} (current v{templates.BLOCK_VERSION}) — "
                          "run `horus upgrade-project --apply --no-hooks --no-skills` to migrate")
                elif v > templates.BLOCK_VERSION:
                    print(f"  {_LEVEL_TAG['warn']} {name} block is v{v}, newer than this CLI "
                          f"(v{templates.BLOCK_VERSION}) — upgrade horus-harness")
        print()

    if args.target in ("machine", "all"):
        print(f"doctor machine: {root}")
        findings = machine_findings(root) + _account_isolation_findings()
        _print_findings(findings)
        if any(f.level == "fail" for f in findings):
            rc = 1
        print()

    return rc


def cmd_dashboard(args: argparse.Namespace) -> int:
    if args.reload:
        ok, detail = companion.reload_dashboard(args.host, args.port)
        print(detail, file=sys.stderr if not ok else sys.stdout)
        return 0 if ok else 1
    try:
        dashboard.serve(host=args.host, port=args.port, exposed=args.exposed)
    except config.ConfigError as exc:
        print(f"dashboard: {exc}", file=sys.stderr)
        return 2
    return 0


def _fleet_fetch(path: str) -> None:
    """Refresh remote-tracking refs before reading fleet/status git state: a
    TTL-cached, read-only `git fetch` (never a pull, never touches the working
    tree) — the same fetch-first primitive as the session-start hook
    (`_fetch_check_hook`), reused here so ahead/behind/gone reflects the fetched
    remote rather than however stale the local refs happen to be. Best-effort:
    any failure (offline, no remote, git error) silently falls back to whatever
    refs are already on disk."""
    try:
        fetchcheck.fetch_and_state(Path(path))
    except Exception:  # noqa: BLE001 (signal refresh only — never break status/fleet)
        pass


def cmd_status(args: argparse.Namespace) -> int:
    """Headless peer of the dashboard overview: git freshness + latest session."""
    projects = config.load_projects()
    if not projects:
        print("No projects registered (run `horus init` inside a project).")
        return 0
    for path in projects:
        _fleet_fetch(path)
        p = dashboard.load_project(path)
        git = gitstate.summary(p.get("git")) or "not a git repo"
        latest = p.get("latest")
        if latest:
            label = latest.get("summary") or latest.get("file", "")
            sess = f"{latest.get('date', '')} — {label}".strip(" —")
        else:
            sess = "no sessions"
        source = p.get("continuity_source") or "-"
        print(f"{p['name']}\n  git:  {git}\n  source: {source}\n  last: {sess}")
        hint = gitstate.staleness_hint(p.get("git"))
        if hint:
            print(f"  note: {hint}")
    return 0


def cmd_fleet(args: argparse.Namespace) -> int:
    """One-line dispatch view for every registered project except the cockpit,
    or (with `--backlog`) the fleet-wide backlog card roll-up (all registered
    projects, cockpit included — its own backlog is as much fleet work as any
    other project's)."""
    if getattr(args, "backlog", False):
        return _cmd_fleet_backlog(args)
    if getattr(args, "review", False):
        try:
            result = fleet_review.build(config.load_projects())
        except ValueError as exc:
            print(f"fleet review: {exc}", file=sys.stderr)
            return 2
        if getattr(args, "stdout", False):
            print(fleet_review.render_json(result), end="")
        else:
            print(fleet_review.render_text(result), end="")
        return 0

    projects = [
        path for path in config.load_projects()
        if Path(path).name.casefold() != "horus-agent"
    ]
    if not projects:
        print("No fleet projects registered (the horus-agent cockpit is excluded).")
        return 0

    def compact(value: object, fallback: str = "-") -> str:
        text = " ".join(str(value or "").split())
        return text or fallback

    for path in projects:
        _fleet_fetch(path)
        project = dashboard.load_project(path)
        git = gitstate.summary(project.get("git")) or "not a git repo"
        latest = project.get("latest")
        if latest:
            label = latest.get("summary") or latest.get("file", "")
            session = f"{latest.get('date', '')} — {label}".strip(" —")
        else:
            session = "no sessions"
        row = (
            f"{project['name']} | git: {compact(git)} | src: {compact(project.get('continuity_source'))} | "
            f"last: {compact(session)} | "
            f"focus: {compact(project.get('current_focus'))} | "
            f"next: {compact(project.get('next_action'))} | "
            f"prompt: {compact(project.get('next_prompt'))}"
        )
        hint = gitstate.staleness_hint(project.get("git"))
        if hint:
            row += f" | note: {compact(hint)}"
        print(row)
    return 0


def _cmd_fleet_backlog(args: argparse.Namespace) -> int:
    """`horus fleet --backlog`: deterministic, read-only fleet-wide backlog
    card roll-up (see horus/fleet_backlog.py). No network/fetch — a pure read
    of each registered project's live `.horus/backlog/` (or best-effort inline
    `## Backlog` count for projects not yet migrated, per PR #164)."""
    projects = config.load_projects()
    if not projects:
        print("No projects registered (run `horus init` inside a project).")
        return 0

    project_filter = getattr(args, "project", None) or ""
    if project_filter:
        match = capabilities.resolve_project_path(project_filter, projects)
        if match is None:
            print(f"No registered project named {project_filter!r} (see `horus fleet`).")
            return 1
        projects = [match]

    type_filter = getattr(args, "type", "") or ""
    rollups = fleet_backlog.apply_filters(
        fleet_backlog.load_fleet_rollup(projects), type_filter=type_filter
    )

    if getattr(args, "stdout", False):
        print(fleet_backlog.render_json(rollups, type_filter=type_filter, project_filter=project_filter), end="")
    else:
        print(fleet_backlog.render_text(rollups), end="")
    return 0


def _warn_if_priors_stale(rollups: list[datums.ModelRollup]) -> None:
    """Non-blocking nudge printed to stderr: never affects exit code or stdout."""
    warning = datums.staleness_warning(rollups)
    if warning:
        print(f"WARNING: {warning}", file=sys.stderr)


def cmd_capabilities(args: argparse.Namespace) -> int:
    """EXPERIMENTAL: read-only fleet capability catalog (see horus/capabilities.py).

    With ``--models``, prints the DATA-ONLY model-calibration roll-up instead —
    measured datums (``~/.horus/datums.json``) joined with owner priors
    (``~/.horus/capabilities.toml``). It describes what was measured and what the
    owner flagged; it never names a model to pick (see horus/datums.py). Owner
    priors may also carry price-for-capability fields (price/capability
    note/researched_at — see the ``older-models-in-roster`` backlog card), which
    render here when present.

    With ``--matrix``, prints the DISPLAY-ONLY delegation decision matrix instead
    — the same tier ladder as ``--models``, joined with the shape->tier and
    tier-trust->verification tables from the shared ``delegation-rubric`` skill
    essence (``horus/skills.py``). It renders the rubric so any agent or user can
    read it deterministically; it never auto-picks or auto-routes a model (see
    horus/datums.py: ``render_delegation_matrix`` / ``delegation_matrix_to_dict``).

    Both ``--models`` and ``--matrix`` render a CONCISE tier-ladder table by
    default (model/tier/price/datums/capability — a CLI glance, per-run LAST
    outcomes and RESEARCHED date omitted); pass ``--verbose``/``--full`` to
    restore those columns. ``--stdout`` JSON always carries every field
    regardless of this flag.

    Both ``--models`` and ``--matrix`` print a non-blocking staleness WARNING to
    stderr when the price/capability priors look stale (see
    ``datums.staleness_warning``) — the command still exits 0 and its normal
    output is unaffected either way.

    With ``--project <name>`` — or with no flags at all when run from inside a
    registered project's root (the self-document default) — regenerates a
    provenance-stamped record for just that one project, writes it to
    ``<project>/.horus/capabilities.json``, and prints the same JSON to stdout.
    Every invocation regenerates from that project's live sources; the file is
    a publishing artifact, not a cache read back."""
    if getattr(args, "matrix", False):
        rollups = datums.build_model_rollup(
            datums.DatumStore.default().all(), datums.load_priors()
        )
        if args.stdout:
            print(json.dumps(
                datums.delegation_matrix_to_dict(
                    rollups, skills.DELEGATION_SHAPE_TIERS, skills.DELEGATION_VERIFICATION_DIAL
                ),
                indent=2,
            ))
        else:
            print(datums.render_delegation_matrix(
                rollups, skills.DELEGATION_SHAPE_TIERS, skills.DELEGATION_VERIFICATION_DIAL,
                verbose=getattr(args, "verbose", False),
            ), end="")
        _warn_if_priors_stale(rollups)
        return 0

    if getattr(args, "models", False):
        rollups = datums.build_model_rollup(
            datums.DatumStore.default().all(), datums.load_priors()
        )
        if args.stdout:
            print(json.dumps(datums.rollup_to_dict(rollups), indent=2))
        else:
            print(datums.render_model_rollup(rollups, verbose=getattr(args, "verbose", False)), end="")
        _warn_if_priors_stale(rollups)
        return 0

    projects = config.load_projects()

    if getattr(args, "project", None):
        project_path = capabilities.resolve_project_path(args.project, projects)
        if project_path is None:
            print(f"No registered project named {args.project!r} (see `horus fleet`).")
            return 1
    else:
        project_path = capabilities.project_path_for_cwd(Path.cwd(), projects)

    if project_path is not None:
        out_path = Path(args.out) if args.out else capabilities.project_out_path(project_path)
        text = capabilities.generate_project(project_path, out_path)
        print(text, end="")
        return 0

    if not projects:
        print("No projects registered (run `horus init` inside a project).")
        return 0
    out_path = Path(args.out) if args.out else capabilities.default_out_path()
    text = capabilities.generate(projects, out_path)
    if args.stdout:
        print(text, end="")
    else:
        data = json.loads(text)
        total = sum(len(p["capabilities"]) for p in data["projects"])
        print(f"Wrote {len(data['projects'])} project(s), {total} capability entrie(s) to {out_path}")
    return 0


def cmd_datum_close(args: argparse.Namespace) -> int:
    """Attach the agent-supplied qualitative + supervisor-cost half to a
    measured datum, and — with ``--card`` — do the one-act acceptance stamp.

    The mechanical half (model/effort/account/runtime/exit…) is captured
    automatically by `horus run`; this one structured command adds the judgment
    the harness must never infer: ``outcome`` (clean/nudged/bounced quality,
    died operational failure, or void for an aborted/untested run), the
    ``shape`` (ambiguity/volume/runtime), a free note, and — all optional — the
    2026-07-14 frozen cost-envelope flags (``--oversight``/``--follow-on``/
    ``--counterfactual``/``--dividend``). Resolves the run id by prefix, like
    `horus tail`.

    ``--card <path-or-slug>`` collapses the post-merge tail into this one
    command: it stamps the delivered backlog card `status: done` + `shipped:
    <date>` in the target project (the closed datum's own ``project``, unless
    ``--card`` is already a resolvable path), then PRINTS a warning — never
    auto-fixing anything — if that target's own continuity looks stale versus
    this run's completion time."""
    try:
        datum = datums.DatumStore.default().close(
            args.run_id,
            outcome=args.outcome,
            shape=args.shape,
            note=args.note,
            oversight=args.oversight,
            follow_on=args.follow_on,
            counterfactual=args.counterfactual,
            dividend=args.dividend,
        )
    except (LookupError, ValueError) as exc:
        print(exc)
        return 2
    bits = [f"outcome={datum.outcome}"]
    if datum.shape:
        bits.append(f"shape={datum.shape!r}")
    if datum.note:
        bits.append(f"note={datum.note!r}")
    if datum.oversight:
        bits.append(f"oversight={datum.oversight}")
    if datum.follow_on is not None:
        bits.append(f"follow-on={datum.follow_on}")
    if datum.counterfactual:
        bits.append(f"counterfactual={datum.counterfactual}")
    if datum.dividend:
        bits.append(f"dividend={datum.dividend}")
    print(f"Closed datum {datum.session_id} ({datum.model or 'unknown model'}): {' | '.join(bits)}")

    if getattr(args, "card", None):
        run_dir = Path(datum.project) if datum.project else None
        # `datum.project` records wherever the run actually executed, which is
        # the WORKTREE path when `horus run --worktree` was used — but the
        # delivered card lives in the primary checkout's own `.horus/backlog/`
        # and must be stamped there even after the worktree is later removed.
        project_root = worktree.primary_checkout(run_dir) if run_dir is not None else None
        try:
            card_path = backlog.resolve_delivered_card(args.card, project_root=project_root)
        except FileNotFoundError as exc:
            print(f"Could not stamp the delivered card: {exc}")
            return 2
        shipped_date = date.today().isoformat()
        backlog.stamp_delivered(card_path, shipped_date=shipped_date)
        print(f"Stamped {card_path} — status: done, shipped: {shipped_date}.")
        if project_root is not None:
            warning = closure.target_continuity_staleness(project_root, completed_at=datum.completed_at)
            if warning:
                print(f"WARNING: {warning}")
        if getattr(args, "remove_worktree", False) and run_dir is not None and project_root is not None:
            if run_dir.resolve() != project_root.resolve():
                removal = worktree.remove_if_merged(project_root, run_dir)
                print(f"{'Removed' if removal.removed else 'Kept'} worktree: {removal.detail}")
            else:
                print("--remove-worktree: this datum's project is already the primary checkout — nothing to remove.")
    return 0


def cmd_datum_migrate_names(args: argparse.Namespace) -> int:
    """One-time, idempotent rename of bare model aliases already captured in
    ``datums.json`` (``sonnet``, ``haiku``, ``opus``) to their canonical
    versioned name, so they join the same roll-up row as owner priors/pricing
    instead of rendering as two half-complete rows. Safe to re-run: a repeat
    call finds nothing left to rename and leaves the file untouched."""
    renamed = datums.DatumStore.default().migrate_names()
    if not renamed:
        print("No bare-alias datums to migrate (already canonical, or no datums.json yet).")
        return 0
    for alias, count in sorted(renamed.items()):
        canonical = datums.ALIAS_TO_CANONICAL[alias]
        print(f"Renamed {count} datum(s): {alias!r} -> {canonical!r}")
    return 0


def cmd_datum_report(args: argparse.Namespace) -> int:
    """Render recent per-worker actuals without requiring run-id archaeology."""
    rows = [row for row in datums.DatumStore.default().all() if row.worker]
    if args.path:
        root = Path(args.path).resolve()
        rows = [row for row in rows if row.project and Path(row.project).resolve() == root]
    if not args.all:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent: list[datums.Datum] = []
        for row in rows:
            try:
                stamp = datetime.fromisoformat(row.launched_at.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.astimezone()
            except (ValueError, AttributeError):
                continue
            if stamp.astimezone(timezone.utc) >= cutoff:
                recent.append(row)
        rows = recent
    breakdown = datums.worker_breakdown(rows)
    if args.json:
        print(json.dumps(breakdown, indent=2, sort_keys=True))
    else:
        print(datums.render_worker_breakdown(breakdown), end="")
    return 0


def cmd_merge_watch(args: argparse.Namespace) -> int:
    """Poll a PR/commit's required checks on the EXACT sha until they settle,
    printing one line per state change — absorbs the wait, not the
    observation (the supervisor still reads the final green/red itself)."""
    root = Path(args.path).resolve()
    try:
        outcome = mergewatch.watch(root, args.ref, interval=args.interval, timeout=args.timeout)
    except mergewatch.MergeWatchError as exc:
        print(f"merge-watch: {exc}")
        return 2
    return 0 if outcome.state == "success" else 1


def cmd_reinstall(args: argparse.Namespace) -> int:
    """`uv cache clean` + force-reinstall from PATH, then grep the INSTALLED
    surface for --verify's marker and report found/absent."""
    source = str(Path(args.path).resolve())
    try:
        result = reinstall.reinstall(source, args.verify, package=args.package, python=args.python)
    except reinstall.ReinstallError as exc:
        print(f"reinstall: {exc}")
        return 2
    print(f"reinstall: {args.package} reinstalled from {source} (python {args.python})")
    status = "FOUND" if result.marker_found else "ABSENT"
    print(f"reinstall: marker {result.marker!r} -> {status} ({result.detail})")
    for note in result.service_notes:
        print(f"reinstall: NOTE {note}")
    return 0 if result.marker_found else 1


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
    if getattr(args, "preflight", False):
        fleet_mode = getattr(args, "fleet", False)
        roots = [Path(path) for path in config.load_projects()] if fleet_mode else [root]
        if not roots:
            print("No Horus projects found for the requested preflight.")
            return 1
        if not fleet_mode and not (root / HORUS_DIR).is_dir():
            print(f"No {HORUS_DIR}/ here (run `horus init` first).")
            return 1
        digest = resume_preflight.gather(
            roots,
            installed=__version__,
            do_fetch=not getattr(args, "no_fetch", False),
            mode="fleet" if fleet_mode else "project",
        )
        print(
            resume_preflight.render_json(digest)
            if getattr(args, "stdout", False)
            else resume_preflight.render_text(digest),
            end="",
        )
        return 0
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
    print(f"Git identity: {result.git_identity}.")
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
    """List tracked agent sessions, reconciling live state against real PIDs first.

    Default view surfaces running sessions first, then recently-updated ones;
    rows untouched for more than a day are hidden (not deleted) unless ``--all``
    is passed, so a registry that's accumulated months of dead workers doesn't
    bury the one session that's actually running or just finished. A non-clean
    row (``failed``/``stale``) gets a best-effort delivery-receipt suffix when the
    worker's own worktree/branch shows it pushed a commit, opened a PR, or closed
    its continuity before its process died — see :mod:`horus.delivery`.
    """
    reg = registry.Registry.default()
    reg.reconcile()  # correct records left "running" by a crashed/closed run
    if args.prune:
        removed = reg.prune()
        if args.json:
            print(json.dumps([], sort_keys=True))
            return 0
        print(f"Pruned {len(removed)} finished session(s).")
        return 0
    records = sorted(reg.all(), key=lambda r: r.updated_at, reverse=True)
    records.sort(key=lambda r: r.status != "running")  # stable: running first, recency preserved within each group

    hidden = 0
    if not args.all:
        now = datetime.now(timezone.utc)
        visible = [r for r in records if r.status == "running" or registry.is_recent(r, now=now)]
        hidden = len(records) - len(visible)
        records = visible

    # Machine output must never be prefixed by an empty-state/filter message.
    if args.json:
        print(json.dumps([asdict(record) for record in records], sort_keys=True))
        return 0

    if not records:
        if hidden:
            print(f"No running or recent sessions ({hidden} older session(s) hidden — pass --all to show them).")
        else:
            print("No tracked sessions.")
        return 0

    for r in records:
        proj = Path(r.project).name
        rc = "" if r.returncode is None else f" rc={r.returncode}"
        line = (
            f"{r.status:<8} {r.agent:<7} {r.account or '-':<14} {proj:<24} "
            f"pid={r.pid or '-'} {r.session_id}{rc} delivery={r.delivery_status}"
        )
        if r.status in delivery.NONCLEAN_STATUSES:
            try:
                session_end = datetime.fromisoformat(r.updated_at) if r.updated_at else None
            except ValueError:
                session_end = None
            suffix = delivery.render_receipt(
                r.status,
                delivery.delivery_receipt(
                    r.project, dispatch_base_sha=r.dispatch_base_sha, session_end=session_end
                ),
            )
            if suffix:
                line += f" · {suffix}"
        print(line)
    if hidden:
        print(f"\n{hidden} older session(s) hidden — pass --all to show them.")
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


# --worker posture presets (skill-v8 matrix). Headless claude stalls under the
# default posture (exits 0 with zero diffs); codex auto-edits with a gated sandbox.
# An explicit --posture always wins over the preset.
_WORKER_POSTURE = {"claude": "full-auto", "codex": "auto-edit"}


def _resolve_run_posture(explicit: str | None, worker: str | None) -> str:
    if explicit is not None:
        return explicit
    if worker:
        return _WORKER_POSTURE[worker]
    return "default"


def _resolved_config_dir(agent: str, account: str | None) -> Path | None:
    """The CLAUDE_CONFIG_DIR / CODEX_HOME an ``agent`` run under ``account`` will use.

    A mapped isolated account resolves to its own dir; an unmapped or absent account
    falls back to the ambient default (the env var, else the tool's home directory).
    Returns ``None`` for agents with no config-dir model (e.g. the fake test adapter)."""
    try:
        if agent == "claude":
            mapped = config.load_account_config_dirs().get(account) if account else None
            raw = mapped or os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
        elif agent == "codex":
            mapped = config.load_account_codex_homes().get(account) if account else None
            raw = mapped or os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
        else:
            return None
        return Path(raw).expanduser().resolve()
    except OSError:
        return None


def _config_dir_conflict_guard(agent: str, account: str | None, *, force: bool) -> int | None:
    """Refuse to launch a second live agent process into a config dir already in use.

    Two agent CLIs sharing one ``CLAUDE_CONFIG_DIR`` / ``CODEX_HOME`` race on its JSON
    config and corrupt it, so both can die on startup. Returns an exit code to refuse
    the run, or ``None`` to proceed. The launching session sharing its OWN dir with the
    new worker (overseer==worker) is the tolerated case — it warns and proceeds.
    ``--force`` downgrades a refusal to a warning. A registry read failure never blocks."""
    if agent not in ("claude", "codex"):
        return None
    target = _resolved_config_dir(agent, account)
    if target is None:
        return None
    try:
        live = [
            rec for rec in registry.Registry.default().all()
            if rec.agent == agent and rec.status == "running"
            and registry.process_alive(rec.pid)
            and _resolved_config_dir(agent, rec.account) == target
        ]
    except Exception:
        return None  # a registry read must never block a launch
    if not live:
        return None
    label = "CLAUDE_CONFIG_DIR" if agent == "claude" else "CODEX_HOME"
    peer = live[0]
    if target == _resolved_config_dir(agent, None) and len(live) == 1:
        print(
            f"Note: this run shares {label} {target} with the launching session "
            f"(live {agent} session {peer.session_id[:8]}). One config dir, two {agent} "
            "processes can race on startup — proceeding since the peer is this session."
        )
        return None
    print(
        f"{'Warning' if force else 'Refusing to run'}: {label} {target} is already in use "
        f"by a live {agent} session ({peer.session_id[:8]}, pid {peer.pid})."
    )
    print(
        f"Two {agent} processes on one config dir race on its JSON state and corrupt it — "
        "both can die on startup. Use a different --account (its own isolated dir) or wait "
        + ("for the peer to finish (overriding anyway: --force)." if force
           else "for the peer to finish; pass --force to override.")
    )
    return None if force else 2


@dataclass(frozen=True)
class _EnvelopeAuth:
    """An authorized unattended dispatch, carried from the guard to the ledger write."""

    name: str
    request: "envelope.DispatchRequest"


def _envelope_usage_remaining(agent: str, account: str | None) -> int | None:
    """Percent of the account's most-constraining window still available, or ``None``
    when the signal is unreadable (which an envelope treats as a refusal, not health).

    Agents with no usage window at all (the fake adapter) report full capacity: there
    is no window to reserve, so the floor cannot bind.
    """
    if agent not in ("claude", "codex"):
        return 100
    now = time.time()
    snap = usage_snapshot.cached_usage(agent, account)
    if snap is not None and snap.has_expired_window(now=now):
        snap = usage_snapshot.refresh_usage(agent, account, now=now) or snap
    if snap is not None:
        snap = snap.without_expired_windows(now=now)
    pct, _reset, _window = snap.worst() if snap is not None else (None, None, "5h")
    return None if pct is None else int(100 - pct)


def _envelope_guard(args: argparse.Namespace, root: Path) -> tuple[int | None, _EnvelopeAuth | None]:
    """Validate an unattended dispatch against its standing envelope.

    Returns ``(exit_code, None)`` to refuse, or ``(None, auth)`` to proceed — with
    ``auth`` set only when an envelope authorized the run and its ledger is owed a
    line. An attended run with no ``--envelope`` passes straight through unchanged.

    This binds here, at the launch itself, rather than in the scheduler that calls
    it: a wrapper-level check is bypassed by any cron entry, script, or dispatcher
    bug that invokes ``horus run`` directly. The bound belongs where the worker
    actually starts.
    """
    name = getattr(args, "envelope", None)
    if getattr(args, "unattended", False) and not name:
        print("Refusing to run: --unattended requires --envelope <name>.")
        print("Unattended dispatch runs under an owner-created standing envelope; "
              "create one with `horus envelope create`.")
        return 2, None
    if not name:
        return None, None

    card_name = getattr(args, "card", None)
    if not card_name:
        print("Refusing to run: --envelope requires --card <name> (the envelope bounds which cards may run).")
        return 2, None
    env = envelope.load(name)
    if env is None:
        print(f"Refusing to run: no readable envelope named {name!r} (looked in {envelope.envelopes_dir()}).")
        return 2, None
    # The card's own frontmatter supplies tier/branch: a caller cannot talk its way
    # past the tier bound by asserting a tier the card does not carry.
    card = backlog.find_card(root, card_name)
    if card is None:
        print(f"Refusing to run: card {card_name!r} was not found in {backlog.backlog_dir(root)}.")
        print("An envelope authorizes named cards, so an unknown card cannot be authorized.")
        return 2, None
    request = envelope.DispatchRequest(
        card=card.name,
        account=args.account,
        tier=card.tier,
        effort=getattr(args, "effort", None) or "",
        branch=card.field_value("branch"),
    )
    refusal = envelope.validate(
        env, request, usage_remaining=_envelope_usage_remaining(args.agent, args.account)
    )
    if refusal is not None:
        print(f"Refusing to run: {refusal.message}")
        print(f"Violated bound: {refusal.bound}. Envelope bounds are the owner's standing "
              "authorization — widen it by creating a new envelope, never by overriding here.")
        return 2, None
    print(f"Envelope {env.name}: dispatch of {card.name} authorized (expires {env.expires}).")
    return None, _EnvelopeAuth(name=env.name, request=request)


def _apply_unattended_defaults(args: argparse.Namespace) -> int | None:
    """Give `--unattended` the safe dispatch posture, then return ``None`` to proceed
    (or an exit code to refuse).

    An unattended worker has nobody watching it, which implies two things the
    attended default cannot assume:

    - **Attachable.** ``horus run`` hosts the agent in the caller's own process by
      default, so a cron-launched worker is unreachable — the 2026-07-17 dogfood hit
      exactly this: real work, registered in `horus sessions`, but never
      `horus attach`-able. Unattended runs go to managed tmux, detached, so the owner
      can always look in or intervene.
    - **Isolated.** An unattended worker in the shared checkout can switch branches
      under a concurrent session's feet, so it gets its own worktree.

    Every implied flag yields to an explicit one, and attended ``horus run`` is
    untouched: this only fills in blanks on the unattended path.
    """
    unattended = getattr(args, "unattended", False)
    # argparse cannot distinguish an omitted --target from its default, so the flag
    # defaults to None and the real default is resolved here, per posture.
    if not unattended:
        args.target = getattr(args, "target", None) or terminal_sessions.CURRENT
        return None

    if args.agent not in _WORKER_POSTURE:
        print(f"Refusing to run: --unattended needs a worker-capable agent "
              f"({', '.join(sorted(_WORKER_POSTURE))}), not {args.agent!r}.")
        print("Unattended dispatch is worker dispatch: it runs headless, detached, with no "
              "live supervisor, so it needs an agent with a worker posture.")
        return 2

    args.worker = getattr(args, "worker", None) or args.agent
    args.target = getattr(args, "target", None) or terminal_sessions.TMUX
    args.detach = True
    if not getattr(args, "worktree", None):
        # --unattended requires --envelope, which requires --card, so a card slug is
        # always available here. `auto/` namespaces machine-created branches: coming
        # back from a trip, `git branch` says at a glance what was dispatched, and an
        # auto branch can never collide with one the owner cut for the same card.
        args.worktree = f"auto/{args.card}"
    return None


def _run_usage_preflight(
    agent: str, account: str | None, *, force: bool, refuse_on_unknown: bool = False
) -> int | None:
    """Best-effort usage gate before a run spawns. Returns an exit code to refuse the
    run, or ``None`` to proceed.

    Only claude/codex are checked (the fake adapter has no usage and tests depend on
    it). Both the 5-hour and weekly windows are read; the bands below apply to the MORE
    CONSTRAINING of the two (the higher-utilization window):

    - ≥95% refuses (exit 2) unless ``--force`` — the window would die mid-run;
    - ≥80% warns (a closing window) and proceeds;
    - ≥50% surfaces a closing-window notice with the percent and reset time, so a long
      dispatch is not silently green-lit — this is point-in-time visibility, NOT a
      runtime predictor.

    An unknown signal (no snapshot, or neither window readable) is SURFACED rather than
    treated as healthy: by default it prints a notice and proceeds (a courtesy, not a
    wall); with ``refuse_on_unknown`` it refuses (exit 2) for a critical launch.
    """
    if agent not in ("claude", "codex"):
        return None
    now = time.time()
    snap = usage_snapshot.cached_usage(agent, account)
    if snap is not None and snap.has_expired_window(now=now):
        refreshed = usage_snapshot.refresh_usage(agent, account, now=now)
        if refreshed is not None:
            snap = refreshed
    if snap is not None:
        snap = snap.without_expired_windows(now=now)
    who = f"{agent}{f' account {account}' if account else ''}"
    pct, reset, window = snap.worst() if snap is not None else (None, None, "5h")

    if pct is None:
        # Unknown != healthy: make the blind spot visible instead of proceeding green.
        print(f"Capacity unknown for {who} — no usage signal (offline, missing creds, or schema drift).")
        if refuse_on_unknown:
            print("Refusing to run: --refuse-on-unknown is set for this critical launch.")
            return 2
        print("Proceeding anyway (preflight is a courtesy); pass --refuse-on-unknown to gate on this.")
        return None

    reset = reset or "unknown reset"
    if pct >= usage_snapshot.PREFLIGHT_REFUSE and not force:
        print(f"Refusing to run: {who} {window} usage is {pct:.0f}% (resets {reset}).")
        print("The window is nearly exhausted — the session would likely die mid-run.")
        print("Pass --force to launch anyway, or wait for the reset.")
        return 2
    if pct >= usage_snapshot.PREFLIGHT_WARN:
        print(f"Warning: {who} {window} usage is {pct:.0f}% (resets {reset}) — launching into a closing window.")
    elif pct >= usage_snapshot.PREFLIGHT_CLOSING:
        print(f"Note: {who} {window} usage is {pct:.0f}% (resets {reset}) — a long dispatch may not finish this window.")
    return None


def cmd_run(args: argparse.Namespace) -> int:
    """Spawn (or resume) an agent session through an adapter, tracked in the registry.

    Streams the session's events to stdout and records it so it shows up in
    `horus sessions` and the dashboard's Live sessions card.

    With ``--worktree <branch>`` the session runs in a per-branch git worktree
    (created or reused), so the registry row records that worktree's path.
    """
    # argparse cannot distinguish an omitted option from its default unless the
    # default is None. Let the worker's named agent select the matching adapter;
    # an explicit --agent remains authoritative.
    args.agent = args.agent or args.worker or "claude"
    try:
        adapter = adapters.get_adapter(args.agent)
    except KeyError as exc:
        print(exc)
        return 2
    model_error = adapter.validate_model(getattr(args, "model", None))
    if model_error is not None:
        print(f"Refusing to run: {model_error}")
        return 2

    root = Path(args.path).resolve()
    # The standing envelope is the outermost authorization: refuse before any git
    # work, worktree creation, or usage read happens on an unauthorized dispatch.
    refusal, envelope_auth = _envelope_guard(args, root)
    if refusal is not None:
        return refusal
    # Before the worker/worktree work below, so an unattended run reaches it already
    # wearing the attachable + isolated posture.
    refusal = _apply_unattended_defaults(args)
    if refusal is not None:
        return refusal

    dispatch_base_sha: str | None = None
    dispatch_pending = 0
    if getattr(args, "worker", None):
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                dispatch_base_sha = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        dispatch_pending = len(closure.pending_delivery_commits(root))
        base_label = dispatch_base_sha[:8] if dispatch_base_sha else "unknown"
        print(f"Dispatch boundary: base {base_label} · pending continuity {dispatch_pending}")
        if dispatch_pending:
            print(
                "Warning: canonical continuity does not cover the latest delivery commits; "
                "include their relevant state in the worker brief or checkpoint before dispatch."
            )

    guard_refusal = _config_dir_conflict_guard(
        args.agent, args.account, force=getattr(args, "force", False)
    )
    if guard_refusal is not None:
        return guard_refusal
    if getattr(args, "worktree", None):
        try:
            wt = worktree.ensure_worktree(root, args.worktree)
        except worktree.WorktreeError as exc:
            print(f"Refusing to run: {exc}")
            return 2
        verb = "Created" if wt.created else "Reusing"
        print(f"{verb} worktree {wt.path} (branch {wt.branch})")
        root = wt.path.resolve()

    refusal = _run_usage_preflight(
        args.agent,
        args.account,
        force=getattr(args, "force", False),
        refuse_on_unknown=getattr(args, "refuse_on_unknown", False),
    )
    if refusal is not None:
        return refusal

    request = run_executor.RunRequest(
        session_id=str(uuid.uuid4()), agent=args.agent, project=root, prompt=args.prompt,
        account=args.account,
        posture=_resolve_run_posture(args.posture, getattr(args, "worker", None)),
        model=args.model, effort=args.effort, worker=bool(getattr(args, "worker", None)),
        resume=args.resume, dispatch_base_sha=dispatch_base_sha, dispatch_pending=dispatch_pending,
        delivery_expected=getattr(args, "expect_delivery", False),
        watch=getattr(args, "watch", False),
    )
    # Record the attempt at authorization, not at success: a worker that dies or
    # bounces has still spent an attempt, which is exactly what the bound protects.
    if envelope_auth is not None:
        envelope.record_dispatch(
            envelope_auth.name, envelope_auth.request, session_id=request.session_id
        )
    if getattr(args, "detach", False):
        if not getattr(args, "worker", None) or args.target != terminal_sessions.TMUX:
            print("Refusing to run: --detach requires --worker and --target tmux")
            return 2
        result = terminal_sessions.launch_detached_run(request)
        if not result.ok:
            print(f"Refusing to run: {result.error}")
            return 2
        print(f"Started detached {request.agent} worker (tmux, "
              f"session {request.session_id}, runner pid {result.pid}).")
        return 0
    if getattr(args, "target", terminal_sessions.CURRENT) != terminal_sessions.CURRENT:
        print("Refusing to run: --target tmux requires --detach")
        return 2
    return run_executor.execute(request, watcher=_spawn_watcher)


def cmd_envelope_create(args: argparse.Namespace) -> int:
    """Create a bounded standing envelope. Bad bounds refuse at create rather than
    silently never matching at fire time."""
    try:
        env = envelope.create(
            name=args.name,
            expires=args.expires,
            cards=tuple(args.card),
            branch=args.branch.strip(),
            accounts=tuple(args.account),
            tiers=tuple(args.tier),
            efforts=tuple(args.effort),
            usage_floor=args.usage_floor,
            max_attempts_per_card=args.max_attempts,
            max_dispatches_per_day=args.max_dispatches_per_day,
            merge_authority=args.allow_merge,
        )
    except envelope.EnvelopeError as exc:
        print(f"Refusing to create envelope: {exc}")
        return 2
    print(f"Created envelope {env.name} (expires {env.expires}, inclusive).")
    print(f"  cards      : {', '.join(env.cards) or '(none)'}")
    if env.branch:
        print(f"  branch     : {env.branch} (every card stamped `branch: {env.branch}`)")
    print(f"  accounts   : {', '.join(env.accounts)}")
    print(f"  tiers      : {', '.join(env.tiers)}")
    print(f"  efforts    : {', '.join(env.efforts) or '(any)'}")
    print(f"  usage floor: {_usage_floor_label(env)}")
    print(f"  attempts   : {env.max_attempts_per_card}/card · {env.max_dispatches_per_day}/day")
    print(f"  merge      : {'authorized on green gates' if env.merge_authority else 'NOT authorized (verify + escalate only)'}")
    print(f"\nStored at {envelope.envelope_path(env.name)} — machine-local, never commit it.")
    print(f"Revoke at any time with `horus envelope revoke {env.name}`.")
    return 0


def _usage_floor_label(env: "envelope.Envelope") -> str:
    """The floor is opt-in, so say which regime this envelope is actually in — the
    owner reads this while setting up a trip they cannot correct from."""
    if env.usage_floor <= 0:
        return "none (capacity not checked; dispatches even when usage is unreadable)"
    return f"{env.usage_floor}% remaining (unreadable capacity refuses)"


def _envelope_state(env: "envelope.Envelope", *, today: date) -> str:
    if env.revoked:
        return "revoked"
    return "expired" if env.is_expired(today=today) else "active"


def cmd_envelope_list(args: argparse.Namespace) -> int:
    envs = envelope.load_all()
    today = datetime.now(timezone.utc).date()
    if getattr(args, "stdout", False):
        print(json.dumps(
            [
                {
                    **asdict(env),
                    "state": _envelope_state(env, today=today),
                    "spend": asdict(envelope.spend(env.name)),
                }
                for env in envs
            ],
            indent=2,
        ))
        return 0
    if not envs:
        print("No standing envelopes. Create one with `horus envelope create`.")
        return 0
    print(f"{'NAME':<24} {'STATE':<8} {'EXPIRES':<12} {'TODAY':<7} CARDS")
    for env in envs:
        used = envelope.spend(env.name)
        scope = ", ".join(env.cards) or (f"branch:{env.branch}" if env.branch else "(none)")
        per_day = f"{used.dispatches_today}/{env.max_dispatches_per_day}"
        print(f"{env.name:<24} {_envelope_state(env, today=today):<8} {env.expires:<12} {per_day:<7} {scope}")
    return 0


def cmd_envelope_show(args: argparse.Namespace) -> int:
    env = envelope.load(args.name)
    if env is None:
        print(f"No readable envelope named {args.name!r} (looked in {envelope.envelopes_dir()}).")
        return 1
    today = datetime.now(timezone.utc).date()
    used = envelope.spend(env.name)
    if getattr(args, "stdout", False):
        print(json.dumps(
            {
                **asdict(env),
                "state": _envelope_state(env, today=today),
                "spend": asdict(used),
                "ledger": envelope.read_ledger(env.name),
            },
            indent=2,
        ))
        return 0
    print(f"Envelope {env.name} — {_envelope_state(env, today=today)}")
    print(f"  created    : {env.created}")
    print(f"  expires    : {env.expires} (inclusive)")
    if env.revoked:
        print(f"  revoked    : {env.revoked_at or 'yes'}")
    print(f"  cards      : {', '.join(env.cards) or '(none)'}")
    if env.branch:
        print(f"  branch     : {env.branch}")
    print(f"  accounts   : {', '.join(env.accounts)}")
    print(f"  tiers      : {', '.join(env.tiers)}")
    print(f"  efforts    : {', '.join(env.efforts) or '(any)'}")
    print(f"  usage floor: {_usage_floor_label(env)}")
    print(f"  merge      : {'authorized on green gates' if env.merge_authority else 'NOT authorized (verify + escalate only)'}")
    print(f"\nSpend (from the append-only ledger, {envelope.ledger_path(env.name)}):")
    print(f"  dispatches today : {used.dispatches_today}/{env.max_dispatches_per_day}")
    print(f"  dispatches total : {used.total}")
    if not used.attempts_by_card:
        print("  attempts         : none yet")
    for card, count in sorted(used.attempts_by_card.items()):
        exhausted = " (exhausted)" if count >= env.max_attempts_per_card else ""
        print(f"  attempts         : {card} {count}/{env.max_attempts_per_card}{exhausted}")
    return 0


def cmd_envelope_revoke(args: argparse.Namespace) -> int:
    env = envelope.revoke(args.name)
    if env is None:
        print(f"No readable envelope named {args.name!r} (looked in {envelope.envelopes_dir()}).")
        return 1
    print(f"Revoked envelope {env.name} at {env.revoked_at}.")
    print("Pending scheduled dispatches validate at fire time, so they are refused from now on.")
    print("Live attached sessions are untouched — stop those with `horus stop <session>`.")
    return 0


def _spawn_watcher(session_id: str, cwd: Path) -> None:
    """Open a watcher terminal running ``horus tail <session_id>`` (--watch).

    Best-effort by contract: no display, no emulator, or no ``horus`` on PATH
    must never fail the run — warn once and continue headless."""
    try:
        launcher.open_terminal(["horus", "tail", session_id], cwd=cwd)
    except Exception as exc:  # noqa: BLE001 (any watcher failure stays non-fatal)
        print(f"  [watch] could not open a watcher terminal ({exc}); continuing headless")


def _resolve_tail_session(reg: "registry.Registry", session_id: str | None) -> "registry.SessionRecord":
    """The session `horus tail` should follow: prefix match when an id is given
    (like git short hashes), else the most recently updated running session.
    Raises ``LookupError`` with a user-facing message when there isn't one."""
    records = reg.all()
    if session_id:
        matches = [r for r in records if r.session_id.startswith(session_id)]
        if not matches:
            raise LookupError(f"No session matching {session_id!r}. Run `horus sessions` to list them.")
        if len(matches) > 1:
            raise LookupError(f"{session_id!r} is ambiguous ({len(matches)} sessions); use more of the id.")
        return matches[0]
    running = [r for r in records if r.status == "running"]
    if not running:
        raise LookupError("No running session to tail. Run `horus sessions` or pass a session id.")
    return max(running, key=lambda r: r.updated_at)


def cmd_tail(args: argparse.Namespace) -> int:
    """Print a session's run log so far, then follow it until the run is over.

    The watcher half of `horus run --watch`: reads the per-session log that
    `horus run` tees to ``~/.horus/logs/runs/``, polls for new lines, and stops
    once the registry marks the session terminal and the log has gone quiet,
    closing with a final status line from the registry. Ctrl+C detaches cleanly
    (the run itself is unaffected — this is a reader, not the session)."""
    reg = registry.Registry.default()
    reg.reconcile()
    try:
        rec = _resolve_tail_session(reg, args.session_id)
    except LookupError as exc:
        print(exc)
        return 2

    path = runlog.run_log_path(rec.session_id)
    text, offset = runlog.read_from(path, 0)
    if text:
        sys.stdout.write(text)
        sys.stdout.flush()
    elif rec.status in registry.TERMINAL:
        print(f"(no run log at {path})")

    if rec.status not in registry.TERMINAL:
        def is_terminal() -> bool:
            reg.reconcile()  # a crashed run leaves "running" behind; don't follow a ghost
            current = reg.get(rec.session_id)
            return current is None or current.status in registry.TERMINAL

        def write(chunk: str) -> None:
            sys.stdout.write(chunk)
            sys.stdout.flush()

        try:
            runlog.follow(path, offset, emit=write, is_terminal=is_terminal)
        except KeyboardInterrupt:
            print(f"\n(detached from session {rec.session_id})")
            return 0

    final = reg.get(rec.session_id) or rec
    rc = "" if final.returncode is None else f" rc={final.returncode}"
    print(f"\n{final.status} — session {final.session_id} (account {final.account or '-'}){rc}")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    """Open a tracked attended agent in a window, this TTY, or persistent tmux."""
    root = Path(args.path).resolve()
    prompt = args.prompt if args.prompt is not None else (
        routines.resume_prompt(root) if args.mode == "resume" else ""
    )
    if args.detach and args.target != terminal_sessions.TMUX:
        print("Refusing to open: --detach is only valid with --target tmux")
        return 2
    if args.target == terminal_sessions.WINDOW:
        brief = backend.LaunchBrief(
            project_dir=root,
            agent=args.agent,
            account=args.account,
            posture=args.posture,
            model=args.model,
            prompt=prompt,
        )
        try:
            handle = backend.LocalBackend().launch(brief)
        except backend.LaunchFailed as exc:
            print(f"Refusing to open: {exc}")
            return 2
        print(f"Opened {args.agent} session in {root.name} as {args.account or 'ambient'} "
              f"(pid {handle.meta['pid']}, session {handle.session_id}).")
        return 0

    kwargs = {
        "agent": args.agent,
        "project_dir": root,
        "account": args.account,
        "posture": args.posture,
        "model": args.model,
        "prompt": prompt,
    }
    if args.target == terminal_sessions.TMUX:
        result = terminal_sessions.launch_tmux(**kwargs, attach=not args.detach)
    else:
        result = terminal_sessions.run_attached(**kwargs)
    if not result.ok:
        print(f"Refusing to open: {result.error}")
        return 2
    verb = "Started" if args.target == terminal_sessions.TMUX else "Completed"
    print(f"{verb} {args.agent} session in {root.name} as {args.account or 'ambient'} "
          f"({args.target}, session {result.session_id}).")
    return 0


def cmd_terminal_app(args: argparse.Namespace) -> int:
    return terminal_app.run()


def cmd_attach(args: argparse.Namespace) -> int:
    error = terminal_sessions.attach_session(args.session_id)
    if error:
        print(f"Could not attach: {error}")
        return 2
    return 0


def cmd_session_stop(args: argparse.Namespace) -> int:
    error = terminal_sessions.stop_session(args.session_id)
    if error:
        print(f"Could not stop: {error}")
        return 2
    print(f"Stopped session {args.session_id}.")
    return 0


def cmd_reap(args: argparse.Namespace) -> int:
    reaped = terminal_sessions.reap_orphans()
    if not reaped:
        print("No orphaned tmux sessions found.")
        return 0
    print(f"Reaped {len(reaped)} orphaned tmux session(s): {', '.join(sorted(reaped))}")
    return 0


def cmd_brainstorm(args: argparse.Namespace) -> int:
    """Launch a tracked brainstorm session seeded with scoped PRD context + a topic.

    The CLI twin of the dashboard's Ideas/Brainstorm card: both call
    :func:`horus.brainstorm.start_brainstorm`, so there is one code path. The
    session drafts an implementation plan to `.horus/temp/brainstorm-<slug>.md`
    and never edits PRD.md.
    """
    root = Path(args.path).resolve()
    if not (root / HORUS_DIR).is_dir():
        print(f"No {HORUS_DIR}/ here (run `horus init` first) — brainstorm seeds from PRD.md.")
        return 1
    try:
        result = brainstorm.start_brainstorm(
            project_dir=root,
            topic=args.topic,
            agent=args.agent,
            account=args.account,
            posture=args.posture,
            model=args.model,
        )
    except ValueError as exc:
        print(f"Refusing to brainstorm: {exc}")
        return 2
    launched = result.launch
    if not launched.ok:
        print(f"Refusing to brainstorm: {launched.error}")
        return 2
    print(f"Started brainstorm on {launched.project.name} as {launched.account or 'ambient'} "
          f"(pid {launched.pid}, session {launched.session_id}).")
    print(f"Topic: {result.topic}")
    print(f"The session will draft its plan to {result.note_path} (review it there; PRD.md is untouched).")
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
    if action.status in ("created", "updated"):
        print("In VS Code: Ctrl+Shift+B runs \"Horus: resume Claude session\" in the integrated terminal;")
        print("fresh/Codex variants live under Terminal > Run Task. For dedicated shortcuts, add to your")
        print("USER keybindings.json (keybindings are per-user in VS Code, never per-repo):\n")
        print(vscode.KEYBINDINGS_SNIPPET)
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
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
    sessions = root / HORUS_DIR / SESSIONS_DIR
    if not (root / HORUS_DIR).is_dir():
        print(f"No {HORUS_DIR}/ here (run `horus init` first).")
        return 1
    sessions.mkdir(parents=True, exist_ok=True)

    # Timestamp (not just date): multiple recovery notes a day must not collide.
    now = datetime.now()
    path = sessions / f"{now:%Y-%m-%d-%H%M%S}-{_slugify(args.title)}.md"
    if path.exists():
        print(f"Already exists: {path}")
        return 1
    # Explicit attribution wins. Environment inference is deliberately
    # conservative: when both/neither runtime markers exist, record "unknown"
    # instead of silently misattributing the note to Claude.
    agent = args.agent
    if agent is None:
        declared = os.environ.get("HORUS_AGENT", "").strip().lower()
        if declared in {"claude", "codex"}:
            agent = declared
        else:
            has_claude = bool(os.environ.get("CLAUDE_CONFIG_DIR"))
            has_codex = bool(os.environ.get("CODEX_HOME"))
            agent = "claude" if has_claude and not has_codex else "codex" if has_codex and not has_claude else "unknown"

    # Record the alias, never the raw account identifier.
    if args.account:
        account = args.account
    elif agent == "claude":
        account = config.alias_for(claude_usage.current_account()) or "unknown"
    elif agent == "codex":
        account = config.alias_for(codex_usage.current_account()) or "unknown"
    else:
        account = "unknown"
    path.write_text(
        templates.session_summary(
            title=args.title,
            date=now.strftime("%Y-%m-%dT%H:%M:%S"),
            project=root.name,
            agent=agent,
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
        focus = frontmatter.resolve_focus(root)
        execution_doc = _read_horus_doc(root, "execution.md")
        print(
            templates.execution_supervisor_prompt(
                target=args.target,
                project=root.name,
                next_action=focus["next_action"],
                execution_recommendation=focus["execution_recommendation"],
                execution_status=execution_doc.front_matter.get("status", ""),
                current_feature=execution_doc.front_matter.get("current_feature", ""),
                prd_structure=frontmatter.has_prd(root),
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
                prd_structure=frontmatter.has_prd(root),
            ),
            encoding="utf-8",
        )
        print(f"Created {path}")
        return 0

    print(f"Unsupported execution command: {args.execution_cmd}")
    return 2


def cmd_backlog(args: argparse.Namespace) -> int:
    """`.horus/backlog/` cards: list (with parallel-safety metadata) or claim
    (guarded by an overlap check against currently in-progress cards)."""
    root = _resolve_dir(args.path)
    if root is None:
        return 2

    if args.backlog_cmd == "list":
        cards = backlog.load_active_cards(root)
        if args.type:
            cards = [c for c in cards if c.type == args.type]
        if not cards:
            scope = f" with type={args.type}" if args.type else ""
            print(f"No cards in {HORUS_DIR}/{backlog.BACKLOG_DIR}/{scope}.")
            return 0
        for c in cards:
            parallel = c.parallel or "unstated"
            surface = ", ".join(c.surface) if c.surface else "unverified"
            print(f"{c.name}  [{c.status}]  priority={c.priority or '-'} tier={c.tier or '-'} type={c.type} parallel={parallel}")
            print(f"    {c.title}")
            print(f"    surface: {surface}")
            if c.shipped_pr or c.shipped_sha:
                print(f"    shipped: pr={c.shipped_pr or '-'} sha={c.shipped_sha or '-'}")
        return 0

    if args.backlog_cmd == "migrate":
        if args.apply and (rc := _enforce_version_floor(root)) is not None:
            return rc
        actions = backlog_migrate.migrate_inline_backlog(root, apply=args.apply)
        mode = "Applying" if args.apply else "Checking"
        print(f"{mode} inline '## Backlog' -> cards migration in {root}\n")
        for a in actions:
            print(f"  [{a.status}] {a.message}")
        if any(a.status == "error" for a in actions):
            return 2
        if not args.apply and any(a.status in ("would-create", "would-update") for a in actions):
            print("\nDry run only. Re-run with `--apply` to write these cards and update PRD.md.")
            return 1
        return 0

    if args.backlog_cmd == "claim":
        if (rc := _enforce_version_floor(root)) is not None:
            return rc
        claimed, findings = backlog.claim(root, args.name, force=args.force)
        healthy = _print_findings(findings)
        if claimed:
            print(f"{'Claimed' if healthy else 'Claimed (forced)'}: {args.name}")
            return 0
        if any(f.level == "fail" for f in findings):
            return 2
        print(f"error: refusing to claim '{args.name}' — resolve the warning(s) above, or re-run with --force")
        return 1

    if args.backlog_cmd == "ship":
        if (rc := _enforce_version_floor(root)) is not None:
            return rc
        try:
            card = backlog.ship(root, args.name, pr=str(args.pr), sha=args.sha)
        except FileExistsError as exc:
            print(f"error: {exc}")
            return 2
        if card is None:
            print(f"error: no backlog card named '{args.name}'")
            return 2
        print(f"Shipped: {card.name} (PR #{card.shipped_pr}, {card.shipped_sha})")
        return 0

    if args.backlog_cmd == "review":
        if (rc := _enforce_version_floor(root)) is not None:
            return rc
        if not (args.note or args.verdict):
            print("error: a review needs --note and/or --verdict")
            return 2
        card = backlog.add_review(
            root,
            args.name,
            author=args.by or backlog.default_author(root),
            source=args.source,
            verdict=args.verdict,
            note=args.note,
        )
        if card is None:
            print(f"error: no backlog card named '{args.name}'")
            return 2
        print(f"Review appended to {card.path.relative_to(root)} — commit it to sync "
              "(`horus close --commit --push`).")
        return 0

    print(f"Unsupported backlog command: {args.backlog_cmd}")
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
        if not getattr(args, "no_isolate", False):
            isolated, msg = config.isolate_account(agent, args.alias)
            print(("Isolated by default — " if isolated else "Note: ") + msg)
        return 0

    if getattr(args, "isolate", False):
        target = args.alias_name or config.alias_for(identifier)
        if not target:
            print("No account to isolate (pass --alias-name, or log in so an alias can be resolved).")
            return 1
        isolated, msg = config.isolate_account(agent, target)
        print(("Isolated — " if isolated else "Could not isolate: ") + msg)
        return 0 if isolated else 1

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
    if tool not in native_hooks.SHELL_TOOL_NAMES or not _is_gh_pr_merge_command(command):
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


def _is_gh_pr_merge_command(command: str) -> bool:
    """Recognize gh-pr-merge only where a shell command may begin.

    Quoted prompt text remains one token, so e.g. horus-run with a prompt that
    mentions the spelling is not mistaken for a merge. Compound commands remain
    useful fast feedback: cd repo && gh pr merge is recognized after the operator.
    CI is the hard gate; malformed/complex shell syntax safely returns false here.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return False

    at_command = True
    for index, token in enumerate(tokens):
        if token and all(char in ";&|\n" for char in token):
            at_command = True
            continue
        if not at_command:
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
            continue
        if (
            token.casefold() in {"gh", "gh.exe"}
            and index + 2 < len(tokens)
            and tokens[index + 1:index + 3] == ["pr", "merge"]
        ):
            return True
        at_command = False
    return False


def _print_product_audit_advisory(root: Path) -> None:
    """One non-blocking product-audit staleness line (advisory; never a gate)."""
    from horus import product_audit

    line = product_audit.advisory_line(root, installed=__version__)
    if line:
        print(f"\n[advisory] {line}")


def cmd_close(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if (rc := _enforce_version_floor(root)) is not None:
        return rc

    if getattr(args, "hook", False):
        # PreToolUse merge-gate mode (reads the tool call from stdin).
        return _close_merge_hook(root)

    if getattr(args, "check", False):
        # Gate mode (scriptable / CI): only dashboard-freshness signals, verdict + exit
        # code, no ritual prompt and no usage/drift noise.
        print(f"Closure freshness check: {root}\n")
        base_ref = getattr(args, "base_ref", None)
        freshness = (
            closure.pr_freshness_gate(root, base_ref)
            if base_ref
            else closure.boundary_freshness_gate(root)
        )
        findings = freshness + closure.checkpoint_gate(root)
        healthy = _print_findings(findings)
        if healthy and base_ref and closure.continuity_granularity(root) != "delivery":
            print(
                "\nDelivery accepted — git evidence is durable; canonical continuity may remain "
                "pending until the next configured boundary."
            )
        elif healthy:
            print("\nFresh — canonical continuity and work are checkpointed.")
        else:
            print(
                "\nStale — update continuity (run the horus-consolidate skill) and commit/push "
                "before closing/merging."
            )
        return 0 if healthy else 1

    print(f"Closure check: {root}\n")
    if args.commit:
        _, detail = closure.commit_continuity(root, args.message, push=args.push)
        print(f"\n--commit: {detail}")
        # Acting close reports only the state after its own mutation. Printing
        # pre-commit dirty warnings and then ending in success made a healthy
        # checkpoint look unresolved. Recomputing remains essential: it catches
        # residual hook edits, failed pushes, and unsuccessful/no-op commits.
    findings = closure.closure_status(root, usage_threshold=args.usage_threshold)
    healthy = _print_findings(findings)
    _print_product_audit_advisory(root)

    if healthy and args.commit:
        print("\nContinuity captured — boundary checkpoint committed and ready to resume anywhere.")
        return 0

    prompt = templates.CLOSURE_PROMPT_V3 if frontmatter.has_prd(root) else templates.CLOSURE_PROMPT
    print("\n" + prompt)
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
    # A token that sits where a command can start: line start, after a shell
    # separator/subshell, or after a common wrapper. Anchoring here is what keeps a
    # mere *mention* (a path like horus/dashboard.py, a grep pattern, a pytest
    # target) from matching — only invocations block.
    cmd_pos = (
        r"(?:^|[;&|(`]\s*|\$\(\s*"
        r"|\b(?:sudo|exec|nohup|setsid|env|time|xargs|command)\s+"
        r"|\b(?:uv|uvx|poetry|pdm|pipx)\s+run\s+)"
    )
    # Relaunching the Horus app/dashboard from inside its own host: `horus` invoked
    # as a command with app/dashboard as its immediate subcommand.
    if re.search(rf"{cmd_pos}horus\s+(app|dashboard)\b", lowered):
        return True
    if re.search(r"-m\s+horus(\.cli)?\s+(app|dashboard)\b", lowered):
        return True
    # A service-level restart/stop of the dashboard host (systemd or SysV spelling).
    if re.search(
        r"\b(systemctl|service)\b[^;&|]*"
        r"\b(restart|try-restart|reload-or-restart|stop|kill)\b[^;&|]*\bhorus",
        lowered,
    ) or re.search(r"\bservice\b[^;&|]*\bhorus[^;&|]*\b(restart|stop)\b", lowered):
        return True
    # A kill verb invoked as a command, aimed — within the same command segment —
    # at the host PID specifically…
    kill_verb = rf"{cmd_pos}(taskkill(\.exe)?|stop-process|kill|pkill|killall)\b"
    if host_pid and re.search(rf"{kill_verb}[^;&|]*\b{re.escape(host_pid)}\b", lowered):
        return True
    # …or at the process that *is* the host: the Python interpreter, or the host
    # identified by name (`horus` / `dashboard`).
    if re.search(
        rf"{kill_verb}[^;&|]*(\bpython(w)?(\.exe)?\b|\bhorus\b|\bdashboard\b)", lowered
    ):
        return True
    return False


def _is_worker_global_state_delete(command: str) -> bool:
    """Match a narrow destructive command aimed at user-global agent state."""
    lowered = command.lower().replace("\\", "/")
    cmd_pos = (
        r"(?:^|[;&|(`]\s*|\$\(\s*"
        r"|\b(?:sudo|exec|nohup|setsid|env|time|xargs|command)\s+)"
    )
    destructive = re.compile(
        rf"{cmd_pos}(?:rm|rmdir|rd|del|remove-item)\b(?P<args>[^;&|]*)",
        re.IGNORECASE,
    )
    home = Path.home().as_posix().lower().rstrip("/")
    protected_prefixes = (
        "~/.horus", "~/.claude", "~/.codex",
        "$home/.horus", "$home/.claude", "$home/.codex",
        "${home}/.horus", "${home}/.claude", "${home}/.codex",
        "%userprofile%/.horus", "%userprofile%/.claude", "%userprofile%/.codex",
        "$env:userprofile/.horus", "$env:userprofile/.claude", "$env:userprofile/.codex",
        f"{home}/.horus", f"{home}/.claude", f"{home}/.codex",
    )
    for match in destructive.finditer(lowered):
        segment = match.group(0).replace('"', "").replace("'", "")
        if any(prefix in segment for prefix in protected_prefixes):
            return True
    return False


def _guard_host_hook(root: Path) -> int:
    """PreToolUse gate for hosted-session and tracked-worker shell footguns.

    Hosted sessions cannot kill their own dashboard host. Tracked workers cannot
    destructively clean user-global Horus/Claude/Codex state. Normal attended
    terminals remain unaffected; ambiguous commands are allowed.
    """
    hook_input = _read_hook_stdin()
    tool = hook_input.get("tool_name") or hook_input.get("toolName") or ""
    tool_input = hook_input.get("tool_input") or hook_input.get("toolInput") or {}
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    if tool not in native_hooks.SHELL_TOOL_NAMES or not command:
        return 0
    if os.environ.get("HORUS_RUN_WORKER") == "1" and _is_worker_global_state_delete(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": templates.WORKER_GLOBAL_STATE_INSTRUCTION,
            }
        }))
        return 0
    if os.environ.get("HORUS_HOSTED_SESSION") != "1":
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


def _usage_account(target: str) -> str | None:
    """Alias of the account this session runs under (registered alias when known,
    else the stable ``acct-<sha6>`` tag), so usage snapshots are keyed per account
    and never cross-contaminate between accounts sharing one machine."""
    try:
        if target == "codex":
            from horus import codex_usage as _codex_usage  # local import to keep the top lean

            ident = _codex_usage.current_account()
        else:
            ident = claude_usage.current_account()
        return config.alias_for(ident)
    except Exception:  # noqa: BLE001 (identity is best-effort; None = default cache key)
        return None


def _usage_bands(threshold: float) -> list[float]:
    """Closure-escalation bands: the configured threshold plus the emergency band."""
    return sorted({float(threshold), usage_snapshot.GUARD_EMERGENCY})


def _current_band(percent: float, bands: list[float]) -> float | None:
    """The highest band ``percent`` has crossed, or None while below all bands."""
    crossed = [b for b in bands if percent >= b]
    return crossed[-1] if crossed else None


def _closure_sentinel_kind(event: str) -> str:
    """Separate sentinels per hook event: the soft UserPromptSubmit advisory must
    never consume the Stop hook's (stronger) closure prompt — sharing one marker let
    a session sail from the threshold to the cutoff on a single soft nudge."""
    return "closure-advisory" if event == "UserPromptSubmit" else "closure"


def _emit_usage_closure(event: str, level: str) -> None:
    if event == "UserPromptSubmit":
        # Pre-task: inject usage *context* before the agent acts on the user's prompt.
        # Advisory only — it must defer to the user's explicit request (and push), never
        # replace it with a closure-only commit.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": templates.USAGE_CLOSURE_ADVISORY.format(level=level),
            }
        }))
    else:  # Stop: block the stop and ask the user how to proceed (close now vs push ahead).
        print(json.dumps({"decision": "block", "reason": templates.USAGE_CLOSURE_PROMPT.format(level=level)}))


def _snapshot_level(snap: usage_snapshot.UsageSnapshot | None) -> str:
    if snap is None or snap.percent is None:
        return "near a limit"
    return f"at {snap.percent:.0f}% (resets {snap.resets_at or 'unknown reset'})"


def _usage_check_claude(args: argparse.Namespace) -> int:
    if not args.hook:
        report = claude_usage.latest_usage()
        findings = claude_usage.usage_findings(threshold=args.threshold, report=report)
        healthy = _print_findings(findings)
        return 0 if healthy else 1

    # Hook mode: drive the session into the closure routine when over budget. The
    # cached snapshot is account-scoped and shared with the PreToolUse guard, so the
    # Stop/UserPromptSubmit hot path costs a file read, not an OAuth fetch.
    snap = usage_snapshot.cached_usage("claude", _usage_account("claude"))
    if snap is None or snap.percent is None:
        return 0
    band = _current_band(snap.percent, _usage_bands(args.threshold))
    if band is None:
        return 0
    hook_input = _read_hook_stdin()
    if hook_input.get("stop_hook_active"):  # we already triggered a Stop continuation
        return 0
    session_id = str(hook_input.get("session_id", "unknown"))
    event = hook_input.get("hook_event_name", "Stop")
    kind = _closure_sentinel_kind(event)
    # Band escalation, not a timer: fire once per band per usage window, so a user who
    # chose to push ahead is re-asked only when usage crosses the next band.
    if native_hooks.band_sentinel_fired(session_id, kind=kind, band=band, reset=snap.resets_at):
        return 0
    native_hooks.mark_band_sentinel(session_id, kind=kind, band=band, reset=snap.resets_at)
    _emit_usage_closure(event, _snapshot_level(snap))
    return 0


def _usage_account_mapping(target: str) -> tuple[dict[str, str], str]:
    """The alias -> isolated-dir mapping for ``target`` and its env-var name."""
    if target == "claude":
        return config.load_account_config_dirs(), "CLAUDE_CONFIG_DIR"
    return config.load_account_codex_homes(), "CODEX_HOME"


def _overseer_collision(target: str, alias: str, mapped: Path) -> bool:
    """True when the requested isolated account is the same underlying account this
    session runs under — a dispatched worker would share the overseer's rate-limit
    pool, so the isolation is nominal only."""
    try:
        if target == "claude":
            ambient = claude_usage.current_account()
            requested = claude_usage.current_account(mapped / ".claude.json")
        else:
            ambient = codex_usage.current_account()
            requested = codex_usage.current_account(mapped)
        if ambient and requested and ambient == requested:
            return True
        return bool(ambient) and config.alias_for(ambient) == alias
    except Exception:  # noqa: BLE001 (identity is best-effort; no evidence = no warning)
        return False


def _usage_check_account(args: argparse.Namespace) -> int:
    """Explicit account-scoped check: resolve the isolated mapping for the alias
    without touching the ambient login. An unknown alias fails (exit 2) rather than
    silently reporting the ambient account's usage as if it were the target's."""
    alias = args.account
    target = args.target
    if args.hook:
        print("--account is incompatible with --hook: hooks always read the ambient session account.")
        return 2
    mapping, kind = _usage_account_mapping(target)
    mapped = mapping.get(alias)
    if not mapped:
        known = ", ".join(sorted(mapping)) or "none configured"
        print(f"Unknown {target} account alias {alias!r} (isolated accounts: {known}).")
        print("Refusing the ambient-login fallback for an explicit --account check.")
        return 2

    print(f"account: {alias} ({target}; {kind} {mapped})")
    if target == "claude":
        print("source:  live OAuth /usage read of the isolated credentials")
    else:
        print("source:  local rollout telemetry — only as fresh as this account's latest Codex activity")
    if _overseer_collision(target, alias, Path(mapped)):
        print(
            f"  [warn] overseer==worker: {alias!r} is the account this session runs under — "
            "a dispatched worker shares its rate-limit pool (advisory; nothing is blocked)"
        )

    snap = usage_snapshot.refresh_usage(target, alias)
    if snap is None:
        print("no usage signal for this account (missing/expired credentials, offline, or no telemetry yet)")
        return 0
    fresh = snap.without_expired_windows()
    over = False
    for label, pct, reset, fresh_pct in (
        ("5h", snap.percent, snap.resets_at, fresh.percent),
        ("weekly", snap.weekly_percent, snap.weekly_resets_at, fresh.weekly_percent),
    ):
        if pct is None:
            print(f"{label} window: no reading")
        elif fresh_pct is None:
            print(f"{label} window: snapshot stale (reset {reset} has passed)")
        else:
            print(f"{label} window: {pct:.0f}% (resets {reset or 'unknown reset'})")
            over = over or pct >= args.threshold
    if over:
        print(f"  [warn] usage at/over the {args.threshold:.0f}% threshold — a risky dispatch target this window")
    return 1 if over else 0


def cmd_usage_check(args: argparse.Namespace) -> int:
    if getattr(args, "account", None):
        return _usage_check_account(args)
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
        event = hook_input.get("hook_event_name") or hook_input.get("hookEventName") or "Stop"
        # Codex telemetry has no reliable band signal, so it keeps the time-based
        # re-arm — but with per-event sentinels, matching the Claude path.
        kind = _closure_sentinel_kind(event)
        if native_hooks.sentinel_fired(session_id, kind=kind):
            return 0
        native_hooks.mark_sentinel_fired(session_id, kind=kind)
        _emit_usage_closure(event, _snapshot_level(usage_snapshot.cached_usage("codex", _usage_account("codex"))))
        return 0
    healthy = _print_findings(findings)
    return 0 if healthy else 1


def _emit_pretooluse_context(text: str) -> None:
    """Inject advisory context on a PreToolUse hook (never a deny)."""
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}
    }))


def _guard_session_id(hook_input: dict) -> str:
    return str(
        hook_input.get("session_id")
        or hook_input.get("sessionId")
        or os.environ.get("HORUS_RUN_SESSION_ID")
        or "unknown"
    )


def _emergency_state_save(root: Path, session_id: str, percent: float, reset: str) -> int:
    """Perform the worker-aware emergency state-save once per window, then inject
    context. Never denies the tool call; any rescue failure is reported, not raised."""
    if native_hooks.sentinel_fired(session_id, kind="rescue", rearm_seconds=native_hooks.RESCUE_REARM_SECONDS):
        return 0  # already rescued this window — stay quiet
    native_hooks.mark_sentinel_fired(session_id, kind="rescue")
    try:
        result = rescue.emergency_rescue(root, session_id=session_id)
        detail = result.detail
    except Exception as exc:  # noqa: BLE001 (a rescue must never crash the hook)
        detail = f"automatic state-save hit an error ({exc}); commit your work manually"
    _emit_pretooluse_context(
        templates.USAGE_RESCUE_ADVISORY.format(percent=f"{percent:.0f}", reset=reset, detail=detail)
    )
    return 0


def _usage_guard_hook(root: Path, target: str) -> int:
    """PreToolUse usage guard: advisory near the limit, emergency state-save at the
    top. Always stdout JSON + exit 0; a missing/unreadable snapshot is a silent pass."""
    try:
        snap = usage_snapshot.cached_usage(target, _usage_account(target))
    except Exception:  # noqa: BLE001 (guard invariant: never let the hook error out)
        return 0
    if snap is None or snap.percent is None:
        return 0
    pct = snap.percent
    if pct < usage_snapshot.GUARD_ADVISORY:
        return 0

    hook_input = _read_hook_stdin()
    session_id = _guard_session_id(hook_input)
    reset = snap.resets_at or "unknown reset"

    if pct >= usage_snapshot.GUARD_EMERGENCY:
        return _emergency_state_save(root, session_id, pct, reset)

    # Advisory band [90, 97): inject once per re-arm window so it doesn't nag.
    if native_hooks.sentinel_fired(session_id, kind="guard-advisory"):
        return 0
    native_hooks.mark_sentinel_fired(session_id, kind="guard-advisory")
    _emit_pretooluse_context(templates.USAGE_GUARD_ADVISORY.format(percent=f"{pct:.0f}", reset=reset))
    return 0


def cmd_usage_guard(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if getattr(args, "hook", False):
        return _usage_guard_hook(root, args.target)
    # Non-hook invocation: report the current snapshot for this target.
    snap = usage_snapshot.cached_usage(args.target, _usage_account(args.target))
    if snap is None or snap.percent is None:
        print(f"No {args.target} usage signal available.")
        return 0
    print(f"{args.target} 5h usage {snap.percent:.0f}% (resets {snap.resets_at or 'unknown reset'})")
    return 0


def _checkpoint_hook(root: Path, *, block: bool) -> int:
    """Stop-hook mode: warn (default) or block (opt-in) when the working tree is dirty
    or has unpushed commits. Silent + exit 0 when the checkpoint is clean or on any
    trouble — the hook signals only via stdout JSON and never a non-zero exit, so the
    `|| exit 0` guard can't mask a real decision."""
    # Per-turn harvesting is the old high-granularity behavior.  Handoff (the
    # default) and manual modes leave session notes untouched until an explicit
    # boundary close, avoiding a post-commit hook edit after every delivery.
    if closure.continuity_granularity(root) == "delivery":
        try:
            closure.harvest_checkpoint(root)
        except Exception:  # noqa: BLE001 (guard invariant: never let the hook error out)
            pass
    try:
        findings = closure.checkpoint_gate(root)
    except Exception:  # noqa: BLE001 (guard invariant: never let the hook error out)
        return 0
    warnings = [f.message for f in findings if f.level in ("warn", "fail")]
    if not warnings:
        return 0  # already checkpointed — stay quiet

    hook_input = _read_hook_stdin()
    # Avoid a Stop → block → Stop loop (the agent sets this once a hook fired the stop).
    if hook_input.get("stop_hook_active") or hook_input.get("stopHookActive"):
        return 0
    session_id = _guard_session_id(hook_input)
    # Fire once per re-arm window so a dirty-tree turn doesn't nag every stop.
    if native_hooks.sentinel_fired(session_id, kind="checkpoint"):
        return 0
    native_hooks.mark_sentinel_fired(session_id, kind="checkpoint")

    detail = "; ".join(warnings)
    if block:
        print(json.dumps({"decision": "block", "reason": templates.CHECKPOINT_STOP_INSTRUCTION.format(detail=detail)}))
    else:
        print(json.dumps({"systemMessage": templates.CHECKPOINT_ADVISORY.format(detail=detail)}))
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if getattr(args, "harvest", False):
        # Deterministic incremental consolidation. Never errors out (hook-safe).
        try:
            n, note = closure.harvest_checkpoint(root)
        except Exception:  # noqa: BLE001 (guard invariant: a harvest must never wedge a commit)
            return 0
        if not getattr(args, "hook", False):
            print(f"Harvested {n} commit(s) into {note}" if n else "No new commits to harvest.")
        return 0
    if getattr(args, "hook", False):
        return _checkpoint_hook(root, block=getattr(args, "block", False))
    # Non-hook invocation (scriptable / CI): the git-checkpoint verdict + exit code.
    print(f"Checkpoint check: {root}\n")
    healthy = _print_findings(closure.checkpoint_gate(root))
    print("\nCheckpointed — working tree committed and local commits pushed." if healthy
          else "\nNot checkpointed — commit and push (see above) before closing.")
    return 0 if healthy else 1


def _fetch_check_hook(root: Path) -> int:
    """SessionStart-hook mode: fetch (TTL-cached) and inject a behind-origin warning
    as session context. Silent + exit 0 when fresh, offline, or on any trouble — the
    fetch-first rule as a deterministic signal, advisory only (never blocks)."""
    try:
        state = fetchcheck.fetch_and_state(root)
        message = fetchcheck.warning_line(state)
    except Exception:  # noqa: BLE001 (guard invariant: never let the hook error out)
        return 0
    if not message:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        }
    }))
    return 0


def cmd_fetch_check(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if getattr(args, "hook", False):
        return _fetch_check_hook(root)
    # Non-hook invocation (scriptable): fetch + behind/ahead verdict and exit code.
    state = fetchcheck.fetch_and_state(root, ttl=0 if getattr(args, "fresh", False) else fetchcheck.TTL_SECONDS)
    if state is None:
        print(f"Not a git repository: {root}")
        return 0
    print(gitstate.summary(state))
    message = fetchcheck.warning_line(state)
    if message:
        print(message)
        return 1
    return 0


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
            print("PreToolUse gate: blocks hosted-session self-restarts and tracked-worker")
            print("destructive cleanup of user-global Horus/Claude/Codex state.")
        if kind in ("checkpoint", "all"):
            action = native_hooks.install_codex_checkpoint_hook(root)
            print(f"[{action.status}] {action.message}")
            print("Stop hook: on session end, warns when the working tree is dirty or has")
            print("unpushed commits (the committed-and-pushed checkpoint discipline).")
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
            print("PreToolUse gate: blocks hosted-session self-restarts and tracked-worker")
            print("destructive cleanup of user-global Horus/Claude/Codex state. Normal")
            print("attended terminals are unaffected.")
        if kind in ("checkpoint", "all"):
            action = native_hooks.install_claude_checkpoint_hook(root)
            print(f"[{action.status}] {action.message}")
            print("Stop hook: on session end, warns (non-blocking) when the working tree is")
            print("dirty or has unpushed commits — the committed-and-pushed checkpoint")
            print("discipline as an observed signal, not a remembered habit.")
        if kind in ("fetch-check", "all"):
            action = native_hooks.install_claude_fetch_check_hook(root)
            print(f"[{action.status}] {action.message}")
            print("SessionStart hook: fetches (TTL-cached) and injects a behind-origin")
            print("warning into the session context — the fetch-first rule as a signal.")
        return 0
    print(f"unsupported hook target: {args.target}")
    return 2


def cmd_upgrade_project(args: argparse.Namespace) -> int:
    if args.structure == "prd":
        if args.all:
            print("error: --structure prd cannot be combined with --all")
            return 2
        root = _resolve_dir(args.path)
        if root is None:
            return 2
        actions = upgrade.upgrade_structure_prd(root, apply=args.apply)
        mode = "Applying" if args.apply else "Checking"
        print(f"{mode} Horus structure migration to PRD in {root}\n")
        for action in actions:
            print(f"  [{action.status}] {action.message}")
        if any(a.status == "error" for a in actions):
            return 2
        if not args.apply and any(a.status == "would-update" for a in actions):
            print("\nDry run only. Re-run with `--apply` to migrate this project to PRD structure.")
            return 1
        return 0

    if args.all:
        if args.path != ".":
            print("error: --all cannot be combined with --path")
            return 2
        return _cmd_upgrade_project_all(args)

    root = _resolve_dir(args.path)
    if root is None:
        return 2
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
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
    if getattr(args, "terminal", False):
        return terminal_app.run()
    root = _resolve_dir(args.path)
    if root is None:
        return 2
    if not getattr(args, "no_detach", False) and companion.relaunch_without_console():
        # Re-spawned under pythonw.exe so no console window lingers; the detached
        # child carries the GUI from here.
        return 0
    open_mode = companion.resolve_open_mode(app_window=args.app_window, tab=args.tab)
    try:
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
    except Exception:
        # Under pythonw / a desktop launcher a crash here is invisible ("the app
        # won't open") — record it where `horus doctor` can point the user.
        import traceback
        companion.log_companion_event(f"companion crashed:\n{traceback.format_exc()}")
        raise


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
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
    if root is None:
        return 2
    print(f"Consolidation check: {root}\n")
    findings = routines.consolidate_signals(root)
    healthy = _print_findings(findings)
    _print_product_audit_advisory(root)
    if frontmatter.has_prd(root):
        print("\n" + templates.CONSOLIDATE_PROMPT_V3)
        if healthy:
            print("PRD backlog already consolidated — nothing to trim or distill.")
        else:
            print("Consolidation candidates above — the in-loop agent applies the routine.")
        _skill_nudge(root)
        return 0
    print("\n" + templates.CONSOLIDATE_PROMPT)
    if healthy:
        print("Lanes already consolidated — nothing to route or prune.")
    else:
        print("Consolidation candidates above — the in-loop agent applies the routine.")
    _skill_nudge(root)
    return 0


def cmd_distill_history(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
    if root is None:
        return 2
    source = routines.find_source_log(root, args.source)
    print(f"Distill-history check: {root}\n")
    _print_findings(routines.distill_signals(root, source))
    if frontmatter.has_prd(root):
        print("\n" + templates.DISTILL_HISTORY_PROMPT_V3)
    else:
        print("\n" + templates.DISTILL_HISTORY_PROMPT)
    return 0


def cmd_infer(args: argparse.Namespace) -> int:
    root = _resolve_dir(args.path)
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
    if root is None:
        return 2
    print(f"Infer check: {root}\n")
    _print_findings(routines.infer_signals(root))
    prompt = templates.INFER_PROMPT_V3 if frontmatter.has_prd(root) else templates.INFER_PROMPT_V2
    print("\n" + prompt)
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


def cmd_skill_map(args: argparse.Namespace) -> int:
    """Read-only machine-wide skill inventory (the observe-first Skill map slice)."""
    from horus import skillmap

    groups = skillmap.skill_map()
    if not groups:
        print("No skills found on this machine (projects, user scope, or account dirs).")
        return 0

    print("Skill map — this machine only (repo-local skills travel with git; user/account scopes do not)\n")
    for group in groups:
        if group["bundled"]:
            badge = f"horus-bundled v{group['latest']}"
            if group["stale"]:
                badge += f", {group['stale']} install(s) behind"
        else:
            badge = "foreign (presence only — provenance unknown)"
        print(f"{group['name']}  [{badge}]")
        if group["description"]:
            print(f"    {group['description']}")
        for inst in group["instances"]:
            where = {
                "project": f"project {inst['owner']}",
                "user": "user scope",
                "account": f"account {inst['owner']}",
            }[inst["scope"]]
            version = f"v{inst['version']}" if inst["version"] is not None else "no version marker"
            flag = {"stale": "  <- STALE", "unmarked": "  <- unmarked"}.get(inst["verdict"], "")
            print(f"    - {where} ({inst['agent']}): {version}{flag}")
        print()
    stale_total = sum(g["stale"] for g in groups)
    if stale_total:
        print(f"{stale_total} bundled install(s) behind the CLI — `horus upgrade-project --all` refreshes project scopes.")
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if (rc := _enforce_version_floor(root)) is not None:
        return rc
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


def cmd_verify_inventory(args: argparse.Namespace) -> int:
    source_path = Path(args.source).resolve()
    produced_path = Path(args.produced).resolve()
    try:
        source = verify_inventory.load_manifest(source_path, expect_nonempty=not args.allow_empty_source)
        produced = verify_inventory.load_manifest(produced_path, expect_nonempty=not args.allow_empty_produced)
    except verify_inventory.EmptyWalkError as exc:
        print(f"error: {exc}")
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    result = verify_inventory.reconcile(source, produced)
    for line in verify_inventory.format_report(result):
        print(line)
    return 0 if result.clean else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="horus", description=__doc__)
    parser.add_argument("--version", action="version", version=f"horus {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="scaffold .horus/ and managed instruction blocks")
    p_init.add_argument("path", nargs="?", default=".", help="project root (default: cwd)")
    p_init.add_argument("--yes", "-y", action="store_true", help="auto-confirm block injection")
    p_init.add_argument("--no-input", action="store_true", help="never prompt; skip injection")
    p_init.add_argument("--no-skills", action="store_true", help="don't scaffold agent skills")
    p_init.add_argument("--no-hooks", action="store_true", help="don't install native agent hooks")
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
        "--structure",
        choices=("prd",),
        help="opt-in continuity structure migration (currently: prd)",
    )
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
    p_dash.add_argument(
        "--exposed", action="store_true",
        help="enforce the [access] Cloudflare gate (for a tunnel-exposed dashboard); "
             "refuses to start without an [access] block. Local mode never reads it.",
    )
    p_dash.add_argument(
        "--reload", action="store_true",
        help="restart the identified dashboard on this host/port from the current install; preserves exposed mode",
    )
    p_dash.set_defaults(func=cmd_dashboard)

    p_status = sub.add_parser("status", help="print git freshness + latest session for all registered projects")
    p_status.set_defaults(func=cmd_status)

    p_fleet = sub.add_parser(
        "fleet",
        help="print one-line git/session/next-step context for every project except horus-agent",
    )
    p_fleet.add_argument(
        "--backlog", action="store_true",
        help="print the fleet-wide backlog card roll-up instead (all registered "
             "projects, cockpit included) — deterministic, read-only, no fetch",
    )
    p_fleet.add_argument(
        "--review", action="store_true",
        help="render the curator manifest using fetched remote continuity as shipped "
             "truth, kept separate from local checkout state",
    )
    p_fleet.add_argument(
        "--stdout", action="store_true",
        help="with --backlog or --review: print full JSON instead of the human-readable view",
    )
    p_fleet.add_argument(
        "--type", choices=backlog.CARD_TYPES, default="",
        help="with --backlog: filter to one card type (bug|feature|chore|task)",
    )
    p_fleet.add_argument(
        "--project", default=None,
        help="with --backlog: roll up just ONE registered project (matched by directory basename)",
    )
    p_fleet.set_defaults(func=cmd_fleet)

    p_capabilities = sub.add_parser(
        "capabilities",
        help="EXPERIMENTAL: read-only fleet capability catalog (Shipped ledgers + CLI surface) as JSON",
    )
    p_capabilities.add_argument(
        "--out",
        default=None,
        help="output JSON path (default: ~/.horus/capabilities.json fleet-wide, "
             "or <project>/.horus/capabilities.json with --project)",
    )
    p_capabilities.add_argument("--stdout", action="store_true", help="print the full JSON to stdout instead of a summary")
    p_capabilities.add_argument(
        "--project",
        default=None,
        help="regenerate ONE registered project's stamped capability record (resolved "
             "by directory basename) instead of the fleet-wide catalog; writes "
             "<project>/.horus/capabilities.json and prints it. Defaults to the current "
             "project when run from inside its root with no --project",
    )
    p_capabilities.add_argument(
        "--models",
        action="store_true",
        help="EXPERIMENTAL: print the DATA-ONLY model-calibration roll-up (measured datums "
             "+ owner priors) instead of the fleet catalog — describes what was measured and "
             "flagged; never recommends a model",
    )
    p_capabilities.add_argument(
        "--matrix",
        action="store_true",
        help="EXPERIMENTAL: print the DISPLAY-ONLY delegation decision matrix — the tier "
             "ladder (measured datums + owner priors) joined with the shape->tier and "
             "verification-depth tables from the delegation-rubric skill; renders the "
             "rubric deterministically, never picks or routes a model",
    )
    p_capabilities.add_argument(
        "--verbose", "--full",
        dest="verbose",
        action="store_true",
        help="with --models/--matrix: restore the fuller tier-ladder columns (LAST "
             "per-run outcomes, RESEARCHED date) on top of the concise default "
             "(model/tier/price/datums/capability); --stdout JSON always carries "
             "every field regardless of this flag",
    )
    p_capabilities.set_defaults(func=cmd_capabilities)

    p_envelope = sub.add_parser(
        "envelope",
        help="manage standing dispatch envelopes (bounded pre-authorization for unattended runs)",
        description=(
            "A standing envelope is the owner's bounded, expiring authorization for "
            "unattended dispatch. It BOUNDS only — it never selects a card, account, or "
            "model. `horus run --unattended --envelope <name> --card <card>` validates "
            "against it and refuses to exceed it. Stored machine-locally (it names "
            "accounts); never commit one to a repo."
        ),
    )
    envelope_sub = p_envelope.add_subparsers(dest="envelope_cmd", required=True)

    p_env_create = envelope_sub.add_parser(
        "create", help="create a bounded, expiring standing envelope"
    )
    p_env_create.add_argument("name", help="envelope name (letters, digits, '.', '_', '-')")
    p_env_create.add_argument(
        "--expires", required=True, metavar="YYYY-MM-DD",
        help="last day this envelope authorizes anything (inclusive) — no evergreen authority",
    )
    p_env_create.add_argument(
        "--card", action="append", default=[], metavar="NAME",
        help="a card name this envelope authorizes (repeatable)",
    )
    p_env_create.add_argument(
        "--branch", default="", metavar="NAME",
        help="authorize every card stamped `branch: <NAME>` (a vision branch)",
    )
    p_env_create.add_argument(
        "--account", action="append", default=[], metavar="ALIAS", required=True,
        help="an isolated account this envelope may dispatch to (repeatable)",
    )
    p_env_create.add_argument(
        "--tier", action="append", default=[], metavar="TIER", required=True,
        help="an allowed card `tier:` label (repeatable). An allow-list, not an ordered "
             "ceiling, so it stays correct across tier-vocabulary changes",
    )
    p_env_create.add_argument(
        "--effort", action="append", default=[], metavar="EFFORT",
        help="an allowed effort label (repeatable); omit to allow any effort",
    )
    p_env_create.add_argument(
        "--usage-floor", type=int, default=0, metavar="PCT",
        help="refuse to dispatch when the account has less than PCT%% of its window "
             "remaining (default: 0). Unknown capacity always refuses",
    )
    p_env_create.add_argument(
        "--max-attempts", type=int, default=1, metavar="N",
        help="maximum dispatches of any one card over the envelope's life (default: 1)",
    )
    p_env_create.add_argument(
        "--max-dispatches-per-day", type=int, default=1, metavar="N",
        help="maximum dispatches per UTC day across all cards (default: 1)",
    )
    p_env_create.add_argument(
        "--allow-merge", action="store_true",
        help="permit unattended merge on green gates; omit for verify-and-escalate only "
             "(the default, and the away-mode cut line)",
    )
    p_env_create.set_defaults(func=cmd_envelope_create)

    p_env_list = envelope_sub.add_parser("list", help="list standing envelopes and their state")
    p_env_list.add_argument("--stdout", action="store_true", help="emit JSON instead of a table")
    p_env_list.set_defaults(func=cmd_envelope_list)

    p_env_show = envelope_sub.add_parser("show", help="show one envelope's bounds and what it has spent")
    p_env_show.add_argument("name", help="envelope name")
    p_env_show.add_argument("--stdout", action="store_true", help="emit JSON instead of a table")
    p_env_show.set_defaults(func=cmd_envelope_show)

    p_env_revoke = envelope_sub.add_parser(
        "revoke",
        help="ground the envelope: pending scheduled dispatches are refused from now on "
             "(live attached sessions keep running)",
    )
    p_env_revoke.add_argument("name", help="envelope name")
    p_env_revoke.set_defaults(func=cmd_envelope_revoke)

    p_datum = sub.add_parser(
        "datum",
        help="EXPERIMENTAL: record the qualitative half of a measured run datum",
    )
    datum_sub = p_datum.add_subparsers(dest="datum_cmd", required=True)
    p_datum_close = datum_sub.add_parser(
        "close",
        help="attach an agent-supplied outcome/shape/note to a run's auto-captured datum",
    )
    p_datum_close.add_argument("run_id", help="session id or unique prefix (see `horus sessions`)")
    p_datum_close.add_argument(
        "--outcome",
        required=True,
        choices=datums.OUTCOMES,
        help=(
            "how the run went (agent's judgment — void marks aborted/untested; "
            "died and void are excluded from the quality denominator)"
        ),
    )
    p_datum_close.add_argument("--shape", default=None, help="the run's shape: ambiguity/volume/runtime, your words")
    p_datum_close.add_argument("--note", default=None, help="a short free note")
    p_datum_close.add_argument(
        "--oversight",
        default=None,
        choices=datums.OVERSIGHT_LEVELS,
        help="supervisor-steps bucket: light=brief+one review+accept, moderate=one bounce OR a "
             "reinstall/live-probe cycle, heavy=multiple bounce/poll cycles or a debugging tail",
    )
    p_datum_close.add_argument(
        "--follow-on",
        type=int,
        default=None,
        metavar="N",
        help="count of ADDITIONAL worker/PR cycles this dispatch spawned beyond the primary one",
    )
    p_datum_close.add_argument(
        "--counterfactual",
        default=None,
        choices=datums.COUNTERFACTUALS,
        help="in hindsight, the mode that would have been cheapest for this task",
    )
    p_datum_close.add_argument(
        "--dividend",
        default=None,
        choices=datums.DIVIDENDS,
        help="headline judgment: worker detail/context the overseer avoided, minus the fixed "
             "supervisor tax (brief+review+gate+merge+reinstall+datum/continuity close)",
    )
    p_datum_close.add_argument(
        "--card",
        default=None,
        metavar="PATH-OR-SLUG",
        help="one-act acceptance: stamp the delivered backlog card `status: done` + `shipped: "
             "<date>` in the target project's PRIMARY checkout (resolved from this datum's own "
             "`project`, which may be a --worktree path — unless PATH-OR-SLUG already resolves "
             "as a path), then print a stale-continuity warning if that target's own "
             ".horus/PRD.md looks behind this run's completion (never auto-fixed)",
    )
    p_datum_close.add_argument(
        "--remove-worktree",
        action="store_true",
        help="with --card: if this datum's `project` was a linked git worktree, remove it (and "
             "its branch) once the card is stamped — ONLY when the branch looks merged (its "
             "upstream is gone, or its tip is an ancestor of the fetched default branch); "
             "otherwise the worktree is left in place and the reason is printed",
    )
    p_datum_close.set_defaults(func=cmd_datum_close)

    p_datum_report = datum_sub.add_parser(
        "report",
        help="render recent per-worker model/account/runtime/attempt/outcome/usage actuals",
    )
    p_datum_report.add_argument(
        "--path", default=None,
        help="limit to an exact worker project path (default: all projects)",
    )
    p_datum_report.add_argument(
        "--all", action="store_true",
        help="include worker runs older than 24 hours",
    )
    p_datum_report.add_argument("--json", action="store_true", help="emit the breakdown as JSON")
    p_datum_report.set_defaults(func=cmd_datum_report)

    p_datum_migrate = datum_sub.add_parser(
        "migrate-names",
        help="one-time idempotent rename of bare model aliases (sonnet/haiku/opus) to canonical versioned names",
    )
    p_datum_migrate.set_defaults(func=cmd_datum_migrate_names)

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
        p_app.add_argument(
            "--terminal",
            action="store_true",
            help="run the terminal-native project/session application instead of the desktop companion",
        )
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

    p_tui = sub.add_parser("tui", help="run the terminal-native Horus project/session application")
    p_tui.set_defaults(func=cmd_terminal_app)

    p_forget = sub.add_parser("forget", help="remove a project from the dashboard registry")
    p_forget.add_argument("path", nargs="?", default=".", help="project root (default: cwd)")
    p_forget.set_defaults(func=cmd_forget)

    p_prune = sub.add_parser("prune", help="drop registered projects whose .horus/ is gone")
    p_prune.set_defaults(func=cmd_prune)

    p_sessions = sub.add_parser("sessions", help="list tracked agent sessions (reconciles live state)")
    p_sessions.add_argument("--prune", action="store_true", help="drop finished/dead sessions instead of listing")
    p_sessions.add_argument(
        "--all", action="store_true",
        help="show every tracked session, including long-stale ones (default: running + last 24h only)",
    )
    p_sessions.add_argument("--json", action="store_true", help="emit persisted session rows as machine-readable JSON")
    p_sessions.set_defaults(func=cmd_sessions)

    p_focus = sub.add_parser("focus", help="raise a running session's terminal window (best-effort, Windows)")
    p_focus.add_argument("session_id", help="session id (or a unique prefix)")
    p_focus.set_defaults(func=cmd_focus)

    p_attach = sub.add_parser("attach", help="attach this terminal to a running Horus tmux session")
    p_attach.add_argument("session_id", help="session id (or a unique prefix)")
    p_attach.set_defaults(func=cmd_attach)

    p_stop = sub.add_parser("stop", help="close a running Horus tmux session")
    p_stop.add_argument("session_id", help="session id (or a unique prefix)")
    p_stop.set_defaults(func=cmd_session_stop)

    p_reap = sub.add_parser(
        "reap",
        help="kill abandoned Horus tmux sessions (never one that's attached, live, or recently active)",
    )
    p_reap.set_defaults(func=cmd_reap)

    p_merge_watch = sub.add_parser(
        "merge-watch",
        help="poll a PR/commit's required checks on the exact sha until they settle; exit 0 green / 1 red",
    )
    p_merge_watch.add_argument("ref", help="a PR number, PR URL, or literal commit sha")
    p_merge_watch.add_argument("--path", default=".", help="repo root to run gh/git in (default: cwd)")
    p_merge_watch.add_argument(
        "--interval", type=float, default=mergewatch.DEFAULT_INTERVAL, metavar="SECONDS",
        help=f"poll interval (default: {mergewatch.DEFAULT_INTERVAL:g}s)",
    )
    p_merge_watch.add_argument(
        "--timeout", type=float, default=mergewatch.DEFAULT_TIMEOUT, metavar="SECONDS",
        help=f"give up waiting after this long (default: {mergewatch.DEFAULT_TIMEOUT:g}s)",
    )
    p_merge_watch.set_defaults(func=cmd_merge_watch)

    p_reinstall = sub.add_parser(
        "reinstall",
        help="uv cache clean + force-reinstall from PATH, then verify a marker landed in the installed surface",
    )
    p_reinstall.add_argument("path", nargs="?", default=".", help="source to install from (default: cwd)")
    p_reinstall.add_argument(
        "--verify", required=True, metavar="MARKER", dest="verify",
        help="string to grep for in the freshly-installed surface (found/absent, reported and exit-coded)",
    )
    p_reinstall.add_argument("--package", default=reinstall.DEFAULT_PACKAGE, help="uv tool package name")
    p_reinstall.add_argument("--python", default=reinstall.DEFAULT_PYTHON, help="python version for the tool env")
    p_reinstall.set_defaults(func=cmd_reinstall)

    p_run = sub.add_parser("run", help="spawn (or resume) an agent session, tracked in the registry")
    p_run.add_argument("prompt", help="the prompt to send the agent")
    p_run.add_argument(
        "--agent",
        default=None,
        help="adapter to use (claude | codex | fake; default: match --worker, otherwise claude)",
    )
    p_run.add_argument("--account", default=None, help="account alias to run under (uses its isolated config dir)")
    p_run.add_argument("--model", default=None, help="model alias (e.g. haiku, sonnet, opus)")
    p_run.add_argument(
        "--effort",
        default=None,
        choices=adapters.EFFORT_LEVELS,
        help="reasoning effort for the launched worker (default: the agent's own default). "
             "codex: mapped to `-c model_reasoning_effort=<level>` (server-validated — an "
             "unsupported level for the target model fails the turn, not silently ignored). "
             "claude: mapped directly to the CLI's own `--effort <level>` flag.",
    )
    p_run.add_argument(
        "--posture",
        default=None,
        choices=[p.value for p in adapters.PermissionPosture],
        help="permission posture (default: default; overrides any --worker preset)",
    )
    p_run.add_argument(
        "--worker",
        default=None,
        choices=sorted(_WORKER_POSTURE),
        help="agent + posture preset for an unattended worker: claude=full-auto, codex=auto-edit. "
             "The safe codex workspace-write sandbox has network/socket access off; git "
             "fetch/push/PR and local-server/browser verification require --posture full-auto "
             "(bypasses approvals and sandbox). The default posture stalls a headless claude. "
             "Infers --agent when omitted; --agent and --posture win if also given.",
    )
    p_run.add_argument("--resume", metavar="SESSION_ID", help="resume an existing session by id")
    p_run.add_argument(
        "--expect-delivery", action="store_true",
        help="explicitly expect a reviewable git/PR delivery; never inferred from prompt text",
    )
    p_run.add_argument("--path", default=".", help="project root to run in (default: cwd)")
    p_run.add_argument(
        "--target", choices=(terminal_sessions.CURRENT, terminal_sessions.TMUX),
        default=None,
        help="execution host: current process or managed tmux (tmux requires --detach). "
             "Default: current, or tmux under --unattended",
    )
    p_run.add_argument(
        "--detach", action="store_true",
        help="return after managed-tmux runner PID handoff (requires --worker --target tmux)",
    )
    p_run.add_argument(
        "--worktree",
        metavar="BRANCH",
        default=None,
        help="run in a git worktree for BRANCH at <repo-parent>/<repo-name>-wt-<branch-slug> "
             "(created from HEAD if the branch is new, reused if it already exists); "
             "the registry row records the worktree path. Remove with `git worktree remove`.",
    )
    p_run.add_argument(
        "--watch",
        action="store_true",
        help="open a watcher terminal following this session's log (best-effort; headless runs continue without it)",
    )
    p_run.add_argument(
        "--force",
        action="store_true",
        help="launch even when the target account's 5h/weekly usage is near exhaustion (skips the preflight refusal)",
    )
    p_run.add_argument(
        "--refuse-on-unknown",
        action="store_true",
        help="for a critical launch: refuse (exit 2) when usage capacity is unknown for the "
             "target agent+account, instead of the default courtesy notice + proceed",
    )
    p_run.add_argument(
        "--unattended",
        action="store_true",
        help="this dispatch has no live supervisor: requires --envelope (every bound enforced; "
             "--force does not override them), and implies the safe posture — managed tmux, "
             "detached, --worker <agent>, and a per-card `auto/<card>` worktree — so the run is "
             "attachable and cannot disturb the main checkout. Explicit flags win",
    )
    p_run.add_argument(
        "--envelope",
        default=None,
        metavar="NAME",
        help="validate this dispatch against the owner's standing envelope NAME and refuse to "
             "exceed its bounds (see `horus envelope`); requires --card",
    )
    p_run.add_argument(
        "--card",
        default=None,
        metavar="NAME",
        help="the backlog card this dispatch is for; its `tier:`/`branch:` frontmatter is what "
             "the envelope's bounds are checked against",
    )
    p_run.set_defaults(func=cmd_run)

    p_tail = sub.add_parser("tail", help="print and follow a session's run log until it finishes")
    p_tail.add_argument(
        "session_id",
        nargs="?",
        default=None,
        help="session id or unique prefix (default: the most recently updated running session)",
    )
    p_tail.set_defaults(func=cmd_tail)

    p_open = sub.add_parser("open", help="open an interactive agent session in its own terminal (tracked)")
    p_open.add_argument("path", nargs="?", default=".", help="project root to open in (default: cwd)")
    p_open.add_argument("--agent", default="claude", help="adapter to use (claude | codex | fake; default: claude)")
    p_open.add_argument("--account", default=None, help="account alias to run under (uses its isolated config dir)")
    p_open.add_argument("--model", default=None, help="model alias (e.g. haiku, sonnet, opus)")
    p_open.add_argument(
        "--mode",
        choices=("fresh", "resume"),
        default="fresh",
        help="fresh session or seed it with the project's Horus resume prompt (default: fresh)",
    )
    p_open.add_argument(
        "--target",
        choices=terminal_sessions.TARGETS,
        default=terminal_sessions.WINDOW,
        help="display target: new window, current TTY, or persistent tmux (default: window)",
    )
    p_open.add_argument(
        "--detach",
        action="store_true",
        help="with --target tmux, create the session without attaching this terminal",
    )
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

    p_brainstorm = sub.add_parser(
        "brainstorm",
        help="launch a tracked brainstorm session (scoped PRD context + topic) that drafts a plan",
    )
    p_brainstorm.add_argument("topic", help="the topic to brainstorm on")
    p_brainstorm.add_argument("--path", default=".", help="project root (default: cwd)")
    p_brainstorm.add_argument("--agent", default="claude", help="adapter to use (claude | codex | fake; default: claude)")
    p_brainstorm.add_argument("--account", default=None, help="account alias to run under (uses its isolated config dir)")
    p_brainstorm.add_argument("--model", default=None, help="model alias (e.g. haiku, sonnet, opus)")
    p_brainstorm.add_argument(
        "--posture",
        default="default",
        choices=[p.value for p in adapters.PermissionPosture],
        help="permission posture (default: default)",
    )
    p_brainstorm.set_defaults(func=cmd_brainstorm)

    p_vscode = sub.add_parser(
        "vscode-task",
        help="write .vscode/tasks.json tasks that start claude/codex seeded with `horus resume` (Ctrl+Shift+B)",
    )
    p_vscode.add_argument("--path", default=".", help="project root (default: cwd)")
    p_vscode.set_defaults(func=cmd_vscode_task)

    p_resume = sub.add_parser("resume", help="print the minimum-context fresh-session handoff for this project")
    p_resume.add_argument("--path", default=".", help="project root (default: cwd)")
    p_resume.add_argument("--preflight", action="store_true", help="print the compact deterministic session-start digest")
    p_resume.add_argument("--fleet", action="store_true", help="with --preflight: include every registered project")
    p_resume.add_argument("--no-fetch", action="store_true", help="with --preflight: skip the sanctioned git fetch refresh")
    p_resume.add_argument("--stdout", action="store_true", help="with --preflight: print JSON for tooling")
    p_resume.set_defaults(func=cmd_resume)

    p_session = sub.add_parser("session", help="create an optional local recovery note")
    session_sub = p_session.add_subparsers(dest="session_cmd", required=True)
    p_session_new = session_sub.add_parser("new", help="create an optional local recovery note")
    p_session_new.add_argument("title", help="short session title")
    p_session_new.add_argument("--path", default=".", help="project root (default: cwd)")
    p_session_new.add_argument(
        "--agent", choices=("claude", "codex", "unknown"), default=None,
        help="agent attribution (default: HORUS_AGENT/runtime inference, otherwise unknown)",
    )
    p_session_new.add_argument("--account", default=None, help="account tag (default: auto-detect for the attributed agent)")
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

    p_backlog = sub.add_parser(
        "backlog", help="work with .horus/backlog/ cards (parallel-safety metadata + claim check)"
    )
    backlog_sub = p_backlog.add_subparsers(dest="backlog_cmd", required=True)
    p_backlog_list = backlog_sub.add_parser(
        "list", help="list backlog cards with status/priority/tier/type/parallel/surface"
    )
    p_backlog_list.add_argument("--path", default=".", help="project root (default: cwd)")
    p_backlog_list.add_argument(
        "--type", choices=backlog.CARD_TYPES, default="",
        help="filter to one card type (bug|feature|chore|task); default: no filter",
    )
    p_backlog_list.set_defaults(func=cmd_backlog)

    p_backlog_migrate = backlog_sub.add_parser(
        "migrate",
        help="migrate an inline PRD '## Backlog' section to one card per item (idempotent, per-project)",
    )
    p_backlog_migrate.add_argument("--path", default=".", help="project root (default: cwd)")
    p_backlog_migrate.add_argument("--apply", action="store_true", help="write cards + update PRD.md (default is dry-run/report)")
    p_backlog_migrate.set_defaults(func=cmd_backlog)

    p_backlog_claim = backlog_sub.add_parser(
        "claim", help="claim a backlog card (warns on overlap with in-progress cards; --force to override)"
    )
    p_backlog_claim.add_argument("name", help="card filename stem, e.g. companion-signals")
    p_backlog_claim.add_argument("--path", default=".", help="project root (default: cwd)")
    p_backlog_claim.add_argument("--force", action="store_true", help="claim despite overlap/exclusive warnings")
    p_backlog_claim.set_defaults(func=cmd_backlog)

    p_backlog_ship = backlog_sub.add_parser(
        "ship", help="stamp merge provenance and move a shipped card to backlog/archive/"
    )
    p_backlog_ship.add_argument("name", help="card filename stem, e.g. companion-signals")
    p_backlog_ship.add_argument("--pr", required=True, metavar="N", help="merged pull-request number")
    p_backlog_ship.add_argument("--sha", required=True, metavar="SHA", help="merged commit SHA")
    p_backlog_ship.add_argument("--path", default=".", help="project root (default: cwd)")
    p_backlog_ship.set_defaults(func=cmd_backlog)

    p_backlog_review = backlog_sub.add_parser(
        "review",
        help="append a review/comment entry to a card's `## Reviews` section (append-only)",
    )
    p_backlog_review.add_argument("name", help="card filename stem, e.g. companion-signals")
    p_backlog_review.add_argument("--note", default="", help="free-text review body")
    p_backlog_review.add_argument("--verdict", default="", help="short verdict, e.g. approve / needs-work")
    p_backlog_review.add_argument("--by", default="", help="reviewer attribution (default: git user.name)")
    p_backlog_review.add_argument(
        "--source", choices=backlog.REVIEW_SOURCES, default="manual",
        help="who authored this review (agents pass --source agent)",
    )
    p_backlog_review.add_argument("--path", default=".", help="project root (default: cwd)")
    p_backlog_review.set_defaults(func=cmd_backlog)

    p_account = sub.add_parser("account", help="show the detected agent account, alias, and isolation dir")
    p_account.add_argument("--agent", default="claude", help="which agent's account to inspect (default: claude)")
    p_account.add_argument("--set", dest="alias", metavar="ALIAS", help="set the public alias for the detected account")
    p_account.add_argument("--set-dir", metavar="PATH", help="map an account alias to its CLAUDE_CONFIG_DIR (isolation)")
    p_account.add_argument("--set-codex-home", metavar="PATH", help="map an account alias to its CODEX_HOME (Codex isolation)")
    p_account.add_argument("--alias-name", metavar="ALIAS", help="with --set-dir / --set-codex-home / --isolate: which alias to map (default: current account's)")
    p_account.add_argument("--isolate", action="store_true", help="provision the canonical isolated dir (~/.horus/accounts/<agent>-<alias>) from the current login and map it")
    p_account.add_argument("--no-isolate", action="store_true", help="with --set: only alias, do not auto-provision an isolated dir")
    p_account.set_defaults(func=cmd_account)

    p_close = sub.add_parser("close", help="verify continuity (git-aware) and print the closure ritual")
    p_close.add_argument("--path", default=".", help="project root (default: cwd)")
    p_close.add_argument(
        "--check", action="store_true",
        help="gate mode: print the freshness verdict and exit non-zero if the lanes are stale (for scripts/CI)",
    )
    p_close.add_argument(
        "--base-ref",
        help="with --check: compare product/source changes with this fetched ref; "
             "delivery granularity requires canonical continuity, while handoff/manual "
             "defer it to a visible pending boundary (for required PR CI)",
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
        help="guard hosted-session and tracked-worker shell safety",
    )
    p_guard.add_argument("--path", default=".", help="project root (default: cwd)")
    p_guard.add_argument(
        "--hook", action="store_true",
        help="PreToolUse hook mode: block hosted-session self-restarts and tracked-worker "
             "destructive cleanup of user-global agent state",
    )
    p_guard.set_defaults(func=cmd_guard_host)

    p_checkpoint = sub.add_parser(
        "checkpoint",
        help="check the git commit-and-push checkpoint (working tree clean + commits pushed)",
    )
    p_checkpoint.add_argument("--path", default=".", help="project root (default: cwd)")
    p_checkpoint.add_argument(
        "--hook", action="store_true",
        help="Stop-hook mode: warn (default) when the tree is dirty or has unpushed "
             "commits; always exit 0, signalling only via stdout JSON",
    )
    p_checkpoint.add_argument(
        "--block", action="store_true",
        help="with --hook: block the stop and instruct the agent to checkpoint "
             "(reserved for repos that opt into hard enforcement; warn-only otherwise)",
    )
    p_checkpoint.add_argument(
        "--harvest", action="store_true",
        help="incremental consolidation: append commit messages since the last "
             "harvest to the latest session note + advance the marker (deterministic, "
             "no LLM). Meant for a PostToolUse(git commit) hook; combine with --hook to "
             "stay silent.",
    )
    p_checkpoint.set_defaults(func=cmd_checkpoint)

    p_fetch_check = sub.add_parser(
        "fetch-check",
        help="fetch (TTL-cached) and report whether local refs are behind origin",
    )
    p_fetch_check.add_argument("--path", default=".", help="project root (default: cwd)")
    p_fetch_check.add_argument(
        "--hook", action="store_true",
        help="SessionStart-hook mode: inject a behind-origin warning as session "
             "context; always exit 0, signalling only via stdout JSON",
    )
    p_fetch_check.add_argument(
        "--fresh", action="store_true",
        help="skip the fetch TTL cache and fetch now",
    )
    p_fetch_check.set_defaults(func=cmd_fetch_check)

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
    p_usage_check.add_argument(
        "--account",
        help="isolated account alias to check (resolves its mapped CLAUDE_CONFIG_DIR/"
             "CODEX_HOME without changing the ambient login; unknown aliases fail, "
             "never fall back to the ambient account)",
    )
    p_usage_check.set_defaults(func=cmd_usage_check)

    p_usage_guard = usage_sub.add_parser(
        "guard",
        help="PreToolUse usage guard: advisory near the limit + worker-aware emergency state-save",
    )
    p_usage_guard.add_argument("--path", default=".", help="project root (default: cwd)")
    p_usage_guard.add_argument(
        "--target", choices=("codex", "claude"), default="claude",
        help="which app's cached usage snapshot to read (default: claude)",
    )
    p_usage_guard.add_argument(
        "--hook",
        action="store_true",
        help="hook mode: inject advisory context / run the emergency state-save; never denies; always exit 0",
    )
    p_usage_guard.set_defaults(func=cmd_usage_guard)

    p_hook = sub.add_parser("hook", help="install native app hooks")
    hook_sub = p_hook.add_subparsers(dest="hook_cmd", required=True)
    p_hook_install = hook_sub.add_parser("install", help="install a native app hook")
    p_hook_install.add_argument("--path", default=".", help="project root (default: cwd)")
    p_hook_install.add_argument("--target", choices=("codex", "claude"), required=True, help="native app target")
    p_hook_install.add_argument(
        "--kind", choices=("usage", "merge", "guard", "checkpoint", "fetch-check", "all"), default="usage",
        help="which hook(s): usage = quota→closure (default); merge = PreToolUse gate on "
             "`gh pr merge`; guard = PreToolUse gate that stops a hosted session "
             "restarting/killing its own host; checkpoint = Stop hook that warns on a "
             "dirty tree / unpushed commits; fetch-check = SessionStart behind-origin "
             "warning (claude only); all = every applicable hook.",
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
    p_skill_map = skill_sub.add_parser(
        "map",
        help="read-only inventory of every skill installed on this machine (projects, user scope, accounts)",
    )
    p_skill_map.set_defaults(func=cmd_skill_map)

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

    p_verify_inventory = sub.add_parser(
        "verify-inventory",
        help="reconcile a source manifest/tree against a produced tree by count and size",
    )
    p_verify_inventory.add_argument(
        "source", help="source manifest (JSON {path: size}) or directory to walk",
    )
    p_verify_inventory.add_argument(
        "produced", help="produced/committed directory to walk (or a JSON manifest)",
    )
    p_verify_inventory.add_argument(
        "--allow-empty-source", action="store_true",
        help="do not error if the source walk/manifest is empty (default: error — an "
             "empty walk of an expected-non-empty source is a retryable failure)",
    )
    p_verify_inventory.add_argument(
        "--allow-empty-produced", action="store_true",
        help="do not error if the produced walk/manifest is empty (same default as --allow-empty-source)",
    )
    p_verify_inventory.set_defaults(func=cmd_verify_inventory)

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
