__author__ = 'sebbz'
import os

from twisted.trial import unittest

from plugins.reverser.reverser import Reverser


class FormatTestCase(unittest.TestCase):

    def test_reverse(self):
        message = Reverser._reverseString("sirap")
        self.assertEqual(message, "paris")
