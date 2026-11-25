import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import fleet  # noqa: E402
import stream_filter  # noqa: E402


class TestStreamFilter(unittest.TestCase):
    def test_formats_agy_ndjson_lifecycle_and_dedups_active_done_tool(self):
        events = [
            "warning: --mode auto is not available for this account; continuing in the default mode.\n",
            json.dumps({
                "event": "init",
                "conversation_id": "conv-1",
                "init": {"model": "gemini-3.8-flash-medium", "cwd": "/tmp/worktrees/TASK-93"},
            }) + "\n",
            json.dumps({
                "event": "step_update",
                "step_update": {"step_index": 0, "state": "DONE", "step_type": "user_input"},
            }) + "\n",
            json.dumps({
                "event": "step_update",
                "step_update": {"step_index": 1, "state": "DONE", "step_type": "agent_response", "duration_seconds": 1.2},
            }) + "\n",
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_index": 2,
                    "state": "ACTIVE",
                    "step_type": "tool",
                    "tool_name": "read_file",
                    "tool_info": {"name": "read_file", "parameters": {"Path": "/tmp/worktrees/TASK-93/scripts/fleet.py"}},
                },
            }) + "\n",
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_index": 2,
                    "state": "DONE",
                    "step_type": "tool",
                    "tool_name": "read_file",
                    "duration_seconds": 0.4,
                    "tool_info": {"name": "read_file", "parameters": {"Path": "/tmp/worktrees/TASK-93/scripts/fleet.py"}},
                },
            }) + "\n",
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_index": 3,
                    "state": "DONE",
                    "step_type": "tool",
                    "tool_name": "run_command",
                    "tool_info": {"name": "run_command", "parameters": {"CommandLine": ".amase/test-gate.sh"}},
                },
            }) + "\n",
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_index": 4,
                    "state": "DONE",
                    "step_type": "agent_response",
                    "text": "All checks passed cleanly.",
                },
            }) + "\n",
            json.dumps({
                "event": "result",
                "status": "success",
                "duration_seconds": 8.5,
            }) + "\n",
        ]

        raw_input = "".join(events)
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "worker.log")
            count = stream_filter.filter_stream(io.StringIO(raw_input), out, log_path=log_path)
            with open(log_path, "r", encoding="utf-8") as f:
                logged = f.read()

        self.assertEqual(logged, raw_input)
        lines = out.getvalue().splitlines()
        self.assertEqual(count, len(lines))
        self.assertEqual(
            lines,
            [
                "[agent] init (gemini-3.8-flash-medium)",
                "[tool] read_file -> scripts/fleet.py",
                "[tool] run_command -> .amase/test-gate.sh",
                "[agent] All checks passed cleanly.",
                "[done] success (8.5s)",
            ],
        )

    def test_suppresses_malformed_json_fragments_and_surfaces_text_errors(self):
        flt = stream_filter.StreamFilter()
        self.assertIsNone(flt.format_line('{"event":"step_update","partial":'))
        self.assertIsNone(flt.format_line("   \n"))
        self.assertEqual(
            flt.format_line("Error: connection reset by peer\n"),
            "[agent] Error: connection reset by peer",
        )
        self.assertEqual(
            flt.format_line(json.dumps({"event": "error", "error": {"message": "quota hit"}, "duration_seconds": 2.0})),
            "[done] error: quota hit (2.0s)",
        )

    def test_last_activity_ignores_truncated_json_and_returns_concise_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "worker.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"event": "init", "init": {"model": "gemini-3.8-flash-medium", "cwd": "/repo"}}) + "\n")
                f.write(json.dumps({
                    "event": "step_update",
                    "step_update": {
                        "step_index": 2,
                        "state": "ACTIVE",
                        "step_type": "tool",
                        "tool_name": "edit_file",
                        "tool_info": {"parameters": {"Path": "/repo/scripts/dispatch-worker.sh"}},
                    },
                }) + "\n")
                f.write(json.dumps({
                    "event": "step_update",
                    "step_update": {"step_index": 3, "state": "DONE", "step_type": "agent_response", "duration_seconds": 1.1},
                }) + "\n")
                f.write('{"event":"step_update","step_update":{"conversation_id":"truncated\n')

            summary = stream_filter.last_activity(log_path)
            self.assertEqual(summary, "[tool] edit_file -> scripts/dispatch-worker.sh")
            self.assertFalse(summary.startswith("{"))

    def test_last_activity_handles_plain_text_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "opencode.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("warning: --mode auto is not available for this account\n")
                f.write("Running unit tests...\n")

            self.assertEqual(stream_filter.last_activity(log_path), "Running unit tests...")

    def test_cli_filters_stdin_to_stdout_and_writes_raw_log(self):
        script = os.path.join(SCRIPTS_DIR, "stream_filter.py")
        ndjson = (
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_index": 1,
                    "state": "ACTIVE",
                    "step_type": "tool",
                    "tool_name": "read_file",
                    "tool_info": {"parameters": {"Path": "README.md"}},
                },
            })
            + "\n"
            + json.dumps({"event": "done", "status": "ok", "duration_seconds": 3.0})
            + "\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "raw.log")
            res = subprocess.run(
                [sys.executable, script, log_path],
                input=ndjson,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(
                res.stdout.splitlines(),
                ["[tool] read_file -> README.md", "[done] ok (3.0s)"],
            )
            with open(log_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), ndjson)

            hb_res = subprocess.run(
                [sys.executable, script, "--last-activity", log_path],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(hb_res.returncode, 0, hb_res.stderr)
            self.assertEqual(hb_res.stdout.strip(), "[done] ok (3.0s)")

    def test_dispatch_worker_and_fleet_use_gemini_38_flash_tier(self):
        dispatch_path = os.path.join(SCRIPTS_DIR, "dispatch-worker.sh")
        with open(dispatch_path, "r", encoding="utf-8") as f:
            dispatch_src = f.read()

        self.assertIn("agy/gemini-3.8-flash-medium", dispatch_src)
        self.assertIn("agy/gemini-3.8-flash-high", dispatch_src)
        self.assertIn("agy/gemini-4-hydrogen-medium", dispatch_src)
        self.assertLess(
            dispatch_src.index("agy/gemini-3.8-flash-medium"),
            dispatch_src.index("agy/gemini-3.8-flash-high"),
        )
        self.assertLess(
            dispatch_src.index("agy/gemini-3.8-flash-high"),
            dispatch_src.index("agy/gemini-4-hydrogen-medium"),
        )
        self.assertIn("stream_filter.py", dispatch_src)
        self.assertIn("--last-activity", dispatch_src)

        with patch.dict(os.environ, {"AMASE_MODEL_TIER": "pro", "AGY_BIN": "/bin/true"}):
            with patch("fleet.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="ok", stderr=""
                )
                out = fleet.query_fleet("ping")
                self.assertEqual(out, "ok")
                cmd = mock_run.call_args[0][0]
                self.assertIn("gemini-3.8-flash-low", cmd)


if __name__ == "__main__":
    unittest.main()
