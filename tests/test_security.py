import unittest
from app.config import cfg
from app.core.security import is_ip_allowed
from app.api.routes import update_security, SecurityConfigRequest, cleanup_unauthorized_devices
from app.database.db import init_db
from app.database.repository import repository
from app.core.models import NormalizedLog

class TestSecurityIPWhitelist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls._orig_bind = cfg.get("server", "syslog_bind_ip", default="0.0.0.0")
        cls._orig_enabled = cfg.get("security", "enable_ip_whitelist", default=True)
        cls._orig_ips = cfg.get("security", "allowed_device_ips", default=[])

    @classmethod
    def tearDownClass(cls):
        cfg.set(["server", "syslog_bind_ip"], cls._orig_bind)
        cfg.update_security({
            "enable_ip_whitelist": cls._orig_enabled,
            "allowed_device_ips": cls._orig_ips
        })

    def test_whitelist_disabled_allows_all(self):
        cfg.update_security({"enable_ip_whitelist": False, "allowed_device_ips": []})
        self.assertTrue(is_ip_allowed("10.0.0.1", record_block=False))
        self.assertTrue(is_ip_allowed("138.68.40.90", record_block=False))

    def test_whitelist_enabled_empty_blocks_external(self):
        cfg.update_security({"enable_ip_whitelist": True, "allowed_device_ips": []})
        self.assertFalse(is_ip_allowed("138.68.40.90", record_block=False))
        self.assertFalse(is_ip_allowed("10.0.0.1", record_block=False))
        self.assertTrue(is_ip_allowed("127.0.0.1", record_block=False))

    def test_whitelist_enabled_exact_ip_cidr_and_wildcard(self):
        cfg.update_security({
            "enable_ip_whitelist": True,
            "allowed_device_ips": ["10.100.1.5", "192.168.0.0/16", "172.20.*"]
        })

        # Exact match
        self.assertTrue(is_ip_allowed("10.100.1.5", record_block=False))
        # IPv4-mapped IPv6 unwrap
        self.assertTrue(is_ip_allowed("::ffff:10.100.1.5", record_block=False))

        # CIDR subnet match
        self.assertTrue(is_ip_allowed("192.168.1.100", record_block=False))
        # Wildcard prefix match
        self.assertTrue(is_ip_allowed("172.20.5.12", record_block=False))

        # Unauthorized public/scanner IPs
        self.assertFalse(is_ip_allowed("138.68.40.90", record_block=False))
        self.assertFalse(is_ip_allowed("::ffff:138.68.40.90", record_block=False))
        self.assertFalse(is_ip_allowed("91.196.152.146", record_block=False))

    def test_cleanup_unauthorized_devices(self):
        cfg.update_security({
            "enable_ip_whitelist": True,
            "allowed_device_ips": ["10.100.0.0/16"]
        })
        # Insert an authorized log and an unauthorized scanner log
        repository.save_log(NormalizedLog(
            source_ip="10.100.1.10", hostname="Core-SW", vendor="Cisco",
            raw_message="test ok", clean_message="test ok"
        ))
        repository.save_log(NormalizedLog(
            source_ip="138.68.40.90", hostname="138.68.40.90", vendor="Generic",
            raw_message="scanner noise", clean_message="scanner noise"
        ))

        res = cleanup_unauthorized_devices()
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(res["deleted_devices"], 1)
        self.assertGreaterEqual(res["deleted_logs"], 1)

    def test_api_security_update(self):
        req = SecurityConfigRequest(
            syslog_bind_ip="10.20.30.40",
            enable_ip_whitelist=True,
            allowed_device_ips=["10.10.0.0/16", "172.20.1.1"]
        )
        res = update_security(req)
        self.assertEqual(res["status"], "success")
        self.assertEqual(cfg.get("server", "syslog_bind_ip"), "10.20.30.40")
        self.assertTrue(cfg.get("security", "enable_ip_whitelist"))
        self.assertEqual(cfg.get("security", "allowed_device_ips"), ["10.10.0.0/16", "172.20.1.1"])

if __name__ == "__main__":
    unittest.main()
