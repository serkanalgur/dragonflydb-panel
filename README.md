# DragonFly Panel

**aaPanel plugin for [DragonflyDB](https://www.dragonflydb.io) — the Redis-compatible
in-memory store.** Install, configure, start, stop, and observe DragonflyDB from
inside the aaPanel (宝塔 / Baota) control panel, without touching the shell.

[![CI](https://github.com/serkanalgur/dragonflydb-panel/actions/workflows/ci.yml/badge.svg)](https://github.com/serkanalgur/dragonflydb-panel/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/release/serkanalgur/dragonflydb-panel.svg)](https://github.com/serkanalgur/dragonflydb-panel/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-%23serkanalgur-ea4aaa?logo=github-sponsors&logoColor=white)](https://github.com/sponsors/serkanalgur)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

## Overview

DragonflyDB is a drop-in replacement for Redis that is far more memory efficient
and scales to multi-threaded throughput. It speaks the Redis protocol, so
`redis-cli`, Laravel, WordPress, Django, and every existing client connect to it
without a code change.

This project is the aaPanel plugin around it. There is no official DragonflyDB
plugin in the aaPanel app store, so this is an independent community project.

### Why port 6380

aaPanel's own Redis manager owns port **6379**. This plugin defaults to **6380**
and refuses to configure 6379, so both can run side by side on one server.

## Requirements

- aaPanel installed at `/www/server/panel`
- Docker with Compose v2
- 4 GB RAM, 1 CPU core, Linux kernel 4.19 or newer (DragonflyDB upstream minimums)

## Installation

Download the latest `dragonflydb-panel-<version>.zip` from
[**Releases**](https://github.com/serkanalgur/dragonflydb-panel/releases/latest),
then in aaPanel go to **Plugins → Install a plugin → Local plugin**.

Or install from the command line:

```bash
unzip dragonflydb-panel-1.1.0.zip -d /www/server/panel/plugin/
bash /www/server/panel/plugin/dragonflydb/install.sh install
```

Then open the plugin, review the settings, and click **Install**.

> Enable **Developer Mode** in the panel if you are iterating on the plugin;
> without it, edits to `index.html` and the Python appear to do nothing.

## Usage

Everything the plugin's settings page does is available from the shell:

```bash
DF=/www/server/panel/plugin/dragonflydb

bash $DF/main.sh start        # docker compose up -d
bash $DF/main.sh status       # container state
bash $DF/main.sh logs 300     # tail container logs
bash $DF/main.sh stop
bash $DF/main.sh restart
bash $DF/main.sh uninstall    # removes containers, volumes and data
```

Verify the server is answering:

```bash
redis-cli -p 6380 ping                    # PONG
redis-cli -p 6380 set hello world          # OK
curl -s http://127.0.0.1:6380/info | head  # DragonflyDB also speaks HTTP
```

Point an application at it by changing only the port:

```ini
; WordPress wp-config.php
define('WP_REDIS_HOST', '127.0.0.1');
define('WP_REDIS_PORT', '6380');
```

## Requirements check

The settings page verifies the prerequisites before offering any action, so a
missing dependency is visible before it turns into a failed command:

- a labelled dot next to the **Service** controls reports whether Docker is
  usable, with the specific reason when it is not;
- the **Start**, **Stop**, **Restart** and **View logs** buttons are disabled
  until Docker and Compose v2 are present, and until the deployment files exist;
- the same checks run again on the server for every action, so the buttons are
  never the only thing standing between a user and a raw shell error.

## Configuration

Settings are written to `/opt/dragonflydb/` and rendered into a
`docker-compose.yml` plus a `dragonfly.yaml`.

| Setting | Default | Notes |
| --- | --- | --- |
| Port | `6380` | Must not be 6379 |
| Bind | `127.0.0.1` | Use `0.0.0.0` to accept remote connections |
| Password | *(none)* | Set to require `AUTH` |
| Max memory | `1gb` | e.g. `512mb`, `2gb` |
| Eviction policy | `noeviction` | Redis-compatible policy name |
| Snapshot every | `900` s | `0` disables periodic snapshots |
| Image tag | `v1.26.0` | Pinned; the plugin never uses `latest` |

Two deployment details are deliberate and should not be "cleaned up":

- **`network_mode: host`** — a bridge network adds per-request NAT traversal and
  erases the performance advantage. Upstream documents this explicitly.
- **`ulimits.memlock: -1`** — without it DragonflyDB fails to initialise.

## Migrating from Redis

DragonflyDB is protocol compatible, so a migration is a port change plus a data
transfer. `redis-cli --pipe` and replication-based transfer both work; see the
[upstream migration guide](https://www.dragonflydb.io/docs/category/migrating-to-dragonfly).

## Repository layout

```
dragonflydb-panel/     the deployable unit, installed to
                       /www/server/panel/plugin/dragonflydb/
├── info.json          panel metadata and version
├── install.sh         install / uninstall, invoked by the panel
├── index.html         the settings page (a panel fragment, not a document)
├── icon.png
├── dragonflydb_main.py  backend entry point the panel dispatches to
├── main.sh            CLI mirror of the settings page
└── dragonfly/
    ├── config.py      paths, defaults, validation, persistence
    ├── compose.py     renders docker-compose.yml and dragonfly.yaml
    ├── service.py     container lifecycle
    └── client.py      DragonflyDB HTTP client (standard library only)
scripts/               test gates, packaging, SSH deploy
tests/                 unit tests and a simulated panel entry point
```

The internal package is `dragonfly/`, not `class/` — `class` is a Python keyword
and cannot be imported.

## Development

```bash
./scripts/test.sh                  # gates + 25 unit tests, no network or docker
./scripts/package.sh               # build dist/dragonflydb-panel-<version>.zip
./scripts/deploy.sh user@host      # deploy straight to a panel over SSH
```

The gates encode the aaPanel and DragonflyDB contracts, and have already caught
four real defects: a package that shadowed a Python keyword, an eviction-policy
validator that rejected every hyphenated policy, a release workflow that could
not authenticate, and a document-shaped `index.html` that the panel cannot
render.

Read [AGENTS.md](AGENTS.md) before contributing. It documents the architecture,
the DRY and SOLID rules, and the commit and release conventions.

## Releases

Merging a pull request that bumps `versions` in
[`info.json`](dragonflydb-panel/info.json) publishes a GitHub Release with the
installable zip attached. There is no separate release step.

## Sponsor

DragonFly Panel is free and MIT licensed, and stays that way.

If it saves you time on a production server, you can
[become a sponsor on GitHub](https://github.com/sponsors/serkanalgur). Sponsorship
is what keeps the releases coming: testing against a real aaPanel instance and
tracking its plugin conventions over time is the expensive part of this project.

## Contributing

Pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first, and note that commits follow the
[Conventional Commits](https://www.conventionalcommits.org/) specification.

Security reports: see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). DragonflyDB itself is licensed separately by the DragonflyDB
authors; this repository is not affiliated with or endorsed by aaPanel or
DragonflyDB Ltd.
