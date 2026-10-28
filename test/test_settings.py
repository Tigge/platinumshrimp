import unittest

from utils.settings import validate_settings


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "nickname": "bot",
            "realname": "Test Bot",
            "username": "bot",
            "servers": {"test": {"host": "irc.example.net", "port": 6667}},
            "plugins": {"test": {}},
        }

    def test_validates_default_watchdog_configuration(self):
        self.assertTrue(validate_settings(self.settings))

    def test_rejects_invalid_watchdog_timeout(self):
        self.settings["plugin_watchdog"] = {"timeout_seconds": 1}
        self.assertFalse(validate_settings(self.settings))

    def test_rejects_non_finite_watchdog_timeout(self):
        self.settings["plugin_watchdog"] = {"timeout_seconds": float("nan")}
        self.assertFalse(validate_settings(self.settings))

    def test_rejects_negative_restart_limit(self):
        self.settings["plugin_watchdog"] = {"max_restarts": -1}
        self.assertFalse(validate_settings(self.settings))

    def test_accepts_configured_watchdog(self):
        self.settings["plugin_watchdog"] = {
            "timeout_seconds": 15,
            "max_restarts": 5,
        }
        self.assertTrue(validate_settings(self.settings))


if __name__ == "__main__":
    unittest.main()
