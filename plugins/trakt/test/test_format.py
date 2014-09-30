import json
import os

from twisted.trial import unittest

from plugins.trakt.trakt import Trakt


class FormatTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = os.path.join("..", os.path.dirname(__file__))

#    def test_watching_episode(self):
#        activity = json.load(open(os.path.join(self.dir, "test_format_watching_episode.json")))
#        message = Trakt.format_activity(activity, "User")
#        self.assertEqual(message, "User is watching (3h 4m 19s) 'Modern Family' 'S03E07 Treehouse' http://trakt.tv/show/modern-family/season/3/episode/7")

    def test_scrobble_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_scrobble_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User scrobbled 'Covert Affairs' 'S02E11 The Wake-Up Bomb' http://trakt.tv/show/covert-affairs/season/2/episode/11")

    def test_checkin_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_checkin_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User checked in 'The Walking Dead' 'S02E01 What Lies Ahead' http://trakt.tv/show/the-walking-dead/season/2/episode/1")

    def test_seen_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_seen_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, None)

    def test_collection_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_collection_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, None)

    def test_rating_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_rating_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User rated (as 9) 'Dexter' 'S06E05 The Angel of Death' http://trakt.tv/show/dexter/season/6/episode/5")
