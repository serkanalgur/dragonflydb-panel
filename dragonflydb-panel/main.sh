#!/bin/bash
# CLI entry point:  bash main.sh <command>
# Mirrors the plugin's HTTP surface so the same operations are scriptable.

set -u
WORK_DIR=/opt/dragonflydb
COMPOSE_PROJECT=dragonflydb
PLUGIN_DIR=$(cd "$(dirname "$0")" && pwd)

compose() {
  docker compose -p "$COMPOSE_PROJECT" -f "$WORK_DIR/docker-compose.yml" "$@"
}

require_installed() {
  if [ ! -f "$WORK_DIR/docker-compose.yml" ]; then
    echo "Not installed. Open the plugin in the panel and click Install." >&2
    exit 1
  fi
}

status() {
  require_installed
  compose ps
  echo
  compose exec -T dragonfly sh -c '/opt/dragonflydb/dragonfly --port 6380 --ping' 2>/dev/null \
    || echo "Container reachable via: redis-cli -p $(python3 -c "import json;print(json.load(open('$WORK_DIR/settings.json'))['port'])") ping"
}

case "${1:-}" in
  install)   bash "$PLUGIN_DIR/install.sh" install ;;
  uninstall) bash "$PLUGIN_DIR/install.sh" uninstall ;;
  start)     require_installed; compose up -d ;;
  stop)      require_installed; compose stop ;;
  restart)   require_installed; compose restart ;;
  status)    status ;;
  logs)      require_installed; compose logs --tail "${2:-200}" ;;
  *)         echo 'Usage: main.sh install|uninstall|start|stop|restart|status|logs' ; exit 1 ;;
esac
