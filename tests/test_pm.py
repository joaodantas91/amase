import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import pm


class TestProjectManager(unittest.TestCase):
    def test_persona_file_exists_and_under_3kb(self):
        persona_path = os.path.join(REPO_ROOT, "personas", "pm.md")
        self.assertTrue(os.path.exists(persona_path))
        size = os.path.getsize(persona_path)
        self.assertLessEqual(size, 3072)
        with open(persona_path, "r") as f:
            content = f.read()
        self.assertIn("Project Manager", content)
        self.assertIn("TASK-XX", content)

    def test_next_task_number(self):
        backlog = textwrap.dedent("""
        - [x] **TASK-09: Older task**
        - [ ] **TASK-91: Current task**
        - [ ] **TASK-SEC-01: Security task**
        """).strip()
        self.assertEqual(pm.next_task_number(backlog), 92)
        self.assertEqual(pm.next_task_number(""), 1)

    def test_build_decomposition_prompt_includes_inputs_and_git_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = os.path.join(tmpdir, "BACKLOG.md")
            scope_path = os.path.join(tmpdir, "scope.md")
            with open(backlog_path, "w") as f:
                f.write("- [x] **TASK-10: Bootstrap CLI**\n")
            with open(scope_path, "w") as f:
                f.write("Allowed: scripts/\nForbidden: paid models\n")

            mock_files = ["amase", "scripts/pm.py", "tests/test_pm.py"]
            with patch("pm.scout.list_repo_files", return_value=mock_files) as mock_ls:
                prompt = pm.build_decomposition_prompt(
                    objective="Add webhook retry support",
                    backlog_path=backlog_path,
                    scope_path=scope_path,
                    status_input="Project Type: python\nWorking Tree: Clean",
                    repo_dir=tmpdir,
                )

            mock_ls.assert_called_once_with(repo_dir=tmpdir, limit=40)
            self.assertIn("Add webhook retry support", prompt)
            self.assertIn("TASK-11", prompt)
            self.assertIn("Allowed: scripts/", prompt)
            self.assertIn("Working Tree: Clean", prompt)
            self.assertIn("scripts/pm.py", prompt)
            self.assertIn("Bootstrap CLI", prompt)

    def test_sanitize_decomposed_tasks_dedupes_reassigns_and_caps_at_three(self):
        backlog = textwrap.dedent("""
        - [x] **TASK-05: Existing Auth Token Validator**
        - [ ] **TASK-06: Pending Rate Limiter Middleware**
        """).strip()
        raw_output = textwrap.dedent("""
        Here are the tasks:
        - [ ] **TASK-05: Existing Auth Token Validator**
          - **Goal:** Duplicate completed task.
          - **Files:** scripts/auth.py
          - **Criteria:** pytest passes

        - [ ] **TASK-XX: Add Webhook Retry Backoff**
          - **Goal:** Retry failed webhooks with exponential backoff.
          - **Files:** scripts/webhook.py
          - **Criteria:** python3 -m unittest tests/test_webhook.py

        - [ ] **TASK-06: Add Webhook Dead-Letter Queue**
          - **Goal:** Persist exhausted webhooks for inspection.
          - **Files:** scripts/dlq.py
          - **Criteria:** python3 -m unittest tests/test_dlq.py

        - [ ] **TASK-08: Add Webhook Metrics Counter**
          - **Goal:** Track retry counts in telemetry.
          - **Files:** scripts/telemetry.py
          - **Criteria:** python3 -m unittest tests/test_telemetry.py

        - [ ] **TASK-09: Fourth Extra Task Should Be Capped**
          - **Goal:** Should not be returned.
          - **Files:** scripts/extra.py
          - **Criteria:** exit 0
        """).strip()

        tasks = pm.sanitize_decomposed_tasks(raw_output, backlog_text=backlog, max_tasks=3)
        self.assertEqual(len(tasks), 3)
        self.assertIn("**TASK-07: Add Webhook Retry Backoff**", tasks[0])
        self.assertIn("**TASK-08: Add Webhook Dead-Letter Queue**", tasks[1])
        self.assertIn("**TASK-09: Add Webhook Metrics Counter**", tasks[2])
        self.assertNotIn("Existing Auth Token Validator", "\n".join(tasks))
        self.assertNotIn("Fourth Extra Task", "\n".join(tasks))

    def test_decompose_objective_uses_fleet_and_records_telemetry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = os.path.join(tmpdir, "BACKLOG.md")
            scope_path = os.path.join(tmpdir, "scope.md")
            with open(backlog_path, "w") as f:
                f.write("- [x] **TASK-01: Init**\n")
            with open(scope_path, "w") as f:
                f.write("Allowed: scripts/\n")

            llm_reply = textwrap.dedent("""
            - [ ] **TASK-02: Add PM CLI Flag**
              - **Goal:** Support dry-run mode cleanly.
              - **Files:** scripts/pm.py, tests/test_pm.py
              - **Criteria:** python3 -m unittest tests/test_pm.py
            """).strip()

            with patch("pm.scout.list_repo_files", return_value=["scripts/pm.py"]), \
                 patch("pm.query_fleet", return_value=llm_reply) as mock_fleet, \
                 patch("pm.get_last_usage", return_value={"model": "scout-fleet", "tokens_in": 120, "tokens_out": 45}), \
                 patch("pm.record_telemetry") as mock_telemetry:
                result = pm.decompose_objective(
                    objective="Support dry-run mode",
                    backlog_path=backlog_path,
                    scope_path=scope_path,
                    status_input="Working Tree: Clean",
                    repo_dir=tmpdir,
                )

            mock_fleet.assert_called_once()
            self.assertIn("**TASK-02: Add PM CLI Flag**", result)
            mock_telemetry.assert_called_once()
            self.assertEqual(mock_telemetry.call_args.kwargs["role"], "pm")

    def test_cli_help_and_dry_run(self):
        pm_script = os.path.join(SCRIPTS_DIR, "pm.py")
        help_res = subprocess.run(
            [sys.executable, pm_script, "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(help_res.returncode, 0)
        for flag in ("--objective", "--backlog", "--scope", "--status", "--dry-run"):
            self.assertIn(flag, help_res.stdout)

        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = os.path.join(tmpdir, "BACKLOG.md")
            with open(backlog_path, "w") as f:
                f.write("- [x] **TASK-41: Existing task**\n")
            dry_res = subprocess.run(
                [
                    sys.executable, pm_script,
                    "--objective", "Add status JSON output",
                    "--backlog", backlog_path,
                    "--repo", REPO_ROOT,
                    "--dry-run",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(dry_res.returncode, 0)
            self.assertIn("- [ ] **TASK-42: Add status JSON output**", dry_res.stdout)
            self.assertIn("- **Goal:**", dry_res.stdout)
            self.assertIn("- **Files:**", dry_res.stdout)
            self.assertIn("- **Criteria:**", dry_res.stdout)
            # Dry-run must not mutate BACKLOG.md
            with open(backlog_path, "r") as f:
                self.assertEqual(f.read(), "- [x] **TASK-41: Existing task**\n")


if __name__ == "__main__":
    unittest.main()
