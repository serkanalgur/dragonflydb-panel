# Support

## Before opening an issue

Most reports are answered by the manual already.

1. **Check the version.** DragonFly Panel tracks aaPanel's plugin conventions,
   which change between panel releases. Update both and retry.
2. **Enable Developer Mode** if you are testing changes, otherwise edits to
   `index.html` and the Python appear to have no effect.
3. **Read the panel log.** `/www/server/panel/logs/error.log` usually names the
   failure outright.

## Collecting a diagnostic bundle

```bash
DF=/www/server/panel/plugin/dragonflydb

bash $DF/main.sh status            # container state
docker logs --tail 200 dragonflydb
ls -l /opt/dragonflydb/            # settings.json should be 0600
cat /opt/dragonflydb/settings.json # redact the password before pasting
redis-cli -p 6380 ping
curl -s http://127.0.0.1:6380/info | head -40
```

Include the output of these in your issue, **with any password redacted**.

## Common problems

**The settings page will not open, or shows "Getting template" and bounces to
the home page.** The plugin is installed over an older copy whose `index.html`
is still a full HTML document. Reinstall from the latest release zip. If you
edited the file by hand, check it contains no `<!DOCTYPE>`, `<html>`, `<head>`,
`<body>` or `<title>` — the panel injects a fragment.

**Changes to the plugin appear to do nothing.** Developer Mode is off, or the
files were edited outside `/www/server/panel/plugin/dragonflydb/` and deployed
with `./scripts/deploy.sh user@host`.

**AttributeError after an upgrade**, for example
`module 'dragonfly.service' has no attribute 'environment'`. The panel is a
long-lived process and caches imported plugin modules, so an earlier installed
version can keep serving requests after its files have been replaced. The
plugin discards its own cached modules on import and this was fixed in 1.2.1.
Upgrade to 1.2.1 or newer; on an older version, restart the panel after
upgrading.

**DragonflyDB will not start.** Check `docker logs --tail 200 dragonflydb`. The
usual cause is a port collision; aaPanel's Redis manager owns 6379 and this
plugin defaults to 6380. Another cause is `ulimits.memlock` having been removed
from the generated `docker-compose.yml`.

**Connection refused from an application.** The default bind is `127.0.0.1`, so
only local processes can connect. Applications in a Docker container need the
service on the host network, and a `host.docker.internal` mapping or a shared
network.

**A snapshot did not appear where expected.** Snapshots are written to the
configured `dir`, `/opt/dragonflydb/data` by default, and the directory is
mounted into the container at `/data`.

**An earlier install is still running.** `bash $DF/main.sh uninstall` removes
the containers and volumes. Verify nothing is left with
`docker ps -a --filter name=dragonflydb`.

## Reporting a bug

Open an issue with the diagnostic bundle above, your aaPanel version, the plugin
version, and what you expected to happen.

## Questions

Use GitHub Discussions for usage questions and configuration. Bug reports and
feature requests belong in issues; security reports belong in
[SECURITY.md](SECURITY.md).

## Before reporting upstream

If the behaviour is in DragonflyDB itself rather than in this plugin, it belongs
at the [DragonflyDB project](https://github.com/dragonflydb/dragonfly). If it is
in the control panel, it belongs with the aaPanel maintainers. This repository
carries no issues for either.
