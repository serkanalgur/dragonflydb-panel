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
# The release workflow derives its tag from this field; non-semver would fail
# the build at merge time instead of here.
VERSIONS=$("$PYTHON" -c "import json;print(json.load(open('$PLUGIN/info.json'))['versions'])" 2>/dev/null)
if [[ "$VERSIONS" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  pass "versions is semver ($VERSIONS)"
else
  fail "versions must be semver like 1.0.0, got '$VERSIONS'"
fi
if grep -rqE "PLUGIN_VERSION[[:space:]]*=" "$PLUGIN/dragonfly"; then
  fail "version is duplicated outside info.json"
else
  pass "version declared in exactly one place"
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

step "index.html is a panel fragment, not a document"
UI="$PLUGIN/index.html"
# Strip comments first: this file's own header explains the rule and names the
# banned tags, which would otherwise trip the check on itself.
UI_BODY=$("$PYTHON" -c "
import re, sys
src = open(sys.argv[1]).read()
src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
sys.stdout.write(src)
" "$UI")
if printf '%s' "$UI_BODY" | grep -qiE '<!DOCTYPE|<html|<head|<body|<title'; then
  fail "index.html contains document tags; the panel injects a fragment"
else
  pass "no document tags"
fi
if grep -q 'class="bt-form' "$UI" && grep -q 'bt-w-con' "$UI" && grep -q 'plugin_body' "$UI"; then
  pass "panel layout classes present"
else
  fail "missing bt-form / bt-w-con / plugin_body scaffolding"
fi
if grep -qE 'action=a&name=|/plugin\?' "$UI"; then pass "uses the panel plugin endpoint"; else fail "no panel plugin endpoint in index.html"; fi
# jQuery and the panel's button classes come from the panel; do not re-add a lib.
if grep -qE '<script src="https?://' "$UI"; then fail "external script in index.html"; else pass "no external scripts"; fi

step "Backend convention"
MAIN="$PLUGIN/dragonflydb_main.py"
if [ -f "$MAIN" ]; then pass "<name>_main.py present"; else fail "dragonflydb_main.py missing"; fi
if grep -qE '^class dragonflydb_main\b' "$MAIN"; then pass "class dragonflydb_main"; else fail "class must be dragonflydb_main"; fi
if grep -qE 'sys\.path\.append\(.*class' "$MAIN" && grep -qE '^\s*import public' "$MAIN"; then
  pass "puts the panel helpers on sys.path and imports public"
else
  fail "must add the panel's class/ directory to sys.path and import public"
fi
if grep -qE 'os\.chdir\("/www/server/panel"\)' "$MAIN" \
   && ! grep -qE 'if os\.path\.isdir' "$MAIN"; then
  fail "the panel chdir must be guarded or the module cannot be imported"
else
  pass "panel directory chdir is guarded"
fi
if grep -qE 'public\.(toResult|returnMsg)\(' "$MAIN"; then fail "wrong return helper; use public.ReturnMsg"; else pass "uses public.ReturnMsg only"; fi
# action, s, name and a are reserved by the panel dispatcher.
if grep -oE '_arg\(get, "[a-z]+"' "$MAIN" | grep -qE '"(action|s|name|a)"'; then
  fail "a plugin argument collides with a reserved name (action, s, name, a)"
else
  pass "no reserved argument names"
fi

step "Endpoint wiring (dragonflydb_main.py vs index.html)"
for method in GetSettings SetSettings Install Start Stop Restart GetStatus GetLogs; do
  if grep -q "def $method" "$MAIN" && grep -q "'$method'" "$UI"; then
    pass "$method"
  else
    fail "$method declared in Python but not called by the UI (or vice versa)"
  fi
done

step "Community health files"
for f in LICENSE README.md CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md SUPPORT.md; do
  [ -s "$ROOT/$f" ] && pass "$f" || fail "$f missing or empty"
done
if grep -q "CODE_OF_CONDUCT.md" "$ROOT/README.md" && grep -q "SECURITY.md" "$ROOT/README.md" \
   && grep -q "CONTRIBUTING.md" "$ROOT/README.md"; then
  pass "README links the community files"
else
  fail "README must link CONTRIBUTING, CODE_OF_CONDUCT and SECURITY"
fi
# A broken relative link in the README is a dead end for a first-time visitor.
if command -v python3 >/dev/null && "$PYTHON" - <<'PY'
import os, re, sys
src = open("README.md").read()
bad = []
for target in re.findall(r"\]\(([^)#][^)]*)\)", src):
    if target.startswith(("http://", "https://", "mailto:")):
        continue
    if not os.path.exists(target):
        bad.append(target)
for t in bad:
    print("broken link:", t)
sys.exit(1 if bad else 0)
PY
then
  pass "README relative links resolve"
else
  fail "README contains links to files that do not exist"
fi

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
