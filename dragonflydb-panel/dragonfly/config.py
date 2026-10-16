"""Single source of truth for every filesystem path and tunable default.

Nothing else in the plugin may hardcode a path or a port. If a value needs to
change in one place, it changes here and nowhere else.
"""

import os
import re

PLUGIN_NAME = "dragonflydb"
PLUGIN_TITLE = "DragonflyDB"
PLUGIN_AUTHOR = "serkanalgur"
PLUGIN_HOMEPAGE = "https://github.com/serkanalgur/dragonflydb-panel"
PLUGIN_PS = "Redis-compatible in-memory store (DragonflyDB)"

# The version lives in info.json (`versions`) and nowhere else. Do not add a
# PLUGIN_VERSION constant here; it will drift and releases will lie.

PANEL_DIR = "/www/server/panel"
PLUGIN_DIR = os.path.join(PANEL_DIR, "plugin", PLUGIN_NAME)
WORK_DIR = "/opt/dragonflydb"
COMPOSE_FILE = os.path.join(WORK_DIR, "docker-compose.yml")
CONFIG_FILE = os.path.join(WORK_DIR, "dragonfly.yaml")
LOG_FILE = os.path.join(WORK_DIR, "install.log")

IMAGE_REPOSITORY = "docker.dragonflydb.io/dragonflydb/dragonfly"
IMAGE_DEFAULT_TAG = "v1.26.0"
COMPOSE_PROJECT = "dragonflydb"

# Dragonfly must not collide with aaPanel's own Redis on 6379.
DEFAULT_PORT = 6380
DEFAULT_BIND = "127.0.0.1"
DEFAULT_SNAPSHOT_SECONDS = 900

# Explicit allow-list rather than a regex: a typo'd policy silently disables
# eviction, which is a data-loss-shaped failure, not a validation nicety.
MAXMEMORY_POLICIES = frozenset({
    "noeviction",
    "allkeys-lru",
    "allkeys-lfu",
    "allkeys-random",
    "volatile-lru",
    "volatile-lfu",
    "volatile-random",
    "volatile-ttl",
})

VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")


class ConfigError(ValueError):
    """Raised when user-supplied settings cannot be accepted."""


def validate(settings):
    """Return a normalised settings dict, or raise ConfigError.

    Validating once at the boundary keeps every downstream consumer free of
    defensive checks.
    """
    port = settings.get("port") or DEFAULT_PORT
    try:
        port = int(port)
    except (TypeError, ValueError):
        raise ConfigError("Port must be a number")

    if not 1024 <= port <= 65535:
        raise ConfigError("Port must be between 1024 and 65535")
    if port == 6379:
        raise ConfigError(
            "Port 6379 is reserved for aaPanel's Redis manager. "
            "Choose a different port."
        )

    bind = settings.get("bind") or DEFAULT_BIND
    if bind not in ("127.0.0.1", "0.0.0.0"):
        raise ConfigError("Bind address must be 127.0.0.1 or 0.0.0.0")

    normalised = {
        "port": port,
        "bind": bind,
        "password": settings.get("password") or "",
        "maxmemory": str(settings.get("maxmemory") or "1gb").strip(),
        "maxmemory_policy": settings.get("maxmemory_policy") or "noeviction",
        "dir": os.path.abspath(settings.get("dir") or os.path.join(WORK_DIR, "data")),
        "snapshot_seconds": int(settings.get("snapshot_seconds") or DEFAULT_SNAPSHOT_SECONDS),
        "log_level": settings.get("log_level") or "notice",
        "image_tag": (settings.get("image_tag") or IMAGE_DEFAULT_TAG).strip(),
    }

    if normalised["maxmemory_policy"] not in MAXMEMORY_POLICIES:
        raise ConfigError(
            "Unknown maxmemory policy; expected one of: %s"
            % ", ".join(sorted(MAXMEMORY_POLICIES))
        )
    if not 0 <= normalised["snapshot_seconds"] <= 86400:
        raise ConfigError("Snapshot interval must be between 0 and 86400 seconds")
    return normalised


SETTINGS_FILE = os.path.join(WORK_DIR, "settings.json")


def load():
    """Read persisted settings, falling back to defaults when absent."""
    import json

    try:
        with open(SETTINGS_FILE) as handle:
            stored = json.load(handle)
    except (IOError, OSError, ValueError):
        stored = {}
    return validate(stored)


def save(settings):
    """Validate then persist. Returns the normalised settings on success."""
    import json

    normalised = validate(settings)
    os.makedirs(WORK_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as handle:
        json.dump(normalised, handle, indent=2, sort_keys=True)
        os.chmod(SETTINGS_FILE, 0o600)  # may hold a password
    return normalised
