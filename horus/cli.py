"""Horus command-line entry point."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from horus import __version__, closure, config, dashboard, infer, initialize, templates
from horus.continuity import HORUS_DIR, SESSIONS_DIR, check_project
from horus.instructions import check_drift, reconcile

_LEVEL_TAG = {"ok": "[ ok ]", "warn": "[warn]", "fail": "[fail]"}


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
        root, assume_yes=args.yes, no_input=args.no_input, infer_sources=not args.no_infer
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
        if not _print_findings(check_project(root)):
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

    today = date.today().isoformat()
    path = sessions / f"{today}-{_slugify(args.title)}.md"
    if path.exists():
        print(f"Already exists: {path}")
        return 1
    path.write_text(
        templates.session_summary(
            title=args.title,
            date=today,
            project=root.name,
            agent=args.agent,
            account=args.account,
            environment=args.environment,
        ),
        encoding="utf-8",
    )
    print(f"Created {path}")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    print(f"Closure check: {root}\n")
    findings = closure.closure_status(root)
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


def cmd_infer(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    inf = infer.infer(root)
    print(f"Inferred for {root.name}:")
    print(f"  sources:     {', '.join(inf.sources) or '(none found)'}")
    print(f"  status:      {inf.status}")
    print(f"  focus:       {inf.current_focus or '(none)'}")
    desc = inf.description if len(inf.description) <= 120 else inf.description[:117] + "..."
    print(f"  description: {desc or '(none)'}")
    print(f"  tasks:       {len(inf.tasks)} found")

    if not args.write:
        print("\n(preview only; rerun with --write to populate .horus/)")
        return 0

    hdir = root / HORUS_DIR
    if not hdir.is_dir():
        print(f"\nNo {HORUS_DIR}/ here (run `horus init` first).")
        return 1
    if not inf.has_content():
        print("\nNothing inferable found; leaving .horus/ unchanged.")
        return 1

    today = date.today().isoformat()
    targets = {
        "project.md": templates.project_md(
            root.name, today, description=inf.description, status=inf.status,
            current_focus=inf.current_focus, sources=inf.sources,
        ),
        "roadmap.md": templates.roadmap_md(
            today, current_focus=inf.current_focus,
            tasks=[(t.state, t.text, t.section) for t in inf.tasks] if inf.tasks else None,
        ),
    }
    wrote = []
    for fname, content in targets.items():
        path = hdir / fname
        if path.exists() and not infer.is_placeholder(path) and not args.force:
            print(f"  skip {fname}: looks customized (use --force to overwrite)")
            continue
        path.write_text(content, encoding="utf-8")
        wrote.append(fname)
    print(f"  wrote: {', '.join(wrote) or '(nothing)'}")
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
    p_init.add_argument("--no-infer", action="store_true", help="use blank templates; do not mine existing files")
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

    p_forget = sub.add_parser("forget", help="remove a project from the dashboard registry")
    p_forget.add_argument("path", nargs="?", default=".", help="project root (default: cwd)")
    p_forget.set_defaults(func=cmd_forget)

    p_prune = sub.add_parser("prune", help="drop registered projects whose .horus/ is gone")
    p_prune.set_defaults(func=cmd_prune)

    p_session = sub.add_parser("session", help="create a new session summary from the template")
    session_sub = p_session.add_subparsers(dest="session_cmd", required=True)
    p_session_new = session_sub.add_parser("new", help="create a new session summary")
    p_session_new.add_argument("title", help="short session title")
    p_session_new.add_argument("--path", default=".", help="project root (default: cwd)")
    p_session_new.add_argument("--agent", default="claude")
    p_session_new.add_argument("--account", default="personal")
    p_session_new.add_argument("--environment", default="host")
    p_session_new.set_defaults(func=cmd_session)

    p_close = sub.add_parser("close", help="verify continuity (git-aware) and print the closure ritual")
    p_close.add_argument("--path", default=".", help="project root (default: cwd)")
    p_close.add_argument("--commit", action="store_true", help="stage+commit the continuity files")
    p_close.add_argument("--push", action="store_true", help="with --commit, also push to origin")
    p_close.add_argument("--message", "-m", help="commit message for --commit")
    p_close.set_defaults(func=cmd_close)

    p_infer = sub.add_parser("infer", help="infer project state from existing files (README, roadmap, CLAUDE.md, ...)")
    p_infer.add_argument("--path", default=".", help="project root (default: cwd)")
    p_infer.add_argument("--write", action="store_true", help="populate .horus/ from the inference")
    p_infer.add_argument("--force", action="store_true", help="overwrite even non-placeholder .horus/ files")
    p_infer.set_defaults(func=cmd_infer)

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
    # Output may include emoji from inferred content; avoid crashing on consoles
    # with a narrow encoding (e.g. Windows cp1252).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
