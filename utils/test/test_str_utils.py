from twisted.trial import unittest

from utils import str_utils

class TestStrUtils(unittest.TestCase):
    def test_equal_number_of_parameters(self):
        self.assertEqual(str_utils.split("a b c", " ", 3), ["a", "b", "c"])

    def test_more_parameters_than_limit(self):
        self.assertEqual(str_utils.split("a b c d", " ", 3), ["a", "b", "c d"])

    def test_less_parameters_than_limit(self):
        self.assertEqual(str_utils.split("a b", " ", 3), ["a", "b", ""])

