"""Optional CLIProxyAPI integration — vision-branch-x4 stage 1 (mode B / augment).

Run GPT models INSIDE Claude Code, *alongside* Claude, by pointing Claude Code at a
local translating proxy (Docker) that rides subscription OAuth. When enabled, Claude
Code's ``/model`` picker shows Claude AND the proxy's GPT models (gateway discovery),
all served through the proxy; when disabled, the env is removed and the proxy leaves
the path entirely — native Claude, no dependency.

Horus OWNS NO RUNTIME (branch principle 4): it orchestrates an external Docker proxy
and writes Claude Code's own ``settings.json`` env, both reversibly. The integration
is opt-in and off by default (principle 1); enabling is GUIDED and VERIFIED before it
rewires anything global (principle 2) — it refuses to wire Claude Code to a proxy that
is not up and serving.

Proved live 2026-07-18 (`research/2026-07-18-x4-stage0-gpt-in-claude-code-spike.md`):
both GPT (via the Codex sub) and Claude (via the Claude sub) serve through one proxy.
"""

from __future__ import annotations

import json
import secrets
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from horus import config, schedule

DEFAULT_IMAGE = "eceasy/cli-proxy-api:latest"
DEFAULT_PORT = 8317
CONTAINER_NAME = schedule.PROXY_UNIT  # the docker --name, matched by the service unit
# The device/callback login flavours per provider CLIProxyAPI supports here.
LOGIN_FLAG = {"codex": "-codex-device-login", "claude": "-claude-login"}


def state_path() -> Path:
    return config.config_dir() / "proxy.json"


def default_state() -> dict:
    return {
        "enabled": False,
        "image": DEFAULT_IMAGE,
        "port": DEFAULT_PORT,
        "api_key": "",
        "auth_dir": str(Path.home() / ".cli-proxy-api"),
        "config_path": str(config.config_dir() / "cliproxy" / "config.yaml"),
    }


def load_state() -> dict:
    path = state_path()
    state = default_state()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state.update({k: v for k, v in loaded.items() if k in state})
        except (OSError, ValueError):
            pass
    return state


def save_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def ensure_api_key(state: dict) -> str:
    """The client api-key clients present as ``ANTHROPIC_AUTH_TOKEN``; minted once."""
    if not state.get("api_key"):
        state["api_key"] = "sk-horus-" + secrets.token_urlsafe(16)
        save_state(state)
    return state["api_key"]


def docker_available() -> bool:
    return shutil.which("docker") is not None


def logged_in_providers(state: dict) -> list[str]:
    """Providers with a stored OAuth token in the auth dir (``codex``/``claude``/…)."""
    auth = Path(state["auth_dir"]).expanduser()
    found: set[str] = set()
    if auth.is_dir():
        for f in auth.glob("*.json"):
            head = f.name.split("-", 1)[0]
            if head in {"codex", "claude", "gemini", "grok", "kimi"}:
                found.add(head)
    return sorted(found)


def ensure_config_file(state: dict) -> Path:
    """Write the CLIProxyAPI ``config.yaml`` (port + client api-key + auth dir). The
    auth dir is the container-internal mount target ``/root/.cli-proxy-api``."""
    key = ensure_api_key(state)
    path = Path(state["config_path"]).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Managed by Horus (vision-branch-x4 proxy integration).\n"
        f"port: {int(state['port'])}\n"
        'auth-dir: "/root/.cli-proxy-api"\n'
        "api-keys:\n"
        f'  - "{key}"\n',
        encoding="utf-8",
    )
    return path


def proxy_env(state: dict) -> dict[str, str]:
    """The exact env Claude Code needs to reach the proxy and surface its models."""
    return {
        "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{int(state['port'])}",
        "ANTHROPIC_AUTH_TOKEN": ensure_api_key(state),
        "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1",
    }


def docker_run_command(state: dict) -> tuple[str, ...]:
    """The ``docker run`` argv the service runs (the always-on proxy server)."""
    auth = Path(state["auth_dir"]).expanduser()
    cfg = Path(state["config_path"]).expanduser()
    port = int(state["port"])
    return (
        "docker", "run", "--rm", "--name", CONTAINER_NAME,
        "-p", f"127.0.0.1:{port}:{port}",
        "-v", f"{auth}:/root/.cli-proxy-api",
        "-v", f"{cfg}:/CLIProxyAPI/config.yaml",
        state["image"],
        "/CLIProxyAPI/CLIProxyAPI", "-config", "/CLIProxyAPI/config.yaml",
    )


def login_command(state: dict, provider: str) -> tuple[str, ...]:
    """A one-shot ``docker run`` that logs ``provider`` in (device/callback OAuth).
    Claude uses a localhost callback, so its callback port is published + pinned."""
    auth = Path(state["auth_dir"]).expanduser()
    cfg = Path(state["config_path"]).expanduser()
    base = [
        "docker", "run", "--rm",
        *(["-p", "54545:54545"] if provider == "claude" else []),
        "-v", f"{auth}:/root/.cli-proxy-api",
        "-v", f"{cfg}:/CLIProxyAPI/config.yaml",
        state["image"],
        "/CLIProxyAPI/CLIProxyAPI", "-config", "/CLIProxyAPI/config.yaml",
        LOGIN_FLAG[provider], "-no-browser",
    ]
    if provider == "claude":
        base += ["-oauth-callback-port", "54545"]
    return tuple(base)


def reachable(state: dict, *, timeout: float = 3.0) -> tuple[bool, list[str]]:
    """``(ok, model_ids)`` from ``GET /v1/models`` with the client key. No exceptions."""
    url = f"http://127.0.0.1:{int(state['port'])}/v1/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {ensure_api_key(state)}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - localhost only
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False, []
    ids = [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict)]
    return True, [i for i in ids if i]


@dataclass(frozen=True)
class ProxyStatus:
    enabled: bool
    docker: bool
    providers: list[str]
    service_active: bool
    reachable: bool
    model_count: int

    @property
    def ready_to_enable(self) -> bool:
        return self.docker and bool(self.providers)


def status(state: dict | None = None) -> ProxyStatus:
    state = state or load_state()
    docker = docker_available()
    providers = logged_in_providers(state)
    active = schedule.proxy_service_active()
    ok, models = reachable(state) if active else (False, [])
    return ProxyStatus(
        enabled=bool(state.get("enabled")),
        docker=docker,
        providers=providers,
        service_active=active,
        reachable=ok,
        model_count=len(models),
    )


def _claude_config_dirs() -> list[Path]:
    """Every Claude settings.json target: each isolated account + the ambient login
    (the one a plain standalone `claude` uses — the point of a *global* toggle)."""
    dirs = [Path(p) for p in config.load_account_config_dirs().values()]
    dirs.append(Path.home() / ".claude")
    seen: set[str] = set()
    unique: list[Path] = []
    for d in dirs:
        key = str(d.expanduser().resolve())
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def enable(state: dict | None = None) -> tuple[bool, str]:
    """Guided, verified enable: refuse unless Docker is present and a provider is
    logged in; start the service; wait until it is actually serving; only THEN write
    the env into every Claude settings.json. Never wires Claude Code to a dead proxy."""
    state = state or load_state()
    if not docker_available():
        return False, "Docker is not installed — the proxy runs as a Docker container."
    providers = logged_in_providers(state)
    if not providers:
        return False, "No provider logged in. Run `horus proxy login codex` (and/or claude) first."
    ensure_config_file(state)
    try:
        if not schedule.proxy_service_active():
            schedule.install_proxy_service(command=docker_run_command(state))
    except schedule.ScheduleError as exc:
        return False, f"Could not start the proxy service: {exc}"
    if not _wait_reachable(state):
        return False, "Proxy service started but is not serving /v1/models yet — not wiring Claude Code."
    env = proxy_env(state)
    wrote = sum(1 for d in _claude_config_dirs() if config.write_proxy_env(d, env))
    state["enabled"] = True
    save_state(state)
    return True, f"GPT-via-proxy ON — wired {wrote} Claude settings.json; models available in `/model`."


def disable(state: dict | None = None) -> tuple[bool, str]:
    """Reverse of :func:`enable`: remove the env from every Claude settings.json
    (native Claude restored) and stop the proxy service. Best-effort + idempotent."""
    state = state or load_state()
    cleared = sum(1 for d in _claude_config_dirs() if config.clear_proxy_env(d))
    try:
        schedule.remove_proxy_service()
    except schedule.ScheduleError:
        pass
    state["enabled"] = False
    save_state(state)
    return True, f"GPT-via-proxy OFF — cleared {cleared} Claude settings.json; proxy out of the path."


def _wait_reachable(state: dict, *, tries: int = 15) -> bool:
    import time
    for _ in range(tries):
        if reachable(state)[0]:
            return True
        time.sleep(1)
    return False
