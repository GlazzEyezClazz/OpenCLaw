#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash restore_openclaw.sh
# Optional env overrides:
#   REPO_SSH=git@github.com:GlazzEyezClazz/OpenCLaw.git
#   WORKSPACE_DIR=/home/safeuser/.openclaw/workspace

REPO_SSH="${REPO_SSH:-git@github.com:GlazzEyezClazz/OpenCLaw.git}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/home/safeuser/.openclaw/workspace}"
BACKUP_SCRIPT="$WORKSPACE_DIR/scripts/daily_kb_backup.sh"

echo "[1/8] Installing system dependencies"
sudo apt-get update
sudo apt-get install -y git curl build-essential libsecret-1-0 libsecret-1-dev

echo "[2/8] Ensuring Node.js/npm present"
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js missing. Install Node.js (v20+) and rerun."
  exit 1
fi

echo "[3/8] Installing global CLIs"
npm install -g openclaw clawhub mcporter

echo "[4/8] Restoring workspace from GitHub"
mkdir -p "$(dirname "$WORKSPACE_DIR")"
if [ -d "$WORKSPACE_DIR/.git" ]; then
  git -C "$WORKSPACE_DIR" fetch --all --tags
  git -C "$WORKSPACE_DIR" pull --ff-only
else
  git clone "$REPO_SSH" "$WORKSPACE_DIR"
fi

echo "[5/8] Installing skills from ClawHub"
cd "$WORKSPACE_DIR"
clawhub install find-skills || true
clawhub install google-workspace-mcp --force || true

echo "[6/8] Configuring MCP server"
mcporter config add google-workspace --command "npx" --arg "-y" --arg "@presto-ai/google-workspace-mcp" --scope home || true

echo "[7/8] Restoring daily midnight (YEKT) backup cron"
( crontab -l 2>/dev/null | grep -v "daily_kb_backup.sh"; echo "0 19 * * * $BACKUP_SCRIPT" ) | crontab -

echo "[8/8] Done"
echo "Next steps:"
echo "  - Run: clawhub login"
echo "  - Trigger Google OAuth once (any mcporter google-workspace call)"
echo "  - Start OpenClaw services as you normally do"
