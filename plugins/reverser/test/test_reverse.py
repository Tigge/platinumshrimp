import unittest

from reverser import Reverser

__author__ = 'sebbz'


class FormatTestCase(unittest.TestCase):

    def test_reverse(self):
        message = Reverser._reverse_string("sirap")
        self.assertEqual(message, "paris")
