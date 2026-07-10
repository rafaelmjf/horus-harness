"""Tests for the hosted deployment's install and runtime version gates."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deploy-hosted.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_deploy(
    tmp_path: Path,
    *,
    target: str | None = "0.0.34",
    running: str = "0.0.34",
    install_succeeds: bool = True,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"

    _write_executable(
        bin_dir / "curl",
        """#!/usr/bin/env bash
if [[ "$*" == *"pypi.org"* ]]; then
  if [ -n "${FAKE_PYPI_VERSION:-}" ]; then
    printf '{"info":{"version":"%s"}}' "$FAKE_PYPI_VERSION"
  fi
elif [[ "$*" == *"/health"* ]]; then
  printf '{"app":"horus-dashboard","version":"%s","pid":123}' "$FAKE_RUNNING_VERSION"
else
  printf '403'
fi
""",
    )
    _write_executable(
        bin_dir / "uv",
        """#!/usr/bin/env bash
printf 'uv %s\n' "$*" >> "$FAKE_COMMAND_LOG"
[ "$FAKE_INSTALL_SUCCEEDS" = "1" ]
""",
    )
    _write_executable(
        bin_dir / "sudo",
        """#!/usr/bin/env bash
printf 'sudo %s\n' "$*" >> "$FAKE_COMMAND_LOG"
""",
    )
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "FAKE_COMMAND_LOG": str(log),
            "FAKE_INSTALL_SUCCEEDS": "1" if install_succeeds else "0",
            "FAKE_PYPI_VERSION": "" if target is None else target,
            "FAKE_RUNNING_VERSION": running,
        }
    )
    if target is None:
        env.pop("HORUS_DEPLOY_VERSION", None)
    else:
        env["HORUS_DEPLOY_VERSION"] = target

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    commands = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result, commands


def test_deploy_accepts_exact_running_target(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "running version 0.0.34 matches target" in result.stdout
    assert commands[-1] == "sudo systemctl restart horus-dashboard.service"


def test_deploy_rejects_running_version_mismatch(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path, running="0.0.33")

    assert result.returncode != 0
    assert "running version '0.0.33' does not match target '0.0.34'" in result.stderr
    assert commands[-1] == "sudo systemctl restart horus-dashboard.service"


def test_deploy_refuses_restart_when_pinned_install_never_succeeds(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path, install_succeeds=False)

    assert result.returncode != 0
    assert "install of '0.0.34' never succeeded after 8 attempts" in result.stderr
    assert len([command for command in commands if command.startswith("uv ")]) == 8
    assert not any(command.startswith("sudo ") for command in commands)


def test_deploy_warns_when_target_is_unresolved(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path, target=None, running="0.0.34")

    assert result.returncode == 0, result.stderr
    assert "target version could not be resolved" in result.stderr
    assert "could not be confirmed against an unresolved target" in result.stderr
    assert "done with target version unconfirmed" in result.stdout
    assert commands[-1] == "sudo systemctl restart horus-dashboard.service"


def test_deploy_requires_install_success_when_target_is_unresolved(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path, target=None, install_succeeds=False)

    assert result.returncode != 0
    assert "install of '<latest-available>' never succeeded after 8 attempts" in result.stderr
    assert not any(command.startswith("sudo ") for command in commands)
