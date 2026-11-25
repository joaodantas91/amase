"""Unit tests for Structured Task Milestone Banner Script."""

import os
import subprocess
import sys
import unittest

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
TASK_BANNER = os.path.join(SCRIPT_DIR, "task_banner.py")


def _run_banner(*args):
    return subprocess.run(
        [sys.executable, TASK_BANNER, *args],
        capture_output=True,
        text=True,
    )


class TestTaskBannerHelp(unittest.TestCase):
    def test_help_exits_zero(self):
        res = _run_banner("--help")
        self.assertEqual(res.returncode, 0)

    def test_help_contains_description(self):
        res = _run_banner("--help")
        self.assertIn("Structured Task Milestone Banner", res.stdout)


class TestTaskBannerImport(unittest.TestCase):
    def test_module_imports_cleanly(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_banner", TASK_BANNER
        )
        self.assertIsNotNone(spec)

    def test_py_compile_passes(self):
        import py_compile
        py_compile.compile(TASK_BANNER, doraise=True)  # nosec