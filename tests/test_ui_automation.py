import os
import subprocess
import tempfile
import unittest

ORCHESTRATOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestUIAutomation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = self.temp_dir.name
        os.makedirs(os.path.join(self.repo_dir, ".amase"), exist_ok=True)
        os.makedirs(os.path.join(self.repo_dir, "src", "styles"), exist_ok=True)

        # Create dummy tokens.css
        self.tokens_path = os.path.join(self.repo_dir, "src", "styles", "tokens.css")
        with open(self.tokens_path, "w") as f:
            f.write("""
:root {
  --color-bg-primary: #0f172a;
  --color-text-primary: #f8fafc;
  --space-sm: 8px;
  --space-md: 16px;
  --radius-sm: 4px;
}
""")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_agent_injects_ui_tokens_for_ui_task(self):
        cmd = [
            "bash",
            os.path.join(ORCHESTRATOR_DIR, "scripts", "generate-agent.sh"),
            "--repo", self.repo_dir,
            "--role", "builder",
            "--task", "TASK-99: QuickFill Floating Bar Svelte Component Style"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"generate-agent failed: {res.stderr}")
        self.assertIn("DESIGN SYSTEM & UI INVARIANTS", res.stdout)
        self.assertIn("--color-bg-primary", res.stdout)
        self.assertIn("ZERO RAW HEX COLORS", res.stdout)

    def test_generate_agent_skips_ui_tokens_for_backend_task(self):
        cmd = [
            "bash",
            os.path.join(ORCHESTRATOR_DIR, "scripts", "generate-agent.sh"),
            "--repo", self.repo_dir,
            "--role", "builder",
            "--task", "TASK-88: Greenhouse ATS Adapter Regex Parsing"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertNotIn("DESIGN SYSTEM & UI INVARIANTS", res.stdout)


if __name__ == "__main__":
    unittest.main()
