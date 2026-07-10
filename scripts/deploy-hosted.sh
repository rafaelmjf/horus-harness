#!/usr/bin/env bash
# Deploy the latest published horus-harness to the hosted dashboard.
#
# Run this AFTER a horus-harness release is published (manually, or via the
# release->deploy automation). It upgrades the pinned uv-tool install and restarts
# the systemd service that serves the tunnel-fronted dashboard.
#
# Two hard-won details baked in:
#   1. `uv tool install --force --refresh` — NOT `uv tool upgrade --reinstall`.
#      The latter re-reads uv's cached index and silently stays on the old version
#      (observed 0.0.30->0.0.31); --refresh busts the index cache.
#   2. The service runs the pinned install (`~/.local/bin/horus`), so restarting it
#      picks up the upgrade. If the unit still runs a git checkout, repoint it first
#      (see .horus continuity: "repoint systemd unit to pinned install").
set -euo pipefail

SERVICE="${HORUS_HOSTED_SERVICE:-horus-dashboard.service}"
PORT="${HORUS_HOSTED_PORT:-8771}"
PYTHON="${HORUS_TOOL_PYTHON:-3.12}"

# Pin the exact latest version and retry: the release webhook fires the instant a
# release is published, but PyPI's *simple index* (what uv resolves against) lags its
# JSON API by a minute or two — so a plain `--refresh` install races the index and
# silently grabs the PREVIOUS version (observed 0.0.31 for the 0.0.32 release). Install
# `==<latest>` and retry until the index has it.
latest="${HORUS_DEPLOY_VERSION:-}"
if [ -z "$latest" ]; then
  latest="$(curl -s https://pypi.org/pypi/horus-harness/json \
    | grep -oE '"version":"[^"]+"' | head -1 | cut -d'"' -f4 || true)"
fi
if [ -n "$latest" ]; then
  echo "[deploy-hosted] target version: $latest"
else
  echo "[deploy-hosted] WARNING: target version could not be resolved; installing latest available." >&2
fi
installed=""
for attempt in 1 2 3 4 5 6 7 8; do
  if [ -n "$latest" ]; then
    if uv tool install --force --refresh --python "$PYTHON" "horus-harness==$latest"; then
      installed="$latest"
      break
    fi
  else
    if uv tool install --force --refresh --python "$PYTHON" horus-harness; then
      installed="<latest-available>"
      break
    fi
  fi
  if [ "$attempt" != "8" ]; then
    echo "[deploy-hosted] install unavailable (attempt $attempt) — retrying in 20s..."
    sleep 20
  fi
done

if [ -z "$installed" ]; then
  echo "[deploy-hosted] ERROR: install of '${latest:-<latest-available>}' never succeeded after 8 attempts; refusing to restart $SERVICE." >&2
  exit 1
fi

echo "[deploy-hosted] restarting $SERVICE ..."
sudo systemctl restart "$SERVICE"

# Give it a moment to bind, then verify: /health public (200), / gated (403).
sleep 2
health="$(curl -s --max-time 3 "http://127.0.0.1:${PORT}/health" || true)"
root_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:${PORT}/" || true)"
echo "[deploy-hosted] /health -> ${health:-<unreachable>}"
echo "[deploy-hosted] /       -> ${root_code} (expect 403 = still gated)"

if [ "$root_code" != "403" ]; then
  echo "[deploy-hosted] WARNING: hosted dashboard is not returning 403 on / — it may be" >&2
  echo "[deploy-hosted]          ungated. Confirm the unit passes --exposed." >&2
  exit 1
fi

health_version="$(printf '%s' "$health" | python3 -c \
  'import json, sys; value = json.load(sys.stdin).get("version", ""); print(value if isinstance(value, str) else "")' \
  2>/dev/null || true)"
if [ -n "$latest" ]; then
  if [ "$health_version" != "$latest" ]; then
    echo "[deploy-hosted] ERROR: running version '${health_version:-<missing>}' does not match target '$latest' (install completed for '$installed')." >&2
    exit 1
  fi
  echo "[deploy-hosted] done; running version $health_version matches target."
else
  echo "[deploy-hosted] WARNING: install succeeded, but the running version '${health_version:-<missing>}' could not be confirmed against an unresolved target." >&2
  echo "[deploy-hosted] done with target version unconfirmed."
fi
