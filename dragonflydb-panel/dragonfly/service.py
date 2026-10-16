"""Lifecycle operations for the DragonflyDB container.

Thin, uniform wrappers over `docker compose`. Every method returns a
ComposeResult so callers never have to parse strings.
"""

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


def _run(args, timeout=180):
    try:
        completed = subprocess.run(
            args,
            cwd=config.WORK_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ComposeResult(False, "docker not found on this host")
    except subprocess.TimeoutExpired:
        return ComposeResult(False, "docker compose timed out after %ss" % timeout)
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
    import os

    return os.path.exists(config.COMPOSE_FILE)


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
