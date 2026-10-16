"""DragonflyDB client speaking its native HTTP protocol.

Standard library only on purpose: the plugin must run inside the panel's own
interpreter without adding dependencies.
"""

import base64
import json
import urllib.error
import urllib.request


class DragonflyError(Exception):
    """Raised when Dragonfly cannot be reached or returns an error."""


class Client(object):
    def __init__(self, port, password=""):
        self._base = "http://127.0.0.1:%d" % port
        self._auth = (
            "Basic " + base64.b64encode((":".join((password, ""))).encode()).decode()
            if password else None
        )

    def _get(self, path):
        request = urllib.request.Request(self._base + path)
        if self._auth:
            request.add_header("Authorization", self._auth)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise DragonflyError("Cannot reach DragonflyDB: %s" % error.reason)
        except ValueError:
            raise DragonflyError("DragonflyDB returned a malformed response")

    def ping(self):
        """True when the server answers PING. Used as the health check."""
        try:
            return self._get("/ping") == "PONG"
        except DragonflyError:
            return False

    def stats(self):
        """Memory and keyspace counters, flattened for the UI."""
        raw = self._get("/info")
        fields = dict(
            line.split(":", 1)
            for line in raw.splitlines()
            if ":" in line
        )
        return {
            "version": fields.get("dragonfly_version", "unknown").strip(),
            "uptime_seconds": fields.get("uptime_in_seconds", "0").strip(),
            "used_memory": fields.get("used_memory", "0").strip(),
            "total_memory": fields.get("maxmemory", "0").strip(),
            "keys": fields.get("db_keys", "0").strip(),
            "clients": fields.get("connected_clients", "0").strip(),
        }
