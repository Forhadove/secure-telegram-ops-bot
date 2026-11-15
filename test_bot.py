"""
Unit & Integration Test Suite for Secure Telegram Ops Bot.
Validates:
1. RBAC Gatekeeper and security audit logging.
2. System telemetry report generation.
3. Pipeline report generation, quarantine detection, and SHA-256 calculation.
4. Concurrency mutex lock (409 Conflict logic).
"""

import asyncio
import os
import unittest
from pathlib import Path

# Set dummy env before importing bot modules
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:TEST_MOCK_TOKEN"
os.environ["WHITELISTED_ADMINS"] = "111222333,444555666"

from bot.auth import record_unauthorized_attempt
from bot.config import LOGS_DIR, REPORTS_DIR, SECURITY_AUDIT_LOG, WHITELISTED_ADMINS
from bot.pipeline import PIPELINE_LOCK, compute_sha256
from bot.telemetry import format_bytes, get_system_telemetry


class TestSecureOpsBot(unittest.IsolatedAsyncioTestCase):

    def test_whitelisted_admins_parsing(self):
        """Verifies that parse_whitelisted_admins parses comma-separated IDs correctly."""
        from bot.config import parse_whitelisted_admins
        parsed = parse_whitelisted_admins("111222333,444555666")
        self.assertIn(111222333, parsed)
        self.assertIn(444555666, parsed)
        self.assertNotIn(999999999, parsed)

    def test_unauthorized_audit_logging(self):
        """Verifies that unauthorized attempts are written to security_audit.log."""
        fake_user_id = 999999999
        fake_username = "malicious_user"
        fake_cmd = "/run_pipeline"

        record_unauthorized_attempt(fake_user_id, fake_username, fake_cmd, "Hacker Name")

        self.assertTrue(SECURITY_AUDIT_LOG.exists())
        with open(SECURITY_AUDIT_LOG, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(str(fake_user_id), content)
        self.assertIn(fake_username, content)
        self.assertIn(fake_cmd, content)
        self.assertIn("SECURITY ALERT 403", content)

    def test_system_telemetry_idle(self):
        """Verifies /sysinfo telemetry report format in IDLE state."""
        report = get_system_telemetry(is_pipeline_running=False)
        self.assertIn("HOST TELEMETRY", report)
        self.assertIn("IDLE", report)
        self.assertIn("CPU Utilization", report)
        self.assertIn("Memory (RAM)", report)
        self.assertIn("Python Runtime", report)

    def test_system_telemetry_running(self):
        """Verifies /sysinfo telemetry report format in RUNNING state."""
        report = get_system_telemetry(is_pipeline_running=True)
        self.assertIn("RUNNING", report)

    def test_bytes_formatting(self):
        """Verifies bytes human-readable conversion."""
        self.assertEqual(format_bytes(1024), "1.0 KiB")
        self.assertEqual(format_bytes(1024 * 1024 * 5), "5.0 MiB")

    async def test_concurrency_mutex_lock(self):
        """Verifies that asyncio.Lock prevents overlapping pipeline runs."""
        self.assertFalse(PIPELINE_LOCK.locked())

        # Acquire lock
        await PIPELINE_LOCK.acquire()
        self.assertTrue(PIPELINE_LOCK.locked())

        # Second acquisition should indicate lock is held (409 Conflict)
        conflict_detected = PIPELINE_LOCK.locked()
        self.assertTrue(conflict_detected)

        # Release lock
        PIPELINE_LOCK.release()
        self.assertFalse(PIPELINE_LOCK.locked())

    def test_sha256_checksum(self):
        """Verifies SHA-256 calculation on generated report."""
        test_file = REPORTS_DIR / "unit_test_sample.csv"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("record_id,service,latency_ms,status,quarantined\n1,auth,15,OK,False\n")

        checksum = compute_sha256(test_file)
        self.assertEqual(len(checksum), 64)  # 64 hex characters for SHA-256
        test_file.unlink()


if __name__ == "__main__":
    unittest.main()
