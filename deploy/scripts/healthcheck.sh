#!/usr/bin/env bash
set -Eeuo pipefail

ok()   { echo "[OK] $*"; }
warn() { echo "[WARN] $*"; }
err()  { echo "[ERR] $*"; }

command -v docker >/dev/null 2>&1 && ok "docker: $(docker --version)" || err "docker missing"
command -v node >/dev/null 2>&1 && ok "node: $(node -v)" || err "node missing"
command -v npm >/dev/null 2>&1 && ok "npm: $(npm -v)" || err "npm missing"
command -v openclaw >/dev/null 2>&1 && ok "openclaw available" || err "openclaw missing"

if command -v systemctl >/dev/null 2>&1; then
  systemctl is-active --quiet docker && ok "docker service active" || warn "docker service not active"
fi

if command -v openclaw >/dev/null 2>&1; then
  openclaw gateway status >/tmp/openclaw-status.txt 2>&1 || true
  if grep -qi "running\|active\|ok" /tmp/openclaw-status.txt; then
    ok "gateway status reachable"
  else
    warn "gateway status not healthy yet"
  fi
fi

echo "[DONE] healthcheck finished"
