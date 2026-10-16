"""Loads dragonflydb_main the way the panel does, with a stubbed panel module.

The plugin module does `os.chdir("/www/server/panel")` and `sys.path.append("class/")`
at import time, so importing it outside a real panel requires faking that
layout. This catches the failure mode the unit tests cannot: a module that
compiles but does not load through the panel's entry-point conventions.
"""

import importlib
import os
import shutil
import sys
import tempfile
import unittest

PLUGIN_DIR = os.path.join(
    os.path.dirname(__file__), "..", "dragonflydb-panel"
)
PLUGIN_DIR = os.path.abspath(PLUGIN_DIR)

PANEL_PUBLIC = '''
def ReturnMsg(status, msg):
    return {"status": bool(status), "msg": msg}
'''


class PanelStub(object):
    """Stand in for /www/server/panel with just the helper we use."""

    def __init__(self, root):
        self.root = root
        os.makedirs(os.path.join(root, "class"), exist_ok=True)
        with open(os.path.join(root, "class", "public.py"), "w") as handle:
            handle.write(PANEL_PUBLIC)

    def cleanup(self):
        os.chdir(self.started_in)
        shutil.rmtree(self.root, ignore_errors=True)
        for name in list(sys.modules):
            if name in ("public", "dragonflydb_main"):
                del sys.modules[name]


class MainModuleTest(unittest.TestCase):
    def setUp(self):
        self.started_in = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        self.stub = PanelStub(self.tmp)
        self.stub.started_in = self.started_in

        # Stand in for being run by the panel: cwd is the panel directory and
        # cwd/class holds the panel helpers.
        os.chdir(self.tmp)
        sys.path.insert(0, PLUGIN_DIR)
        self.main = importlib.import_module("dragonflydb_main")

    def tearDown(self):
        sys.path.remove(PLUGIN_DIR)
        self.stub.cleanup()

    # ---- the conventions the panel depends on -----------------------------

    def test_class_is_named_after_the_plugin(self):
        self.assertTrue(hasattr(self.main, "dragonflydb_main"))

    def test_internal_modules_resolve_through_the_plugin_path(self):
        # The plugin package is imported by path insertion, not by the panel's
        # sys.path, so this proves the sibling package still resolves.
        self.assertTrue(hasattr(self.main, "config"))
        self.assertTrue(hasattr(self.main, "service"))

    def test_methods_return_the_panel_envelope(self):
        result = self.main.dragonflydb_main().GetSettings({})
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("msg", result)
        self.assertIsInstance(result["status"], bool)

    def test_structured_payload_is_json_inside_msg(self):
        import json

        result = self.main.dragonflydb_main().GetSettings({})
        payload = json.loads(result["msg"])
        self.assertEqual(payload["port"], 6380)
        self.assertEqual(payload["password"], "")

    def test_failures_report_status_false(self):
        # Port 6379 belongs to the panel's own Redis manager.
        result = self.main.dragonflydb_main().SetSettings({"port": "6379"})
        self.assertFalse(result["status"])
        self.assertIn("6379", result["msg"])

    def test_every_public_method_exists(self):
        for method in (
            "GetSettings", "SetSettings", "Install",
            "Start", "Stop", "Restart", "GetStatus", "GetLogs",
        ):
            self.assertTrue(
                callable(getattr(self.main.dragonflydb_main, method)),
                "%s is missing" % method,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
