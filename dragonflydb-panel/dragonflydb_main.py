#!/usr/bin/python
# coding: utf-8
"""aaPanel backend for the DragonflyDB plugin.

The panel dispatches `/plugin?action=a&name=dragonflydb&s=<Method>` to the
class named after this plugin in a file named `<name>_main.py`. Those two
names are not a style choice: they are how the panel finds the entry point.

Every method receives the request arguments and returns `public.ReturnMsg`,
which yields the `{status, msg}` envelope the panel's own front end expects.
`msg` is the only channel back to the UI, so structured payloads are JSON
encoded into it and decoded by index.html.

Deliberately dumb: it validates input, delegates to a service module, and
shapes the reply. No business logic lives here.
"""

import json
import os
import sys

PANEL_DIR = "/www/server/panel"

# Enter the panel directory when we are running inside one, so the relative
# "class/" lookup below resolves to the panel's helpers. Other plugins call
# os.chdir unconditionally, which makes the module unimportable outside a panel;
# the guard keeps it importable for the test suite and for local runs.
if os.path.isdir(PANEL_DIR):
    os.chdir(PANEL_DIR)
sys.path.append(os.path.join(os.getcwd(), "class"))

# The panel's own helpers: ReturnMsg, ReadFile, WriteFile, ExecShell.
import public

# Import the plugin's internal package, which sits next to this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dragonfly import compose, config, service  # noqa: E402
from dragonfly.client import Client  # noqa: E402


def _ok(message=""):
    return public.ReturnMsg(True, message)


def _fail(message):
    return public.ReturnMsg(False, message)


def _data(payload):
    """Return a structured payload, JSON encoded into the `msg` channel."""
    return public.ReturnMsg(True, json.dumps(payload))


def _arg(get, key, default=""):
    """Read one request argument.

    `get` is a dict-like from the panel. Never name a plugin argument
    `action`, `s`, `name` or `a` — the panel reserves those and a collision
    raises.
    """
    try:
        value = get.get(key, default)
    except AttributeError:
        value = default
    return default if value in (None, "") else value


class dragonflydb_main(object):
    """The HTTP surface the panel UI talks to."""

    # ---- settings ---------------------------------------------------------

    def GetSettings(self, get):
        settings = config.load()
        settings["password"] = "********" if settings["password"] else ""
        return _data(settings)

    def SetSettings(self, get):
        candidate = {
            "port": _arg(get, "port"),
            "bind": _arg(get, "bind"),
            "password": _arg(get, "password"),
            "maxmemory": _arg(get, "maxmemory"),
            "maxmemory_policy": _arg(get, "maxmemory_policy"),
            "dir": _arg(get, "dir"),
            "snapshot_seconds": _arg(get, "snapshot_seconds"),
            "log_level": _arg(get, "log_level"),
            "image_tag": _arg(get, "image_tag"),
        }
        if candidate["password"] == "********":
            candidate["password"] = config.load()["password"]  # left unchanged

        try:
            saved = config.save(candidate)
        except config.ConfigError as error:
            return _fail(str(error))

        # Rendering is deterministic, so writing eagerly keeps the deployment
        # files in lockstep with the settings the user just accepted.
        compose.write(saved)
        return _ok("Settings saved")

    # ---- lifecycle --------------------------------------------------------

    def Install(self, get):
        blocked = self._require_docker()
        if blocked:
            return blocked

        if not os.path.exists(config.SETTINGS_FILE):
            return _fail("Save settings before installing")

        pull = service.pull()
        if not pull:
            return _fail("Pull failed:\n%s" % pull.message)

        start = service.start()
        if not start:
            return _fail(start.message)
        return _ok("Started")

    def Start(self, get):
        return self._action(service.start, "Started")

    def Stop(self, get):
        return self._action(service.stop, "Stopped")

    def Restart(self, get):
        return self._action(service.restart, "Restarted")

    # ---- environment ------------------------------------------------------

    def GetEnvironment(self, get):
        """What the settings page needs before offering any action.

        Called on load and after every action, so a server that loses Docker
        between clicks shows a disabled button set instead of a stack trace
        from a failed shell command.
        """
        return _data(service.environment())

    # ---- observability ----------------------------------------------------

    def GetStatus(self, get):
        """Health, version and memory counters in a single round trip."""
        settings = config.load()
        client = Client(settings["port"], settings["password"])
        if not client.ping():
            return _fail("DragonflyDB is not responding")
        return _data(client.stats())

    def GetLogs(self, get):
        try:
            lines = int(_arg(get, "lines", 200))
        except (TypeError, ValueError):
            lines = 200
        return _data({"log": service.logs(min(lines, 2000)).message})

    # ---- internals --------------------------------------------------------

    def _action(self, operation, success):
        blocked = self._require_docker()
        if blocked:
            return blocked
        if not service.is_installed():
            return _fail("Not installed")
        result = operation()
        if result:
            return _ok(success)
        return _fail(result.message)

    def _require_docker(self):
        """Refuse an action early, with a reason the user can act on.

        The UI already disables these buttons, but a disabled button is not
        an access control: the endpoint has to be safe on its own.
        """
        problem = service.prerequisite_message()
        if problem:
            return _fail(problem)
        return None


if __name__ == "__main__":
    print("This module is called by the aaPanel panel, not directly.")
