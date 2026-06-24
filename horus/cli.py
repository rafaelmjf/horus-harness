"""Horus command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from horus import __version__, dashboard, initialize
from horus.continuity import check_project
from horus.instructions import check_drift

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
        root, assume_yes=args.yes, no_input=args.no_input
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="horus", description=__doc__)
    parser.add_argument("--version", action="version", version=f"horus {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="scaffold .horus/ and managed instruction blocks")
    p_init.add_argument("path", nargs="?", default=".", help="project root (default: cwd)")
    p_init.add_argument("--yes", "-y", action="store_true", help="auto-confirm block injection")
    p_init.add_argument("--no-input", action="store_true", help="never prompt; skip injection")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
