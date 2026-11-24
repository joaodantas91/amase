import os
import sys
import unittest
import textwrap

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


if __name__ == "__main__":
    unittest.main()
