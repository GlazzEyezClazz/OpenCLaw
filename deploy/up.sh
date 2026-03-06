#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERR] Missing $ENV_FILE. Run: bash deploy/install.sh"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

echo "[INFO] Applying local OpenClaw state"
bash "$ROOT_DIR/restore-state.sh"

echo "[INFO] Restarting OpenClaw gateway"
openclaw gateway restart || true

echo "[INFO] Status"
openclaw gateway status || true

echo "[DONE] up.sh complete"
