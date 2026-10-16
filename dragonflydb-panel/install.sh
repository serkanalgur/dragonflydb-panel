#!/bin/bash
# aaPanel install / uninstall entry point.
# The panel invokes: install.sh install | install.sh uninstall

set -u
WORK_DIR=/opt/dragonflydb
COMPOSE_PROJECT=dragonflydb

log() { echo "[dragonflydb] $1"; }

seed_config() {
  mkdir -p "$WORK_DIR"
  if [ ! -f "$WORK_DIR/settings.json" ]; then
    cat > "$WORK_DIR/settings.json" <<'EOF'
{
  "bind": "127.0.0.1",
  "dir": "/opt/dragonflydb/data",
  "image_tag": "v1.26.0",
  "log_level": "notice",
  "maxmemory": "1gb",
  "maxmemory_policy": "noeviction",
  "password": "",
  "port": 6380,
  "snapshot_seconds": 900
}
EOF
    chmod 600 "$WORK_DIR/settings.json"
  fi
}

Install() {
  log 'checking prerequisites'
  if ! command -v docker >/dev/null 2>&1; then
    log 'docker is required but was not found'
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    log 'docker compose v2 is required'
    exit 1
  fi

  seed_config
  log 'defaults written to /opt/dragonflydb/settings.json'
  log 'open the plugin to review settings, then click Install'
}

Uninstall() {
  log 'removing containers and volumes'
  if [ -f "$WORK_DIR/docker-compose.yml" ]; then
    docker compose -p "$COMPOSE_PROJECT" -f "$WORK_DIR/docker-compose.yml" \
      down -v --remove-orphans >>"$WORK_DIR/uninstall.log" 2>&1 || true
  fi
  log 'deleting /opt/dragonflydb'
  rm -rf "$WORK_DIR"
}

case "${1:-}" in
  install)   Install ;;
  uninstall) Uninstall ;;
  *)         echo 'Usage: install.sh install|uninstall'; exit 1 ;;
esac
