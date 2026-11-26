import unittest
import asyncio
from app.database.db import init_db
from app.api.routes import (
    get_summary, get_severity_stats, get_device_stats,
    get_ip_stats, get_category_stats, get_logs, get_alerts,
    ingest_log, IngestRequest
)

class TestAPIDirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_direct_summary(self):
        res = get_summary()
        self.assertIn("total_logs", res)
        self.assertIn("total_alerts", res)

    def test_direct_analytics(self):
        devs = get_device_stats(limit=10)
        self.assertIsInstance(devs, list)
        ips = get_ip_stats(limit=10)
        self.assertIsInstance(ips, list)
        sevs = get_severity_stats()
        self.assertIsInstance(sevs, list)
        cats = get_category_stats()
        self.assertIsInstance(cats, list)

    def test_direct_logs(self):
        res = get_logs(limit=10, offset=0)
        self.assertIn("logs", res)
        self.assertIn("total", res)

    def test_direct_alerts(self):
        alerts = get_alerts()
        self.assertIsInstance(alerts, list)

    def test_direct_ingest(self):
        async def do_ingest():
            req = IngestRequest(
                message="<185>Oct 15 11:21:05 Huawei-SW01 %%01DEVM/1/POWER_OFF(l)[12]: The power supply 1 was powered off.",
                source_ip="10.200.5.1"
            )
            return await ingest_log(req)

        res = asyncio.run(do_ingest())
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["log"]["vendor"], "Huawei")
        self.assertEqual(res["log"]["event_category"], "POWER_SUPPLY")
        self.assertTrue(res["log"]["is_alert"])

    def test_delete_device_and_all_logs(self):
        from app.api.routes import delete_device_logs, delete_all_logs
        async def seed():
            await ingest_log(IngestRequest(message="<187>Oct 15 11:20:10 SW-A: %SYS-5-RELOAD: Reload", source_ip="10.10.1.1"))
            await ingest_log(IngestRequest(message="<187>Oct 15 11:20:10 SW-B: %SYS-5-RELOAD: Reload", source_ip="10.10.1.2"))

        asyncio.run(seed())
        res_dev = delete_device_logs(hostname=None, source_ip="10.10.1.1")
        self.assertEqual(res_dev["status"], "success")
        self.assertGreaterEqual(res_dev["deleted_logs"], 1)

        res_all = delete_all_logs()
        self.assertEqual(res_all["status"], "success")
        summary = get_summary()
        self.assertEqual(summary["total_logs"], 0)
        self.assertEqual(summary["total_devices"], 0)

if __name__ == "__main__":
    unittest.main()
