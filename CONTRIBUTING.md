# Contributing to DragonFly Panel

Thanks for taking the time. This document is the short version; [AGENTS.md](AGENTS.md)
holds the architecture and the reasoning.

By participating you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Getting set up

You do not need an aaPanel instance to work on this. The test suite and the
packager run anywhere:

```bash
git clone https://github.com/serkanalgur/dragonflydb-panel
cd dragonflydb-panel
./scripts/test.sh
```

Python 3.9 or newer. No third-party dependencies — deliberately, because the
plugin runs inside the panel's own interpreter.

To test against a real panel, deploy over SSH:

```bash
./scripts/deploy.sh user@your-server
```

Enable **Developer Mode** in the panel first, or your edits will appear to have
no effect.

## The workflow

1. Branch off `main`: `git switch -c feat/short-description`
2. Make one logical change
3. Run `./scripts/test.sh` — it must be green
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/)
5. Open a pull request against `main`

Do not commit directly to `main`. Do not add a `Co-Authored-By` trailer.

Commit types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`,
`chore`.

```
feat(ui): add memory gauge to status panel
fix(compose): keep host networking on compose v2.24
ci: run gates on Python 3.9 and 3.12
```

## Before you open a pull request

```bash
./scripts/test.sh     # syntax, hygiene, contract gates, unit tests
./scripts/package.sh  # the zip the release workflow will publish
```

If your change touches `dragonflydb_main.py` or `index.html`, say so in the pull
request. Those two are the seam between this plugin and the panel, and they are
the places a mistake reaches the user directly.

## The gates, and why they exist

`scripts/test.sh` encodes contracts that are easy to violate by accident and
expensive to discover on a live server. Each has already caught a real defect:

| Gate | What it protects |
| --- | --- |
| `index.html` must not contain document tags | The panel injects a fragment; a full document breaks the settings page |
| Layout scaffold must be present | `bt-form` / `bt-w-con` / `plugin_body` are what the panel's CSS targets |
| No external `<script src>` | The panel supplies jQuery and its own stylesheets |
| Backend must be `<name>_main.py` / `class <name>_main` | The panel's dispatcher finds the entry point by those exact names |
| Replies must use `public.ReturnMsg` | That is the envelope the panel's front end parses |
| No argument named `action`, `s`, `name`, `a` | The panel reserves these for dispatch |
| The panel directory `chdir` must be guarded | An unguarded `chdir` makes the module unimportable outside a panel |
| Standard library only in `dragonfly/` | A dependency breaks panel upgrades |
| No hardcoded paths outside `config.py` | DRY: one place to change a path or a default |
| `versions` must be semver | The release workflow derives the git tag from it |
| Endpoints match between Python and the UI | The names are duplicated across the two languages and drift silently |

If a gate blocks something you believe is correct, change the gate in its own
commit and explain why in the description. Do not delete a gate to make a pull
request pass.

## Adding a setting

A new setting is incomplete until it exists in all four places:

1. `config.validate` — normalisation and validation
2. `compose` — how it is rendered
3. `index.html` — the form control
4. `AGENTS.md` — the configuration table, if it is user-facing

## Versioning and releases

The version lives in exactly one place: `versions` in `info.json`, as semver.
There is deliberately no version constant in the Python.

Merging a pull request that bumps that field publishes a GitHub Release with the
zip attached. So a pull request that changes plugin behaviour must bump the
version in the same commit. A documentation-only change need not.

## Reporting bugs

Open an issue with:

- your aaPanel version and the plugin version
- the output of `bash /www/server/panel/plugin/dragonflydb/main.sh status`
- the relevant panel log from `/www/server/panel/logs/error.log`
- what you expected and what happened instead

## Pull request descriptions

State what changed, why, how you verified it, and the risk. A pull request that
only says "fixes stuff" will be sent back.

## Security

Do not open a public issue for a security problem. See
[SECURITY.md](SECURITY.md).
