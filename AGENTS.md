# AGENTS.md

Operating contract for agents and humans working on this repository. Read this
before touching any file.

## What this repository is

An [aaPanel](https://www.aapanel.com) plugin that installs and manages
[DragonflyDB](https://www.dragonflydb.io), a Redis-compatible in-memory store.

Two structures are simultaneously in force. A change must satisfy both.

### Constraint 1 — the aaPanel plugin structure

Reference: <https://www.aapanel.com/pkg/aaPanel_Linux_Panel_Plug-in_development_documentation_v1.1.pdf>

The directory named in `info.json` (`checks`) is the deployable unit and must be
self-contained. It installs to `/www/server/panel/plugin/dragonflydb/`.

| Path | Role | Required |
| --- | --- | --- |
| `info.json` | Panel metadata: `title`, `name`, `ps`, `versions`, `checks`, `author`, `home` | yes |
| `install.sh` | Invoked as `install.sh install` and `install.sh uninstall` | yes |
| `index.html` | The plugin's UI, injected into the panel's layout | yes |
| `dragonflydb_main.py` | Class `dragonflydb_main`; each method is an endpoint at `/plugin?action=a&name=dragonflydb&s=<Method>` | yes |
| `main.sh` | CLI mirror of the HTTP surface (`bash main.sh status`) | no |
| `icon.png` | App-store icon, 150x150-ish, shown in the plugin list | yes |
| `dragonfly/` | Internal modules, importable via the plugin's own `sys.path` entry | no |

The internal package is named `dragonfly`, **not** `class`. Some older aaPanel
guides use a `class/` directory, but `class` is a Python keyword and
`from class import config` is a syntax error. Do not rename it back.

Hard rules:

- **`index.html` must be a fragment.** No `<!DOCTYPE>`, `<html>`, `<head>`,
  `<body>` or `<title>`. The panel injects the file into its own layout inside a
  layui modal layer; a full document nests a `<body>` and the template fails to
  render, which the panel surfaces as a "Getting template" popup followed by a
  redirect to the home page. Wrap content in
  `bt-form > bt-w-main > bt-w-menu + bt-w-con.pd15 > .plugin_body` and rely on
  the panel's stylesheets and jQuery.
- **Never import outside the standard library and the panel's own modules.** The
  plugin runs inside the panel's interpreter. A dependency added here breaks
  panel upgrades. `scripts/test.sh` audits imports with an AST pass.
- **The backend file and class names are not free choices.** The panel looks for
  `<name>_main.py` containing `class <name>_main`. The UI posts to
  `/plugin?action=a&name=<name>&s=<Method>`.
- **Reply with `public.ReturnMsg(status, msg)`,** which yields
  `{"status": bool, "msg": str}`. There is no `data` channel, so structured
  payloads are JSON encoded into `msg` and decoded in `index.html`.
- **Never name an argument `action`, `s`, `name` or `a`.** The panel reserves
  them for dispatch and a collision raises.
- **Prefix every global in `index.html`** (`dfdNotify`, `dfdCall`, …). The file
  is injected into the panel's own page, where an unprefixed `status` or `call`
  collides with panel code.
- **`install.sh` must handle both verbs** and `Uninstall` must leave no
  containers, volumes, or files behind.
- **Never block an HTTP request.** Anything slow belongs in `service.py` with a
  bounded timeout, or in a backgrounded shell command.
- **Keep the plugin self-contained.** No imports from the repository root, no
  `../` paths, no absolute references to this checkout.
- **`info.json` `checks` must match the deployed directory name exactly.**
- **Enable Developer Mode in the panel** while iterating, or edits to
  `index.html` and the Python will appear to do nothing.

### Constraint 2 — the DragonflyDB deployment contract

Reference: <https://www.dragonflydb.io/docs/getting-started/docker-compose>
and <https://www.dragonflydb.io/docs/managing-dragonfly/flags>

Hard rules:

- **Image is `docker.dragonflydb.io/dragonflydb/dragonfly`.** Pin the tag; never
  use `latest`.
- **`ulimits.memlock` must be `-1/-1`.** Omitting it produces init failures.
- **`network_mode: host`, not an overlay bridge.** Overlay adds per-request NAT
  traversal and erases the performance advantage. This is called out in
  upstream docs; do not "fix" it to port mapping.
- **Never default to port 6379.** aaPanel's own Redis manager owns it.
  `DEFAULT_PORT` is 6380 and `config.validate` rejects 6379.
- **Persistence is mandatory.** Mount `dir` and bind the `dragonfly.yaml` so
  snapshots survive a container replacement.
- **Uninstall uses `docker compose down -v`.** Without `-v` volumes leak.

## Architecture

```
dragonflydb_main.py   HTTP controller. Validates, delegates, wraps. No logic.
  └── dragonfly/
        config.py    Single source of truth: paths, ports, defaults,
        │            validation, settings persistence.
        compose.py   Pure rendering of docker-compose.yml + dragonfly.yaml.
        service.py   Lifecycle: pull/start/stop/restart/logs/destroy.
        client.py    Dragonfly HTTP client (stdlib urllib).
```

Dependency direction is strictly one way: `dragonflydb_main.py → service.py →
compose.py → config.py`. Nothing imports `dragonflydb_main.py`, and no two
service modules import each other. `client.py` is a leaf.

## Principles

**DRY.** Every path, port, image name, and default lives in `config.py`. If a
literal appears twice, that is a bug — hoist it. `_action` in
`dragonflydb_main.py` exists so start/stop/restart share one implementation
instead of three.

**SOLID, applied concretely:**
- *Single responsibility* — `config` knows settings, `compose` knows file
  contents, `service` knows process lifecycle, `client` knows the wire
  protocol. A module gains no second reason to change.
- *Open/closed* — new lifecycle operations are a new function in `service.py`
  plus one controller method. No existing branch is edited.
- *Liskov substitution* — `ComposeResult` is falsy on failure and carries the
  output; callers branch on it rather than parsing strings.
- *Interface segregation* — consumers depend on the narrow function they call,
  never on the module wholesale.
- *Dependency inversion* — `dragonflydb_main.py` depends on `Client` and `ComposeResult`
  interfaces, not on concrete HTTP or subprocess details.

**YAGNI.** No plugin marketplace, no multi-node support, no ACL editor, no
metrics exporter. A feature that no user has asked for does not land.

## Quality gates

Before committing:

```bash
./scripts/test.sh    # syntax, AST import audit, hygiene, endpoint wiring, unit tests
```

No network, no docker, no panel. The gates catch the classes of mistake that are
expensive to find in production: a `class/` rename, a third-party import, a
setting added to Python but not to the form, an endpoint the UI calls that no
longer exists. They have already caught all four.

## Conventional commits

Format: `<type>(<scope>): <subject>`, imperative mood, no trailing period,
subject ≤ 72 characters.

| Type | Use for |
| --- | --- |
| `feat` | New user-visible capability |
| `fix` | Bug fix |
| `refactor` | Behaviour-preserving internal change |
| `perf` | Measurable performance change |
| `docs` | Documentation only |
| `test` | Tests only |
| `build` | Packaging, deployment scripts, CI |
| `ci` | Automation config |
| `chore` | Housekeeping with no source impact |

Scopes: `plugin` (dragonflydb_main.py), `config`, `compose`, `service`, `client`, `ui`
(index.html), `shell` (install.sh / main.sh), `docs`, `ci`, `release`.

Examples that are correct:

```
feat(ui): add memory gauge to status panel
fix(compose): keep host networking on compose v2.24
refactor(plugin): extract _action to remove triplicated lifecycle code
ci: run gates on Python 3.9 and 3.12
docs: record the 6379 port constraint
```

Rules:
- One logical change per commit.
- **No `Co-Authored-By` trailer.** No AI attribution of any kind.
- Reference issues with `(#123)` in the body, never in the subject.
- A PR that changes plugin behaviour bumps `info.json` `versions` in the same
  commit.

## Branching and PR flow

1. **Branch off `main`.** Never commit directly to `main`.
   ```bash
   git switch main && git pull --ff-only
   git switch -c feat/ui-log-viewer     # <type>/<scope>-<short-description>
   ```
   The only exception is the repository's initial commit, which seeds `main`.
2. **Commit as you go**, in conventional-commit form. Small commits, each
   independently revertible.
3. **Run the gates locally** before pushing. `./scripts/test.sh` must be green.
4. **Push the branch** and open a PR against `main`:
   ```bash
   git push -u origin <branch>
   gh pr create --title "feat(ui): add log viewer" --body "$(cat <<'EOF'
   ## What
   ...

   ## Why
   ...

   ## Verification
   - [ ] ./scripts/test.sh passes
   - [ ] Manual smoke test on a panel instance

   ## Risk
   ...
   EOF
   )"
   ```
5. **PR description** states what, why, how it was verified, and the risk. A PR
   that only says "fixes stuff" will be sent back.
6. **Wait for review.** Do not merge your own PR. Squash-merge is the default so
   `main` history stays linear and conventional.
7. **After merge**, delete the branch locally and remotely:
   ```bash
   git switch main && git pull --ff-only
   git branch -d <branch> && git push origin --delete <branch>
   ```

## Versioning and releases

**The version lives in exactly one place:** `dragonflydb-panel/info.json` →
`versions`, as semver (`1.0.0`). There is no version constant in the Python and
a gate enforces that. The release workflow derives the git tag from this field.

On every push to `main`, `.github/workflows/release.yml`:

1. runs `./scripts/test.sh` and aborts on failure;
2. reads `versions` and compares it with the latest published tag;
3. skips silently if `v<versions>` already exists;
4. otherwise runs `./scripts/package.sh`, which builds
   `dist/<name>-panel-<version>.zip` containing a single top-level directory
   named exactly as `info.json` `name` — the panel rejects anything else;
5. tags `v<version>`, pushes the tag, and creates a release with the zip and
   install instructions.

So the human process is just: **bump `versions` in `info.json` in the same PR
as the change.** Merging that PR publishes the release. Nothing else is manual.

`./scripts/package.sh [output-dir]` builds the identical zip locally, so you can
test an install before merging. `workflow_dispatch` with `force: true`
republishes an existing version.

CI (`.github/workflows/ci.yml`) runs the gates on Python 3.9 and 3.12 for every
PR — aaPanel 7.x ships 3.12, older panels 3.9 — and uploads the zip as an
artifact for manual install testing.

## Agent-specific rules

- Read `AGENTS.md` and `README.md` fully before the first edit.
- Never edit `dragonflydb_main.py` and a service module in one commit unless the change
  is a single atomic fix; separate refactors from behaviour changes.
- Never add a third-party dependency to `dragonfly/`. If upstream needs a
  library we do not have, use the HTTP API instead.
- Before adding a setting, add it to `config.validate`, to `compose`, and to the
  form in `index.html`, or it is incomplete.
- After any change to `dragonflydb_main.py` or `index.html`, run `./scripts/test.sh`; the
  endpoint-wiring gate compares the two sides, which is the only defence against
  the duplicated endpoint names drifting apart.
- Prefer deleting code to adding it.
