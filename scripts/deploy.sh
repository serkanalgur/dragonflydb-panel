#!/usr/bin/env bash
# Deploy the plugin onto a panel host over SSH, then install it.
#
#   ./scripts/deploy.sh user@host
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
TARGET=${1:?usage: deploy.sh user@host}

echo "==> Checking local gates"
"$ROOT/scripts/test.sh" >/dev/null || { echo "local gates failed; aborting"; exit 1; }

echo "==> Running install.sh uninstall (best effort)"
ssh -o BatchMode=yes "$TARGET" 'bash -s' uninstall < "$ROOT/dragonflydb-panel/install.sh" || true

echo "==> Syncing plugin to /www/server/panel/plugin/dragonflydb"
ssh -o BatchMode=yes "$TARGET" 'mkdir -p /www/server/panel/plugin/dragonflydb'
scp -r "$ROOT/dragonflydb-panel/." "$TARGET:/www/server/panel/plugin/dragonflydb/"
ssh -o BatchMode=yes "$TARGET" \
  'chmod +x /www/server/panel/plugin/dragonflydb/*.sh && bash /www/server/panel/plugin/dragonflydb/install.sh install'

echo "==> Done. Open the DragonflyDB plugin in the panel."
