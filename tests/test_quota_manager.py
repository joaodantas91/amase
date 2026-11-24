import os
import sys
import time
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import quota_manager


class TestQuotaManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(self.temp_dir.name, "test_quota.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_normalize_provider(self):
        self.assertEqual(quota_manager.normalize_provider("opencode/nemotron-3.5-lightning-free"), "opencode_free")
        self.assertEqual(quota_manager.normalize_provider("opencode/beam-free"), "opencode_free")
        self.assertEqual(quota_manager.normalize_provider("opencode/claude-3-5-sonnet"), "opencode")
        self.assertEqual(quota_manager.normalize_provider("nvidia/nvidia/nemotron-3.5-lightning-30b-a3b"), "nvidia")
        self.assertEqual(quota_manager.normalize_provider("openrouter/openrouter/free"), "openrouter_free")
        self.assertEqual(quota_manager.normalize_provider("groq/llama-3.3-70b-versatile"), "groq")
        self.assertEqual(quota_manager.normalize_provider("ollama/qwen2.5-coder:14b"), "ollama")

    def test_record_and_check_quota(self):
        # Initially available
        avail, msg = quota_manager.check_quota("opencode/beam-free", cache_file=self.cache_file)
        self.assertTrue(avail)
        self.assertEqual(msg, "")

        # Record exhaustion with 1-second TTL
        quota_manager.record_exhaustion("opencode/beam-free", reason="Rate limit reached", ttl=1, cache_file=self.cache_file)

        # Immediately check -> should be exhausted
        avail, msg = quota_manager.check_quota("opencode/beam-free", cache_file=self.cache_file)
        self.assertFalse(avail)
        self.assertIn("opencode_free", msg)
        self.assertIn("Rate limit reached", msg)

        # Another free model in same pool should also be blocked
        avail_other, msg_other = quota_manager.check_quota("opencode/flint-40b-free", cache_file=self.cache_file)
        self.assertFalse(avail_other)

        # A non-free opencode model should NOT be blocked by free pool exhaustion
        avail_paid, _ = quota_manager.check_quota("opencode/claude-3-5-sonnet", cache_file=self.cache_file)
        self.assertTrue(avail_paid)

        # Wait past TTL
        time.sleep(1.1)
        avail_after, _ = quota_manager.check_quota("opencode/beam-free", cache_file=self.cache_file)
        self.assertTrue(avail_after)

    def test_clear_cache(self):
        quota_manager.record_exhaustion("nvidia/model-a", ttl=60, cache_file=self.cache_file)
        quota_manager.record_exhaustion("groq/model-b", ttl=60, cache_file=self.cache_file)

        # Clear specific provider
        quota_manager.clear_cache(provider="nvidia", cache_file=self.cache_file)
        avail_nv, _ = quota_manager.check_quota("nvidia/model-a", cache_file=self.cache_file)
        self.assertTrue(avail_nv)
        avail_gq, _ = quota_manager.check_quota("groq/model-b", cache_file=self.cache_file)
        self.assertFalse(avail_gq)

        # Clear all
        quota_manager.clear_cache(provider=None, cache_file=self.cache_file)
        avail_all, _ = quota_manager.check_quota("groq/model-b", cache_file=self.cache_file)
        self.assertTrue(avail_all)


if __name__ == "__main__":
    unittest.main()
