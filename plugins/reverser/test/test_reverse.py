__author__ = 'sebbz'
import os

from twisted.trial import unittest

from plugins.reverser.reverser import Reverser


class FormatTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = os.path.join("..", os.path.dirname(__file__))

    def test_reverse(self):
        message = Reverser._reverseString("sirap")
        self.assertEqual(message, "paris")
