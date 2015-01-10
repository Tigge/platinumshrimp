import json
import os

from twisted.trial import unittest

from plugins.trakt.trakt import Trakt


class FormatTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = os.path.join("..", os.path.dirname(__file__))

    def test_watch_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_watch_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User watched 'Marvel's Agents of S.H.I.E.L.D.', S01E11 'The Magical Place' http://www.trakt.tv/episodes/74015")

    def test_scrobble_episode(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_scrobble_episode.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User scrobbled 'The Simpsons', S26E10 'The Man Who Came to Be Dinner' http://www.trakt.tv/episodes/1390653")

    def test_watch_movie(self):
        activity = json.load(open(os.path.join(self.dir, "test_format_watch_movie.json")))
        message = Trakt.format_activity(activity, "User")
        self.assertEqual(message, "User watched 'Soul Kitchen' (2009) http://www.trakt.tv/movies/19911")

