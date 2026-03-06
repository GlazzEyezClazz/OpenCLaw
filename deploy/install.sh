#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
ENV_FILE="$ROOT_DIR/.env"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"

exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "[INFO] Bootstrap start: $(date -Is)"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || return 1
}

apt_install() {
  sudo apt-get update -y
  sudo apt-get install -y "$@"
}

install_docker() {
  if require_cmd docker; then
    echo "[OK] docker already installed"
    return
  fi
  echo "[INFO] Installing docker"
  apt_install ca-certificates curl gnupg lsb-release
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
}

install_node() {
  if require_cmd node; then
    echo "[OK] node already installed: $(node -v)"
    return
  fi
  echo "[INFO] Installing Node.js 20 LTS"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
}

install_openclaw() {
  if require_cmd openclaw; then
    echo "[OK] openclaw already installed: $(openclaw --version || true)"
    return
  fi
  echo "[INFO] Installing OpenClaw globally"
  npm install -g openclaw
}

write_env_template() {
  if [[ -f "$ENV_FILE" ]]; then
    echo "[OK] .env exists"
    return
  fi
  cat > "$ENV_FILE" <<'EOF'
# Required secrets/settings. Fill before first full run.
OPENCLAW_GATEWAY_TOKEN=
OPENAI_API_KEY=
# Optional
FIRECRAWL_API_KEY=
TAVILY_API_KEY=
EOF
  echo "[WARN] Created $ENV_FILE (fill secrets)"
}

sync_workspace_state() {
  echo "[INFO] Syncing workspace state bundle"
  rsync -a --delete "$ROOT_DIR/skills/" "$HOME/.openclaw/workspace/skills/" 2>/dev/null || true
  rsync -a "$ROOT_DIR/memory/" "$HOME/.openclaw/workspace/memory/" 2>/dev/null || true
}

run_healthcheck() {
  echo "[INFO] Running post-install checks"
  bash "$ROOT_DIR/scripts/healthcheck.sh"
}

install_docker
install_node
install_openclaw
write_env_template
sync_workspace_state
run_healthcheck

echo "[DONE] Bootstrap finished. Next: bash deploy/up.sh"
