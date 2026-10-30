import unittest
import asyncio
from app.parsers.engine import parser_engine
from app.analyzer.engine import analyzer_engine
from app.database.db import init_db
from app.database.repository import repository
from app.simulator.log_generator import simulate_batch

class TestNetLogIQ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_cisco_parser(self):
        msg = "<187>Oct 15 11:20:10 Cisco-ASR9k: %SYS-5-RELOAD: Reload requested by vty0 (user admin)"
        log = parser_engine.parse(msg, "10.100.1.1")
        self.assertEqual(log.vendor, "Cisco")
        self.assertEqual(log.hostname, "Cisco-ASR9k")
        self.assertEqual(log.severity, 5)

        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "REBOOT")
        self.assertTrue(log.is_alert)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.category, "REBOOT")

    def test_cisco_psu_issue(self):
        msg = "<185>Oct 15 11:21:05 Dist-SW1: %ENVMON-1-POWER_SUPPLY: Power supply 1 failed! Redundant power lost"
        log = parser_engine.parse(msg, "10.100.1.2")
        self.assertEqual(log.vendor, "Cisco")
        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "POWER_SUPPLY")
        self.assertTrue(log.is_alert)
        self.assertIsNotNone(alert)

    def test_huawei_parser_and_reboot(self):
        msg = "<186>Oct 15 2026 11:25:00 Huawei-NE40E %%01SYS/2/REBOOT(l)[15]: System is going to reboot by admin."
        log = parser_engine.parse(msg, "10.100.2.1")
        self.assertEqual(log.vendor, "Huawei")
        self.assertEqual(log.hostname, "Huawei-NE40E")
        self.assertEqual(log.severity, 2)

        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "REBOOT")
        self.assertTrue(log.is_alert)

    def test_huawei_psu_issue(self):
        msg = "<185>Oct 15 2026 11:26:10 Huawei-CE6800 %%01DEVM/1/POWER_OFF(l)[12]: The power supply 1 was powered off."
        log = parser_engine.parse(msg, "10.100.2.2")
        self.assertEqual(log.vendor, "Huawei")
        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "POWER_SUPPLY")
        self.assertTrue(log.is_alert)

    def test_huawei_cpu_overload(self):
        msg = "<188>Oct 15 2026 11:27:00 Huawei-S5700 %%01SYSTEM/4/CPU_OVERLOAD(l)[20]: CPU usage exceeds the threshold (94% > 80%)."
        log = parser_engine.parse(msg, "10.100.2.3")
        self.assertEqual(log.vendor, "Huawei")
        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "HIGH_CPU")
        self.assertTrue(log.is_alert)

    def test_juniper_parser_and_psu(self):
        msg = "<185>Oct 15 11:30:00 Juniper-MX960 chassism[2841]: CHASSISD_POWER_SUPPLY_FAILED: Power Supply 0 failure"
        log = parser_engine.parse(msg, "10.100.3.1")
        self.assertEqual(log.vendor, "Juniper")
        self.assertEqual(log.hostname, "Juniper-MX960")
        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "POWER_SUPPLY")
        self.assertTrue(log.is_alert)

    def test_zte_parser_and_reboot(self):
        msg = "<186>Oct 15 11:35:00 ZTE-C300 %SYS-2-RELOAD: System is reloading by command line."
        log = parser_engine.parse(msg, "10.100.4.1")
        self.assertEqual(log.vendor, "ZTE")
        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "REBOOT")
        self.assertTrue(log.is_alert)

    def test_nokia_parser_and_psu(self):
        msg = "<185>Oct 15 11:38:00 Nokia-7750SR SYSTEM-CRITICAL-1002: Base Chassis Power Supply 1 Failed or Removed"
        log = parser_engine.parse(msg, "10.100.5.1")
        self.assertEqual(log.vendor, "Nokia")
        self.assertEqual(log.hostname, "Nokia-7750SR")
        log, alert = analyzer_engine.analyze(log)
        self.assertEqual(log.event_category, "POWER_SUPPLY")
        self.assertTrue(log.is_alert)

    def test_db_save_and_analytics(self):
        async def run_batch():
            return await simulate_batch(count=10)

        results = asyncio.run(run_batch())
        self.assertEqual(len(results), 10)

        metrics = repository.get_summary_metrics()
        self.assertGreater(metrics["total_logs"], 0)
        self.assertGreater(metrics["total_devices"], 0)

        devices = repository.get_device_analytics(limit=5)
        self.assertTrue(len(devices) > 0)

        severities = repository.get_severity_analytics()
        self.assertTrue(len(severities) > 0)

        categories = repository.get_error_category_analytics()
        self.assertTrue(len(categories) > 0)

if __name__ == "__main__":
    unittest.main()
