#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.openclaw/workspace"

mkdir -p "$TARGET/skills" "$TARGET/memory"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -e "$src" ]]; then
    rsync -a "$src" "$dst"
    echo "[OK] synced: $src -> $dst"
  else
    echo "[SKIP] missing: $src"
  fi
}

copy_if_exists "$ROOT_DIR/skills/" "$TARGET/skills/"
copy_if_exists "$ROOT_DIR/memory/" "$TARGET/memory/"
copy_if_exists "$ROOT_DIR/configs/workspace-scripts/" "$TARGET/scripts/"
copy_if_exists "$ROOT_DIR/patches/" "$TARGET/patches/"

# OpenClaw daemon config + env (if bundled)
mkdir -p "$HOME/.openclaw"
if [[ -f "$ROOT_DIR/configs/openclaw.json" ]]; then
  cp -f "$ROOT_DIR/configs/openclaw.json" "$HOME/.openclaw/openclaw.json"
  echo "[OK] restored ~/.openclaw/openclaw.json"
else
  echo "[SKIP] configs/openclaw.json not bundled"
fi

if [[ -f "$ROOT_DIR/configs/openclaw.env" ]]; then
  cp -f "$ROOT_DIR/configs/openclaw.env" "$HOME/.openclaw/.env"
  chmod 600 "$HOME/.openclaw/.env" || true
  echo "[OK] restored ~/.openclaw/.env"
else
  echo "[SKIP] configs/openclaw.env not bundled"
fi

echo "[DONE] restore-state complete"
