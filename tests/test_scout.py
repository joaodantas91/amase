import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import scout


class TestScout(unittest.TestCase):
    def test_extract_task_ids(self):
        text = textwrap.dedent("""
        # Backlog
        - [x] **TASK-01: First task**
        - [ ] **TASK-02: Second task**
        - [ ] **TASK-54-A: Multi-segment task**
        """).strip()
        ids = scout.extract_task_ids(text)
        self.assertEqual(ids, {"TASK-01", "TASK-02", "TASK-54-A"})

    def test_extract_all_backlog_titles(self):
        text = textwrap.dedent("""
        - [x] **TASK-57: Lever ATS Adapter - Page Detection & Field Mapping**
        - [x] **TASK-58: Popup Profile Selector**
        - [ ] **TASK-59: Ashby ATS Platform Adapter**
        """).strip()
        titles = scout.extract_all_backlog_titles(text)
        self.assertEqual(len(titles), 3)
        self.assertIn("Lever ATS Adapter - Page Detection & Field Mapping", titles)
        self.assertIn("Popup Profile Selector", titles)
        self.assertIn("Ashby ATS Platform Adapter", titles)

    def test_extract_task_blocks(self):
        text = textwrap.dedent("""
        - [ ] **TASK-10: Test Suite Overhaul**
          - **Goal:** Improve unit test coverage across all core modules.
          - **Files:** tests/app.test.ts
          - **Criteria:** 100% tests pass.

        - [ ] **TASK-11: UI Refactor**
          - **Goal:** Centralize CSS tokens.
          - **Files:** src/tokens.css
          - **Criteria:** Zero raw hex values.
        """).strip()
        blocks = scout.extract_task_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["id"], "TASK-10")
        self.assertIn("Test Suite Overhaul", blocks[0]["title"])
        self.assertIn("**Goal:** Improve unit test coverage", blocks[0]["text"])
        self.assertEqual(blocks[1]["id"], "TASK-11")

    def test_normalize_title_tokens(self):
        tokens = scout.normalize_title_tokens("Lever ATS Adapter - Page Detection & Field Mapping")
        self.assertIn("lever", tokens)
        self.assertIn("adapter", tokens)
        # Generic terms should be stripped
        self.assertNotIn("detection", tokens)
        self.assertNotIn("mapping", tokens)
        self.assertNotIn("and", tokens)
        self.assertNotIn("the", tokens)

    def test_is_duplicate_title(self):
        existing = [
            "Lever ATS Adapter – Page Detection & Field Mapping",
            "QuickFill Floating Bar – In-Page Autofill Trigger",
            "Greenhouse ATS Adapter & Custom Field Detection"
        ]

        # Near-identical or re-phrased duplicate slices should be flagged
        self.assertTrue(scout.is_duplicate_title("Lever ATS Adapter – Field Mapping Implementation", existing))
        self.assertTrue(scout.is_duplicate_title("QuickFill Floating Bar UI – Trigger Autofill", existing))
        self.assertTrue(scout.is_duplicate_title("Greenhouse ATS Platform Adapter", existing))

        # Distinct new slices should NOT be flagged as duplicates
        self.assertFalse(scout.is_duplicate_title("Ashby ATS Platform Adapter & Custom Field Detection", existing))
        self.assertFalse(scout.is_duplicate_title("Multilingual Diacritic-Folding Heuristic Matcher", existing))
        self.assertFalse(scout.is_duplicate_title("Production Chrome & Firefox Package Integrity CI Verification", existing))

    def test_list_repo_files_generic_and_filters_assets(self):
        mock_stdout = "\n".join([
            ".agents/skills/ui-ux-pro-max/data/colors.csv",
            "skills/ponytail/SKILL.md",
            "assets/logo.png",
            "package-lock.json",
            "config/settings.yaml",
            "amase",
            "scripts/scout.py",
            "personas/scout.md",
            "tests/test_scout.py",
        ])
        mock_proc = subprocess.CompletedProcess(args=["git", "ls-files"], returncode=0, stdout=mock_stdout, stderr="")
        with patch("scout.subprocess.run", return_value=mock_proc) as mock_run:
            files = scout.list_repo_files(repo_dir="/tmp/repo", limit=20)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ["git", "-C", "/tmp/repo", "ls-files"])
        self.assertIn("scripts/scout.py", files)
        self.assertIn("personas/scout.md", files)
        self.assertIn("tests/test_scout.py", files)
        self.assertIn("amase", files)
        self.assertNotIn("assets/logo.png", files)
        self.assertNotIn("config/settings.yaml", files)
        self.assertNotIn(".agents/skills/ui-ux-pro-max/data/colors.csv", files)
        self.assertNotIn("skills/ponytail/SKILL.md", files)

    def test_find_test_gaps(self):
        files = [
            "scripts/scout.py",
            "scripts/fleet.py",
            "scripts/status.py",
            "tests/test_scout.py",
            "tests/test_status.py",
            "personas/scout.md",
        ]
        gaps = scout.find_test_gaps(files)
        self.assertEqual(gaps, ["scripts/fleet.py"])

    def test_build_discovery_prompt_includes_scope_discovery_commits_and_gaps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scope_path = os.path.join(tmpdir, "scope.md")
            discovery_path = os.path.join(tmpdir, "discovery.md")
            backlog_path = os.path.join(tmpdir, "BACKLOG.md")
            with open(scope_path, "w") as f:
                f.write("Allowed: scripts/\nForbidden: secrets\n")
            with open(discovery_path, "w") as f:
                f.write("- [PROPOSED] Add fleet unit tests\n")
            with open(backlog_path, "w") as f:
                f.write("- [x] **TASK-01: Init repo**\n- [ ] **TASK-02: Next step**\n")

            with patch("scout.list_repo_files", return_value=["scripts/fleet.py", "tests/test_scout.py"]), \
                 patch("scout.get_recent_commits", return_value=["abc1234 feat: update scout"]):
                prompt, _ = scout.build_discovery_prompt(
                    None,
                    backlog_path,
                    scope_path=scope_path,
                    discovery_path=discovery_path,
                    repo_dir=tmpdir,
                )

            self.assertIn("Allowed: scripts/", prompt)
            self.assertIn("Add fleet unit tests", prompt)
            self.assertIn("abc1234 feat: update scout", prompt)
            self.assertIn("scripts/fleet.py", prompt)
            self.assertIn("POTENTIAL TEST COVERAGE GAPS", prompt)
            self.assertIn("Init repo", prompt)


if __name__ == "__main__":
    unittest.main()
