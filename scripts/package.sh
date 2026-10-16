#!/usr/bin/env bash
# Build the panel-installable zip.
#
#   ./scripts/package.sh [output-dir]     # default: dist
#   ./scripts/package.sh /tmp/out
#
# The archive's top-level directory must equal info.json's `name`, otherwise
# the panel rejects the local install. Only the plugin ships: no tests, scripts,
# or repository metadata.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-$ROOT/dist}
PYTHON=${PYTHON:-python3}

read -r NAME VERSION <<EOF
$($PYTHON -c "
import json
info = json.load(open('$ROOT/dragonflydb-panel/info.json'))
print(info['name'], info['versions'])
")
EOF

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "info.json versions must be semver like 1.0.0, got '$VERSION'" >&2
  exit 1
fi

ASSET="$NAME-panel-$VERSION.zip"
rm -rf "$OUT/$NAME"
mkdir -p "$OUT/$NAME"

for f in info.json install.sh main.sh index.html icon.png public.py; do
  cp "$ROOT/dragonflydb-panel/$f" "$OUT/$NAME/"
done
cp -r "$ROOT/dragonflydb-panel/dragonfly" "$OUT/$NAME/"
find "$OUT" -name '__pycache__' -type d -prune -exec rm -rf {} +

# aaPanel invokes the scripts directly; lose the exec bit and install fails.
chmod +x "$OUT/$NAME"/*.sh

rm -f "$OUT/$ASSET"
(cd "$OUT" && zip -r -9 "$ASSET" "$NAME" >/dev/null)

# The panel locates the plugin at the archive's first directory.
unzip -Z1 "$OUT/$ASSET" | grep -q "^$NAME/info.json$" || {
  echo "archive must contain $NAME/info.json at depth 1" >&2
  exit 1
}

echo "$OUT/$ASSET"
