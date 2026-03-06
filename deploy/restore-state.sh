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
copy_if_exists "$ROOT_DIR/configs/" "$TARGET/"
copy_if_exists "$ROOT_DIR/patches/" "$TARGET/"

echo "[DONE] restore-state complete"
