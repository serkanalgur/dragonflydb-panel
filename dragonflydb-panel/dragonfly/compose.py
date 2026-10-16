"""Renders the docker-compose.yml and dragonfly.yaml that define the deployment.

Rendering is a pure function of validated settings: given the same settings you
always get byte-identical files, which makes diffing and testing trivial.
"""

import os

from . import config


def _yaml_config(settings):
    lines = [
        "bind:",
        "  - %s:%d" % (settings["bind"], settings["port"]),
        "",
        "maxmemory: %s" % settings["maxmemory"],
        "maxmemory_policy: %s" % settings["maxmemory_policy"],
        "",
        "dir: %s" % settings["dir"],
        "dbfilename: dump",
        "",
        "snapshot_expiry: %d" % settings["snapshot_seconds"],
        "snapshot_cron: \"\"",
        "",
        "log_level: %s" % settings["log_level"],
        "enable_debug_command: \"no\"",
        "",
    ]
    if settings["password"]:
        lines += ["requirepass: %s" % settings["password"], ""]
    return "\n".join(lines)


def _yaml_compose(settings):
    return "\n".join(
        [
            "services:",
            "  dragonfly:",
            "    image: %s:%s" % (config.IMAGE_REPOSITORY, settings["image_tag"]),
            "    container_name: %s" % config.COMPOSE_PROJECT,
            "    restart: unless-stopped",
            "    network_mode: host",
            "    ulimits:",
            "      memlock:",
            "        soft: -1",
            "        hard: -1",
            "    volumes:",
            "      - ./dragonfly.yaml:/opt/dragonflydb/dragonfly.yaml",
            "      - ./data:/data",
            "    command:",
            "      - --dbfilename=dump",
            "      - --dir=/data",
            "      - --logtostderr",
            "      - --maxmemory=%s" % settings["maxmemory"],
            "",
        ]
    )


def write(settings):
    """Materialise the deployment files and the data directory."""
    os.makedirs(settings["dir"], exist_ok=True)
    os.makedirs(config.WORK_DIR, exist_ok=True)

    with open(config.CONFIG_FILE, "w") as handle:
        handle.write(_yaml_config(settings))
    with open(config.COMPOSE_FILE, "w") as handle:
        handle.write(_yaml_compose(settings))
