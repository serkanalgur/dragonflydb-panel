#!/usr/bin/env bash
# Quality gates. No network, no docker, no panel required.
set -uo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PLUGIN="$ROOT/dragonflydb-panel"
PYTHON=${PYTHON:-python3}
FAILURES=0
PANEL_PLUGIN_ROOT=/www/server/panel/plugin

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mFAIL\033[0m %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
pass() { printf '\033[32mok\033[0m   %s\n' "$1"; }

step "Python syntax"
while IFS= read -r py; do
  if "$PYTHON" -m py_compile "$py" 2>/dev/null; then pass "${py#$ROOT/}"; else fail "${py#$ROOT/}"; fi
done < <(find "$PLUGIN" "$ROOT/tests" -name '*.py' -not -path '*/__pycache__/*')

step "Shell syntax"
while IFS= read -r sh; do
  if bash -n "$sh" 2>/dev/null; then pass "${sh#$ROOT/}"; else fail "${sh#$ROOT/}"; fi
done < <(find "$ROOT" -name '*.sh' -not -path '*/.git/*')

step "JSON validity"
for f in "$PLUGIN/info.json"; do
  if "$PYTHON" -c "import json,sys; json.load(open(sys.argv[1]))" "$f" 2>/dev/null; then
    pass "${f#$ROOT/}"
  else
    fail "${f#$ROOT/}"
  fi
done

step "info.json consistency"
NAME=$("$PYTHON" -c "import json;print(json.load(open('$PLUGIN/info.json'))['name'])" 2>/dev/null)
CHECKS=$("$PYTHON" -c "import json;print(json.load(open('$PLUGIN/info.json'))['checks'])" 2>/dev/null)
# The real invariant: the panel must find the plugin at checks, and that path's
# last segment must equal name. The repo folder name is free to differ.
if [ "$(basename "$CHECKS")" = "$NAME" ]; then
  pass "checks path ends in the declared name '$NAME'"
else
  fail "checks '$CHECKS' does not end in name '$NAME'"
fi
if [ "$CHECKS" = "$PANEL_PLUGIN_ROOT/$NAME" ]; then
  pass "checks path is under $PANEL_PLUGIN_ROOT"
else
  fail "checks path '$CHECKS' is not under $PANEL_PLUGIN_ROOT"
fi

step "Hygiene rules"
# AST-based import audit: names that are not in the standard library.
if "$PYTHON" - "$PLUGIN" <<'PY'
import ast, os, sys, pathlib
allowed = {
    "os", "re", "json", "sys", "subprocess", "base64", "urllib",
    "public",  # the panel's own toResult helper
}
root = pathlib.Path(sys.argv[1]) / "dragonfly"
bad = []
for path in sorted(root.glob("*.py")):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in allowed and top != "dragonfly":
                    bad.append("%s:%d imports %s" % (path.name, node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top and top not in allowed and top != "dragonfly":
                bad.append("%s:%d imports from %s" % (path.name, node.lineno, node.module))
for line in bad:
    print(line)
sys.exit(1 if bad else 0)
PY
then
  pass "dragonfly/ is standard library only"
else
  fail "non-stdlib import found in dragonfly/"
fi
if grep -rn "print(" "$PLUGIN/dragonfly"/*.py >/dev/null; then fail "print() in dragonfly/"; else pass "no print() in dragonfly/"; fi
if grep -rn "'/opt/dragonflydb'\|\"/opt/dragonflydb\"" "$PLUGIN" --include='*.py' \
   | grep -v 'config.py' >/dev/null; then
  fail "hardcoded WORK_DIR outside config.py"
else
  pass "no hardcoded paths outside config.py"
fi
if grep -rn '6379' "$PLUGIN/dragonfly/config.py" >/dev/null; then pass "6379 guard present in config.py"; else fail "6379 guard missing"; fi
if grep -rn 'network_mode: host' "$PLUGIN/dragonfly/compose.py" >/dev/null; then pass "host networking retained"; else fail "host networking missing"; fi
if grep -rn 'memlock' "$PLUGIN/dragonfly/compose.py" >/dev/null; then pass "memlock limit retained"; else fail "memlock limit missing"; fi
if grep -rn 'down", "-v' "$PLUGIN/dragonfly/service.py" >/dev/null; then pass "uninstall removes volumes"; else fail "uninstall does not remove volumes"; fi

step "Endpoint wiring (public.py vs index.html)"
for method in get_settings set_settings install start stop restart status logs; do
  if grep -q "def $method" "$PLUGIN/public.py" && grep -q "'$method'" "$PLUGIN/index.html"; then
    pass "$method"
  else
    fail "$method declared in Python but not called by the UI (or vice versa)"
  fi
done

step "Unit tests"
if "$PYTHON" -m unittest discover -s "$ROOT/tests" -v 2>&1 | tail -20; then
  pass "unittest"
else
  fail "unittest"
fi

printf '\n'
if [ "$FAILURES" -eq 0 ]; then
  printf '\033[32mAll gates passed.\033[0m\n'
else
  printf '\033[31m%s gate(s) failed.\033[0m\n' "$FAILURES"
fi
exit "$FAILURES"
