"""aaPanel entry point: /plugin/dragonflydb/public.<method>

This module is deliberately dumb. It validates input, delegates to a service
module, and shapes the reply into the panel's JSON envelope. No business logic
lives here.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dragonfly import compose, config, service  # noqa: E402
from dragonfly.client import Client  # noqa: E402

# The panel exposes toResult() from /www/server/panel/class/public.py.
try:
    import public as bt_public
except ImportError:  # pragma: no cover - only when run outside the panel
    bt_public = None


def _ok(data=None, message=""):
    payload = {"status": True, "msg": message}
    if data:
        payload["data"] = data
    return payload


def _fail(message):
    return {"status": False, "msg": message}


class public(object):
    """The HTTP surface the panel UI talks to."""

    # ---- settings ---------------------------------------------------------

    def get_settings(self, get):
        settings = config.load()
        settings["password"] = "********" if settings["password"] else ""
        return self._respond(_ok(settings))

    def set_settings(self, get):
        candidate = {
            "port": get.get("port"),
            "bind": get.get("bind"),
            "password": get.get("password"),
            "maxmemory": get.get("maxmemory"),
            "maxmemory_policy": get.get("maxmemory_policy"),
            "dir": get.get("dir"),
            "snapshot_seconds": get.get("snapshot_seconds"),
            "log_level": get.get("log_level"),
            "image_tag": get.get("image_tag"),
        }
        if get.get("password") == "********":
            candidate["password"] = config.load()["password"]  # left unchanged

        try:
            saved = config.save(candidate)
        except config.ConfigError as error:
            return self._respond(_fail(str(error)))

        # Rendering is deterministic, so writing eagerly keeps the deployment
        # files in lockstep with the settings the user just accepted.
        compose.write(saved)
        return self._respond(_ok(saved, "Settings saved"))

    # ---- lifecycle --------------------------------------------------------

    def install(self, get):
        if not os.path.exists(config.SETTINGS_FILE):
            return self._respond(_fail("Save settings before installing"))

        pull = service.pull()
        if not pull:
            return self._respond(_fail("Pull failed:\n%s" % pull.message))

        start = service.start()
        if not start:
            return self._respond(_fail(start.message))
        return self._respond(_ok(None, "Started"))

    def start(self, get):
        return self._action(service.start, "Started")

    def stop(self, get):
        return self._action(service.stop, "Stopped")

    def restart(self, get):
        return self._action(service.restart, "Restarted")

    # ---- observability ----------------------------------------------------

    def status(self, get):
        """Health, version and memory counters in a single round trip."""
        settings = config.load()
        client = Client(settings["port"], settings["password"])
        if not client.ping():
            return self._respond(_fail("DragonflyDB is not responding"))
        return self._respond(_ok(client.stats()))

    def logs(self, get):
        try:
            lines = int(get.get("lines", 200))
        except (TypeError, ValueError):
            lines = 200
        return self._respond(_ok({"log": service.logs(min(lines, 2000)).message}))

    # ---- internals --------------------------------------------------------

    def _action(self, operation, success):
        if not service.is_installed():
            return self._respond(_fail("Not installed"))
        result = operation()
        return self._respond(
            _ok(None, success) if result else _fail(result.message)
        )

    def _respond(self, payload):
        if bt_public is None:
            return payload
        return bt_public.toResult(payload)
