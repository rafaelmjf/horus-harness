"""Warm up the Claude usage window on demand.

Claude's 5-hour usage window only starts counting from the FIRST turn on an
account — until then `horus usage` reads nothing to track. ``horus warmup`` opens
one cheap throwaway turn ("hi") per Claude account so the window STARTS now, then
exits. Pair it with the scheduler (``horus schedule run --at ... -- warmup``) to
align the window on a heavy day; that pacing stays ad-hoc — there is deliberately
no periodic loop here.

Deterministic + best-effort: one ``claude -p`` subprocess per account under its
own isolated ``CLAUDE_CONFIG_DIR`` (never crosses account credentials); a failure
on one account is reported, never fatal to the others.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Callable

from horus import config

# A tiny turn is all it takes to start the window; the cheapest model keeps a
# repeated (ad-hoc every-5h) warmup close to free.
DEFAULT_PROMPT = "hi"
DEFAULT_MODEL = "haiku"
DEFAULT_TIMEOUT = 120.0


@dataclass(frozen=True)
class WarmupResult:
    account: str
    ok: bool
    detail: str


def claude_accounts() -> list[str]:
    """Every configured Claude account alias (each an isolated CLAUDE_CONFIG_DIR)."""
    return sorted(config.load_account_config_dirs())


def _warm_one(
    account: str, config_dir: str | None, *, prompt: str, model: str | None, timeout: float,
) -> WarmupResult:
    """Open one ``claude -p`` turn under ``config_dir`` to start its window."""
    env = dict(os.environ)
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    argv = ["claude", "-p", prompt]
    if model:
        argv += ["--model", model]
    try:
        result = subprocess.run(  # noqa: S603 - argv list, no shell
            argv, capture_output=True, text=True, timeout=timeout, env=env,
        )
    except FileNotFoundError:
        return WarmupResult(account, False, "claude CLI not found on PATH")
    except subprocess.TimeoutExpired:
        return WarmupResult(account, False, f"timed out after {int(timeout)}s")
    except OSError as exc:
        return WarmupResult(account, False, f"could not launch claude: {exc}")
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()
        return WarmupResult(account, False, tail[-1] if tail else f"exit {result.returncode}")
    return WarmupResult(account, True, "window started")


def warmup(
    accounts: list[str] | None = None,
    *,
    prompt: str = DEFAULT_PROMPT,
    model: str | None = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
    runner: Callable[..., WarmupResult] | None = None,
) -> list[WarmupResult]:
    """Open one cheap turn per Claude account to start its 5h window.

    ``accounts`` limits the run to specific aliases; ``None`` warms every
    configured account, or the default login (``~/.claude``) when none are
    configured. Best-effort — see module docstring. ``runner`` is a test seam."""
    dirs = config.load_account_config_dirs()
    targets = accounts if accounts is not None else (list(dirs) or [None])
    run_one = runner or _warm_one
    results: list[WarmupResult] = []
    for alias in targets:
        cfg = dirs.get(alias) if alias else None
        results.append(run_one(alias or "default", cfg, prompt=prompt, model=model, timeout=timeout))
    return results
