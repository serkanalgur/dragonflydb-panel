#!/usr/bin/env python3
"""Unit tests for the pure layers: validation, rendering, INFO parsing.

No network, no docker, no panel. If a test needs any of those, the logic under
test is in the wrong place.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dragonflydb-panel"))

from dragonfly import compose, config  # noqa: E402
from dragonfly.client import Client, DragonflyError  # noqa: E402


def base(**overrides):
    settings = {
        "port": "6380",
        "bind": "127.0.0.1",
        "password": "",
        "maxmemory": "1gb",
        "maxmemory_policy": "noeviction",
        "dir": "/opt/dragonflydb/data",
        "snapshot_seconds": "900",
        "log_level": "notice",
        "image_tag": "v1.26.0",
    }
    settings.update(overrides)
    return settings


class ValidateTest(unittest.TestCase):
    def test_defaults_are_applied_for_missing_fields(self):
        result = config.validate({})
        self.assertEqual(result["port"], config.DEFAULT_PORT)
        self.assertEqual(result["bind"], config.DEFAULT_BIND)

    def test_port_6379_is_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.validate(base(port="6379"))

    def test_non_numeric_port_is_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.validate(base(port="not-a-port"))

    def test_out_of_range_port_is_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.validate(base(port="80"))

    def test_unknown_bind_is_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.validate(base(bind="10.0.0.1"))

    def test_unknown_policy_is_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.validate(base(maxmemory_policy="nonsense"))

    def test_relative_dir_is_normalised_to_absolute(self):
        result = config.validate(base(dir="relative/path"))
        self.assertTrue(os.path.isabs(result["dir"]))

    def test_snapshot_range_is_bounded(self):
        with self.assertRaises(config.ConfigError):
            config.validate(base(snapshot_seconds="99999"))


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.settings = config.validate(base())

    def test_compose_uses_host_network(self):
        rendered = compose._yaml_compose(self.settings)
        self.assertIn("network_mode: host", rendered)
        self.assertNotIn("ports:", rendered)

    def test_compose_relaxes_memlock_limit(self):
        self.assertIn("memlock:", compose._yaml_compose(self.settings))

    def test_compose_pins_the_image_tag(self):
        self.assertIn(":v1.26.0", compose._yaml_compose(self.settings))
        self.assertNotIn(":latest", compose._yaml_compose(self.settings))

    def test_password_appears_only_when_set(self):
        self.assertNotIn("requirepass", compose._yaml_config(self.settings))
        with_password = config.validate(base(password="s3cret"))
        self.assertIn("requirepass: s3cret", compose._yaml_config(with_password))

    def test_render_is_deterministic(self):
        self.assertEqual(
            compose._yaml_compose(self.settings),
            compose._yaml_compose(self.settings),
        )


class PersistenceTest(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        original = config.SETTINGS_FILE
        with tempfile.TemporaryDirectory() as workdir:
            config.SETTINGS_FILE = os.path.join(workdir, "settings.json")
            config.WORK_DIR = workdir
            try:
                saved = config.save(base(password="hunter2"))
                self.assertEqual(config.load()["password"], "hunter2")
                self.assertEqual(saved["port"], 6380)
            finally:
                config.SETTINGS_FILE = original

    def test_load_falls_back_to_defaults_when_file_missing(self):
        original = config.SETTINGS_FILE
        with tempfile.TemporaryDirectory() as workdir:
            config.SETTINGS_FILE = os.path.join(workdir, "absent.json")
            try:
                self.assertEqual(config.load()["port"], config.DEFAULT_PORT)
            finally:
                config.SETTINGS_FILE = original

    def test_load_ignores_corrupt_file(self):
        original = config.SETTINGS_FILE
        with tempfile.TemporaryDirectory() as workdir:
            path = os.path.join(workdir, "settings.json")
            with open(path, "w") as handle:
                handle.write("{not json")
            config.SETTINGS_FILE = path
            try:
                self.assertEqual(config.load()["port"], config.DEFAULT_PORT)
            finally:
                config.SETTINGS_FILE = original


class ClientTest(unittest.TestCase):
    INFO = "\n".join([
        "dragonfly_version:v1.26.0",
        "uptime_in_seconds:1234",
        "used_memory:2mb",
        "maxmemory:1gb",
        "db_keys:42",
        "connected_clients:7",
    ])

    def _offline_client(self, payload):
        """A Client whose transport is replaced, so no socket is opened."""
        client = Client(6380)
        client._get = lambda path: payload
        return client

    def test_stats_flattens_info_fields(self):
        stats = self._offline_client(self.INFO).stats()
        self.assertEqual(stats["version"], "v1.26.0")
        self.assertEqual(stats["keys"], "42")
        self.assertEqual(stats["clients"], "7")
        self.assertEqual(stats["uptime_seconds"], "1234")

    def test_stats_ignores_lines_without_colons(self):
        payload = self.INFO + "\n# a comment line\n"
        self.assertEqual(self._offline_client(payload).stats()["version"], "v1.26.0")

    def test_ping_reports_false_when_unreachable(self):
        client = Client(6380)

        def boom(path):
            raise DragonflyError("down")

        client._get = boom
        self.assertFalse(client.ping())


if __name__ == "__main__":
    unittest.main(verbosity=2)
