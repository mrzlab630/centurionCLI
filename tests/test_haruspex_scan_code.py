import builtins
from contextlib import redirect_stderr, redirect_stdout
import errno
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


SCAN_CODE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "skills", "haruspex", "scripts", "scan_code.py"
)
SCAN_CODE_SPEC = importlib.util.spec_from_file_location("scan_code_test", SCAN_CODE_PATH)
scan_code = importlib.util.module_from_spec(SCAN_CODE_SPEC)
SCAN_CODE_SPEC.loader.exec_module(scan_code)


class HaruspexScanCodeTests(unittest.TestCase):
    def test_scans_file_target(self):
        with tempfile.TemporaryDirectory() as target:
            source = os.path.join(target, "app.ts")
            with open(source, "w") as handle:
                handle.write("element.innerHTML = userInput;\n")

            result = scan_code.main.__wrapped__(SimpleNamespace(target=source))

        self.assertEqual(result["total_findings"], 1)
        self.assertEqual(result["details"][0]["file"], source)

    def test_scans_javascript_and_typescript_extensions(self):
        with tempfile.TemporaryDirectory() as target:
            for extension in (".mjs", ".cjs", ".ts", ".tsx"):
                with open(os.path.join(target, f"vulnerable{extension}"), "w") as handle:
                    handle.write("element.innerHTML = userInput;\n")

            result = scan_code.main.__wrapped__(SimpleNamespace(target=target))

        self.assertEqual(result["total_findings"], 4)
        self.assertTrue(result["scan_complete"])

    def test_reports_incomplete_scan_when_a_file_cannot_be_read(self):
        with tempfile.TemporaryDirectory() as target:
            blocked_path = os.path.join(target, "blocked.mjs")
            with open(blocked_path, "w") as handle:
                handle.write("element.innerHTML = userInput;\n")

            real_open = builtins.open

            def reject_blocked_file(path, *args, **kwargs):
                if path == blocked_path:
                    raise PermissionError("read denied")
                return real_open(path, *args, **kwargs)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch("builtins.open", side_effect=reject_blocked_file),
                mock.patch.object(sys, "argv", ["scan_code.py", target]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
                self.assertRaises(SystemExit) as exit_error,
            ):
                scan_code.main()

        self.assertEqual(exit_error.exception.code, 1)
        output = stdout.getvalue()
        start = output.index("<<<LEGION_JSON_START>>>") + len("<<<LEGION_JSON_START>>>")
        end = output.index("<<<LEGION_JSON_END>>>")
        payload = json.loads(output[start:end])
        self.assertEqual(payload["status"], "error")
        self.assertIn("Scan incomplete", payload["error"])
        self.assertIn(blocked_path, payload["error"])
        self.assertIn("Could not read", stderr.getvalue())

    def test_reports_incomplete_scan_when_a_directory_cannot_be_read(self):
        with tempfile.TemporaryDirectory() as target:
            blocked_path = os.path.join(target, "blocked")
            os.mkdir(blocked_path)

            def blocked_walk(path, onerror=None):
                onerror(PermissionError(errno.EACCES, "read denied", blocked_path))
                return iter(())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch.object(scan_code.os, "walk", side_effect=blocked_walk),
                mock.patch.object(sys, "argv", ["scan_code.py", target]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
                self.assertRaises(SystemExit) as exit_error,
            ):
                scan_code.main()

        self.assertEqual(exit_error.exception.code, 1)
        output = stdout.getvalue()
        start = output.index("<<<LEGION_JSON_START>>>") + len("<<<LEGION_JSON_START>>>")
        end = output.index("<<<LEGION_JSON_END>>>")
        payload = json.loads(output[start:end])
        self.assertEqual(payload["status"], "error")
        self.assertIn(blocked_path, payload["error"])
        self.assertIn("Could not read", stderr.getvalue())
