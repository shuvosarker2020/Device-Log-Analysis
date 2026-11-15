import unittest
from app.config import cfg
from app.core.security import is_ip_allowed
from app.api.routes import update_security, SecurityConfigRequest

class TestSecurityIPWhitelist(unittest.TestCase):
    def setUp(self):
        # Reset security config to defaults
        cfg.update_security({
            "enable_ip_whitelist": False,
            "allowed_device_ips": []
        })

    def tearDown(self):
        # Reset back to non-blocking
        cfg.update_security({
            "enable_ip_whitelist": False,
            "allowed_device_ips": []
        })

    def test_whitelist_disabled_allows_all(self):
        self.assertTrue(is_ip_allowed("10.0.0.1"))
        self.assertTrue(is_ip_allowed("192.168.1.1"))
        self.assertTrue(is_ip_allowed("203.0.113.5"))

    def test_whitelist_enabled_exact_ip_and_cidr(self):
        cfg.update_security({
            "enable_ip_whitelist": True,
            "allowed_device_ips": ["10.100.1.5", "192.168.0.0/16"]
        })

        # Exact match
        self.assertTrue(is_ip_allowed("10.100.1.5"))

        # CIDR subnet match
        self.assertTrue(is_ip_allowed("192.168.1.100"))
        self.assertTrue(is_ip_allowed("192.168.254.1"))

        # Loopback always allowed
        self.assertTrue(is_ip_allowed("127.0.0.1"))

        # Not allowed
        self.assertFalse(is_ip_allowed("10.100.1.6"))
        self.assertFalse(is_ip_allowed("172.16.0.1"))
        self.assertFalse(is_ip_allowed("203.0.113.1"))

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
