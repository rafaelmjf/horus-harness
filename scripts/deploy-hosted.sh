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

echo "[deploy-hosted] upgrading pinned horus-harness (index-refresh)..."
uv tool install --force --refresh --python "$PYTHON" horus-harness

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
echo "[deploy-hosted] done."
