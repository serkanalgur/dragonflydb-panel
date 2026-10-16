"""Lifecycle operations for the DragonflyDB container.

Thin, uniform wrappers over `docker compose`. Every method returns a
ComposeResult so callers never have to parse strings.
"""

import os
import shutil
import subprocess

from . import config


class ComposeResult(object):
    """Outcome of a compose invocation."""

    def __init__(self, ok, message):
        self.ok = ok
        self.message = message

    def __bool__(self):
        return self.ok

    __nonzero__ = __bool__  # Python 2 parity with older panel runtimes

    def __repr__(self):
        return "ComposeResult(ok=%r)" % self.ok


def _run(args, timeout=180, cwd=None):
    try:
        completed = subprocess.run(
            args,
            cwd=cwd if cwd and os.path.isdir(cwd) else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ComposeResult(False, "docker not found on this host")
    except PermissionError:
        return ComposeResult(False, "permission denied running: %s" % args[0])
    except subprocess.TimeoutExpired:
        return ComposeResult(False, "timed out after %ss running %s" % (timeout, args[0]))
    return ComposeResult(
        completed.returncode == 0,
        completed.stdout.decode("utf-8", "replace").strip(),
    )


def _compose(subcommand, *extra):
    return _run(
        [
            "docker", "compose",
            "-p", config.COMPOSE_PROJECT,
            "-f", config.COMPOSE_FILE,
            subcommand,
        ] + list(extra)
    )


def is_installed():
    """True once the deployment files exist on disk."""
    return os.path.exists(config.COMPOSE_FILE)


# ---- environment ----------------------------------------------------------
# Reported in the settings page before any action is offered, so the user is
# never told "command not found" after clicking Install.

def docker_available():
    """True when the docker client is on PATH."""
    return shutil.which("docker") is not None


def compose_available():
    """True when `docker compose` v2 works, not just the client binary."""
    if not docker_available():
        return False
    return _run(["docker", "compose", "version"], timeout=15).ok


def _daemon_available():
    if not docker_available():
        return False
    return _run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20).ok


def _container_running():
    """True when the DragonflyDB container is currently up."""
    if not docker_available():
        return False
    result = _run(
        [
            "docker", "inspect", "-f", "{{.State.Running}}",
            config.COMPOSE_PROJECT,
        ],
        timeout=20,
    )
    return result.ok and result.message.strip().lower() == "true"


def prerequisite_message():
    """Why the actions are unavailable, or None when everything is in place.

    Checked in the order a user would fix it, so the message names the first
    thing that is actually missing.
    """
    if not docker_available():
        return "Docker is not installed on this server."
    if not _daemon_available():
        return "Docker is installed but not running, or the panel user cannot reach it."
    if not compose_available():
        return "Docker Compose v2 is not available (the plugin needs `docker compose`)."
    return None


def environment():
    """Everything the settings page needs to render its controls."""
    return {
        "docker": docker_available(),
        "compose": compose_available(),
        "installed": is_installed(),
        "running": _container_running(),
        "problem": prerequisite_message(),
    }


def pull():
    return _compose("pull")


def start():
    return _compose("up", "-d", "--remove-orphans")


def stop():
    return _compose("stop")


def restart():
    return _compose("restart")


def logs(lines=200):
    return _compose("logs", "--tail", str(lines))


def destroy():
    """Stop and remove containers *and* volumes. Used by the uninstaller."""
    return _compose("down", "-v", "--remove-orphans")
