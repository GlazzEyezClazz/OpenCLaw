#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_OPENCLAW="$HOME/.openclaw"
SRC_WS="$HOME/.openclaw/workspace"

mkdir -p "$ROOT_DIR/configs" "$ROOT_DIR/memory" "$ROOT_DIR/skills"

copy() {
  local src="$1" dst="$2"
  if [[ -e "$src" ]]; then
    rsync -a "$src" "$dst"
    echo "[OK] $src -> $dst"
  else
    echo "[SKIP] $src"
  fi
}

copy "$SRC_OPENCLAW/openclaw.json" "$ROOT_DIR/configs/openclaw.json"
copy "$SRC_OPENCLAW/.env" "$ROOT_DIR/configs/openclaw.env"
copy "$SRC_WS/memory/" "$ROOT_DIR/memory/"
copy "$SRC_WS/skills/" "$ROOT_DIR/skills/"
copy "$SRC_WS/scripts/" "$ROOT_DIR/configs/workspace-scripts/"
copy "$SRC_WS/package.json" "$ROOT_DIR/configs/package.json"
copy "$SRC_WS/package-lock.json" "$ROOT_DIR/configs/package-lock.json"

echo "[DONE] state captured into deploy/"
