import json
import os

from twisted.trial import unittest

from plugins.trakt.trakt import Trakt


class FormatTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = os.path.join("..", os.path.dirname(__file__))

    def test_watching_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_watching_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User is watching (3h 4m 19s) 'Modern Family' 'S03E07 Treehouse' http://trakt.tv/show/modern-family/season/3/episode/7")
