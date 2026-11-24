import os
import sys
import unittest
import tempfile
import importlib.util

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
script_path = os.path.join(SCRIPTS_DIR, "diagnose-failure.py")
spec = importlib.util.spec_from_file_location("diagnose_failure", script_path)
diagnose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnose)


class TestDiagnose(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_log(self, text):
        p = os.path.join(self.temp_dir.name, "worker.log")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_diagnose_quota_exhausted(self):
        log = self._create_log("Error 429: Free usage limit reached for this model. Try again later.")
        sig, reason, _ = diagnose.diagnose_log(log)
        self.assertEqual(sig, "QUOTA_EXHAUSTED")

        log2 = self._create_log("rate_limit_exceeded: TPM limit reached on free tier.")
        sig2, _, _ = diagnose.diagnose_log(log2)
        self.assertEqual(sig2, "QUOTA_EXHAUSTED")

    def test_diagnose_compiler_error(self):
        log = self._create_log("src/core/ats/jobContext.ts:45:11 - error TS2366: Function lacks ending return statement.")
        sig, _, _ = diagnose.diagnose_log(log)
        self.assertEqual(sig, "COMPILER_ERROR")

        log2 = self._create_log("FAILED tests/options.test.ts > Options page > should save profile correctly")
        sig2, _, _ = diagnose.diagnose_log(log2)
        self.assertEqual(sig2, "COMPILER_ERROR")

        log3 = self._create_log("svelte-check found 2 errors and 0 warnings")
        sig3, _, _ = diagnose.diagnose_log(log3)
        self.assertEqual(sig3, "COMPILER_ERROR")

    def test_diagnose_socket_stall(self):
        log = self._create_log("Model stall detected (no output or progress for 90s). Forcing failover...")
        sig, _, _ = diagnose.diagnose_log(log)
        self.assertEqual(sig, "SOCKET_STALL")

    def test_diagnose_context_bloat(self):
        lines = ["reading path /home/src/file{}.ts".format(i) for i in range(12)]
        log = self._create_log("\n".join(lines))
        sig, _, metrics = diagnose.diagnose_log(log)
        self.assertEqual(sig, "CONTEXT_BLOAT")
        self.assertGreaterEqual(metrics["files_read"], 10)

    def test_diagnose_model_abort(self):
        log = self._create_log("I have inspected the codebase and determined no changes are required.")
        sig, _, _ = diagnose.diagnose_log(log)
        self.assertEqual(sig, "MODEL_ABORT")


if __name__ == "__main__":
    unittest.main()
