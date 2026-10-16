# dragonflydb-panel

An [aaPanel](https://www.aapanel.com) plugin that installs and manages
[DragonflyDB](https://www.dragonflydb.io), a Redis-compatible in-memory store.

> [!NOTE]
> This is an independent community plugin. It is not affiliated with, endorsed
> by, or published through the aaPanel app store.

## Why

- DragonflyDB is a drop-in Redis replacement with far better memory efficiency
  and multi-threaded throughput.
- aaPanel's Redis manager owns port 6379, so this plugin runs on **6380** by
  default and the two coexist.

## Layout

```
dragonflydb-panel/     <- the deployable unit, deploys to /www/server/panel/plugin/dragonflydb
├── info.json          <- panel metadata
├── install.sh         <- install / uninstall, run by the panel
├── index.html         <- the UI
├── icon.png           <- app-store icon
├── public.py          <- HTTP controller
├── main.sh            <- CLI mirror: bash main.sh status
└── dragonfly/         <- internal modules (not `class`: that is a Python keyword)
    ├── config.py      <- paths, defaults, validation, persistence
    ├── compose.py     <- renders docker-compose.yml + dragonfly.yaml
    ├── service.py     <- container lifecycle
    └── client.py      <- Dragonfly HTTP client (stdlib only)
scripts/test.sh        <- quality gates
scripts/deploy.sh      <- deploy over SSH
tests/                 <- unit tests
```

## Requirements

- aaPanel installed at `/www/server/panel`
- Docker with Compose v2
- 4 GB RAM, 1 CPU core, kernel 4.19+ (DragonflyDB upstream minimums)

## Install

From the panel: **Plugins → Install a plugin → local plugin**, upload
`dragonflydb-panel.zip`. Or by hand:

```bash
unzip dragonflydb-panel.zip -d /www/server/panel/plugin/
bash /www/server/panel/plugin/dragonflydb/install.sh install
```

Then open the plugin, review the settings, and click **Install**.

## Use

Panel UI, or CLI:

```bash
bash /www/server/panel/plugin/dragonflydb/main.sh start
bash /www/server/panel/plugin/dragonflydb/main.sh status
bash /www/server/panel/plugin/dragonflydb/main.sh logs 300
redis-cli -p 6380 ping        # PONG
curl -s localhost:6380/info   # Dragonfly also speaks HTTP
```

## Development

```bash
./scripts/test.sh                        # gates: syntax, hygiene, unit tests
./scripts/deploy.sh user@host            # deploy to a panel over SSH
```

Read [AGENTS.md](AGENTS.md) before contributing. It documents the architecture,
the DRY/SOLID rules, the quality gates, and the commit and PR conventions.

## License

MIT
