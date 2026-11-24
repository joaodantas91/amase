import os
import sys
import unittest
import tempfile
import json

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import status


class TestStatus(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detect_project_type(self):
        # Node
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        open(os.path.join(d, "package.json"), "w").close()
        self.assertEqual(status.detect_project_type(d), "node")

        # Rust
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        open(os.path.join(d, "Cargo.toml"), "w").close()
        self.assertEqual(status.detect_project_type(d), "rust")

        # Python
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        open(os.path.join(d, "pyproject.toml"), "w").close()
        self.assertEqual(status.detect_project_type(d), "python")

        # Go
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        open(os.path.join(d, "go.mod"), "w").close()
        self.assertEqual(status.detect_project_type(d), "go")

        # Generic
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        self.assertEqual(status.detect_project_type(d), "generic")

    def test_get_backlog_stats(self):
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        backlog_file = os.path.join(d, "BACKLOG.md")
        content = """# Project Backlog
- [x] **TASK-01: Setup tooling**
- [x] **TASK-02: Initial prototype**
- [ ] **TASK-03: Add authentication**
- [ ] **TASK-04: Implement dashboard**
"""
        with open(backlog_file, "w") as f:
            f.write(content)

        next_task, pending, total = status.get_backlog_stats(d)
        self.assertEqual(total, 4)
        self.assertEqual(pending, 2)
        self.assertIn("TASK-03", next_task)

    def test_get_retrospectives_count(self):
        d = tempfile.mkdtemp(dir=self.temp_dir.name)
        fake_retro = os.path.join(d, "retros.jsonl")

        entries = [
            {"project": d, "failure_signature": "SUCCESS"},
            {"project": d, "failure_signature": "SUCCESS"},
            {"project": d, "failure_signature": "COMPILER_ERROR"},
            {"project": "/some/other/repo", "failure_signature": "SUCCESS"}
        ]
        with open(fake_retro, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        # Monkey-patch retro_path check
        orig_expanduser = os.path.expanduser
        try:
            os.path.expanduser = lambda path: fake_retro if "retrospectives.jsonl" in path else orig_expanduser(path)
            succ, fail, proj_total, global_total = status.get_retrospectives_count(d)
            self.assertEqual(succ, 2)
            self.assertEqual(fail, 1)
            self.assertEqual(proj_total, 3)
            self.assertEqual(global_total, 4)
        finally:
            os.path.expanduser = orig_expanduser


if __name__ == "__main__":
    unittest.main()
