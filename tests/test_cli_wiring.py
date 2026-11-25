import json
import os
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMASE_BIN = os.path.join(REPO_ROOT, "amase")


class TestCliAndRoutingWiring(unittest.TestCase):
    def test_amase_help_documents_project_manager_task(self):
        res = subprocess.run(
            [AMASE_BIN, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        task_lines = [line for line in res.stdout.splitlines() if "amase task" in line]
        self.assertTrue(task_lines, "amase --help missing task command documentation")
        self.assertIn("Project Manager", task_lines[0])

    def test_amase_task_dry_run_invokes_pm_and_preserves_backlog(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            amase_dir = os.path.join(tmpdir, ".amase")
            os.makedirs(amase_dir, exist_ok=True)
            backlog_path = os.path.join(tmpdir, "BACKLOG.md")
            original_backlog = "- [x] **TASK-14: Existing task**\n"
            with open(backlog_path, "w") as f:
                f.write(original_backlog)
            with open(os.path.join(amase_dir, "scope.md"), "w") as f:
                f.write("Allowed: scripts/\n")

            res = subprocess.run(
                [AMASE_BIN, "task", "--dry-run", "Add webhook retry queue"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            # pm.py assigns TASK-15 (unlike legacy scout.py hardcoded TASK-99)
            self.assertIn("- [ ] **TASK-15: Add webhook retry queue**", res.stdout)
            self.assertIn("- **Goal:**", res.stdout)
            self.assertIn("- **Files:**", res.stdout)
            self.assertIn("- **Criteria:**", res.stdout)
            with open(backlog_path, "r") as f:
                self.assertEqual(f.read(), original_backlog)

    def test_amase_task_without_objective_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = os.path.join(tmpdir, "BACKLOG.md")
            with open(backlog_path, "w") as f:
                f.write("- [x] **TASK-01: Init**\n")
            res = subprocess.run(
                [AMASE_BIN, "task"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res.returncode, 0)
            with open(backlog_path, "r") as f:
                self.assertEqual(f.read(), "- [x] **TASK-01: Init**\n")

    def test_repo_config_registers_pm_routing(self):
        cfg_path = os.path.join(REPO_ROOT, ".amase", "config.json")
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        routing = cfg.get("persona_routing", {})
        self.assertIn("pm", routing)
        self.assertIsInstance(routing["pm"], list)
        self.assertGreater(len(routing["pm"]), 0)

    def test_init_project_scaffolds_and_heals_pm_routing(self):
        init_script = os.path.join(REPO_ROOT, "scripts", "init-project.sh")
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                ["bash", init_script, tmpdir],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            cfg_path = os.path.join(tmpdir, ".amase", "config.json")
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            self.assertIn("pm", cfg.get("persona_routing", {}))

            # Simulate legacy config missing persona_routing.pm and verify --heal adds it
            del cfg["persona_routing"]["pm"]
            cfg["persona_routing"]["builder"] = ["custom/model"]
            with open(cfg_path, "w") as f:
                json.dump(cfg, f)

            heal_res = subprocess.run(
                ["bash", init_script, tmpdir, "--heal"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(heal_res.returncode, 0, heal_res.stderr)
            with open(cfg_path, "r") as f:
                healed = json.load(f)
            self.assertIn("pm", healed.get("persona_routing", {}))
            self.assertEqual(healed["persona_routing"]["builder"], ["custom/model"])

    def test_generate_agent_supports_all_decoupled_personas(self):
        gen_script = os.path.join(REPO_ROOT, "scripts", "generate-agent.sh")
        expected_headers = {
            "builder": "BUILDER BOUNDARIES",
            "pm": "PROJECT MANAGER BOUNDARIES",
            "scout": "SCOUT BOUNDARIES",
            "sentinel": "SENTINEL BOUNDARIES",
            "designer": "DESIGNER BOUNDARIES",
            "reviewer": "REVIEWER BOUNDARIES",
            "coordinator": "COORDINATOR BOUNDARIES",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".amase"), exist_ok=True)
            with open(os.path.join(tmpdir, ".amase", "scope.md"), "w") as f:
                f.write("Allowed: scripts/\n")

            for role, expected_section in expected_headers.items():
                res = subprocess.run(
                    [
                        "bash",
                        gen_script,
                        "--repo", tmpdir,
                        "--role", role,
                        "--task", "Verify persona compatibility",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(res.returncode, 0, f"{role} failed: {res.stderr}")
                self.assertIn(f"# AMASE Scoped Agent: {role}", res.stdout)
                self.assertIn("PROJECT SCOPE BOUNDARIES", res.stdout)
                self.assertIn(expected_section, res.stdout)


if __name__ == "__main__":
    unittest.main()
