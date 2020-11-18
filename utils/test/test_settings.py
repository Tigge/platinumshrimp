import unittest

from utils import settings


class TestSettings(unittest.TestCase):
    def test_validate_default_settings(self):
        setting = settings.DEFAULT_SETTINGS
        self.assertTrue(settings.validate_settings(setting))
