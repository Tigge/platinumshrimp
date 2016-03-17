import json
import os
import unittest

from unittest.mock import patch
from unittest.mock import Mock

import requests_mock
from dateutil import relativedelta

from plugins.trakt.trakt import Trakt
from plugins.trakt.trakt import API_ACTIVITY
from plugins.trakt.trakt import API_URL


class StubResponse(object):
    status_code = 200
    mock_response = ""

    def __init__(self, status_code, response):
        self.status_code = status_code
        self.mock_response = response

    def json(self):
        if hasattr(self.mock_response, '__call__'):
            return self.mock_response()
        else:
            return self.mock_response

""" Presets copied from Trakt's API  """

ACTIVITY_PRESET_EPISODE_1 = {
    "watched_at": "2014-03-31T09:28:53.000Z",
    "action": "watch",
    "episode": {
        "season": 2,
        "number": 3,
        "title": "Beauty Pageant",
        "ids": {
            "trakt": 253,
            "tvdb": 1088041,
            "imdb": None,
            "tmdb": 397642,
            "tvrage": None
        }
    },
    "show": {
        "title": "Parks and Recreation",
        "year": 2009,
        "ids": {
            "trakt": 4,
            "slug": "parks-and-recreation",
            "tvdb": 84912,
            "imdb": "tt1266020",
            "tmdb": 8592,
            "tvrage": 21686
        }
    }
}

ACTIVITY_PRESET_MOVIE_1 = {
    "watched_at": "2014-03-31T09:28:53.000Z",
    "action": "scrobble",
    "movie": {
        "title": "The Dark Knight",
        "year": 2008,
        "ids": {
            "trakt": 4,
            "slug": "the-dark-knight-2008",
            "imdb": "tt0468569",
            "tmdb": 155
        }
    }
}


class FormatTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def test_watch_episode(self):
        with open(os.path.join(self.dir, "test_format_watch_episode.json")) as f:
            message = Trakt.format_activity(json.load(f), "User")
            self.assertEqual(message, "User watched 'Marvel's Agents of S.H.I.E.L.D.', "
                                      "S01E11 'The Magical Place' http://www.trakt.tv/episodes/74015")

    def test_scrobble_episode(self):
        with open(os.path.join(self.dir, "test_format_scrobble_episode.json")) as f:
            message = Trakt.format_activity(json.load(f), "User")
            self.assertEqual(message, "User scrobbled 'The Simpsons', "
                                      "S26E10 'The Man Who Came to Be Dinner' http://www.trakt.tv/episodes/1390653")

    def test_watch_movie(self):
        with open(os.path.join(self.dir, "test_format_watch_movie.json")) as f:
            message = Trakt.format_activity(json.load(f), "User")
            self.assertEqual(message, "User watched 'Soul Kitchen' (2009) http://www.trakt.tv/movies/19911")

    def test_utf8(self):
        with open(os.path.join(self.dir, "test_format_unicode.json")) as f:
            message = Trakt.format_activity(json.load(f), "User")
            self.assertEqual(message, "User watched 'The Walking Dead \u263b', "
                                      "S05E09 'What Happened and What\u2019s Going On \u263b' "
                                      "http://www.trakt.tv/episodes/998958")


class GetTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()
        self.trakt.settings["key"] = "thekey"

    def raise_(self, ex):
        raise ex

    @requests_mock.mock()
    def test_get_valid(self, mock_requests):
        response = "{\"movie_id\": 123}"
        mock_requests.get(API_URL, text=response)
        res = self.trakt.get("")
        self.assertEqual(res, {"movie_id": 123})

    @requests_mock.mock()
    def test_get_error_code(self, mock_requests):
        mock_requests.get(API_URL, text="", status_code=400)
        self.assertRaises(Exception, self.trakt.get, "")

    @requests_mock.mock()
    def test_get_error_json(self, mock_requests):
        mock_requests.get(API_URL, text="{\"broken_json\": \"blä")
        self.assertEqual(self.trakt.get(""), [])


class StartTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()

    @patch('plugins.trakt.trakt.json')
    def test_user_setup(self, mock_json):
        data_users = ['adam', 'dave', 'sue', 'eva']
        user_json = {'users': data_users}
        mock_json.loads.return_value = user_json
        self.trakt.started("")
        self.assertEqual(self.trakt.users, dict(map(lambda u: (u, {}), data_users)))


class UpdateTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()
        self.trakt.users = {"adam": {}}

    def test_no_entries(self):
        mock_get = Mock(return_value=[])
        self.trakt.get = mock_get

        self.trakt.update_user("adam")

        mock_get.assert_any_call(API_ACTIVITY.format("adam", "episodes"))
        mock_get.assert_any_call(API_ACTIVITY.format("adam", "movies"))
        self.assertFalse("last_sync_episodes" in self.trakt.users["adam"])
        self.assertFalse("last_sync_movies" in self.trakt.users["adam"])

    def test_sets_last_sync_on_first_load(self):
        mock_get = Mock(side_effect=(lambda url: [ACTIVITY_PRESET_EPISODE_1] if "episodes" in url else []))
        self.trakt.get = mock_get

        self.trakt.update_user("adam")

        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
        self.assertFalse("last_sync_movies" in self.trakt.users["adam"])

    def test_single_episode(self):
        mock_get = Mock(side_effect=(lambda url: [ACTIVITY_PRESET_EPISODE_1] if "episodes" in url else []))
        self.trakt.users["adam"]["last_sync_episodes"] = Trakt.get_date(
            ACTIVITY_PRESET_EPISODE_1["watched_at"]) - relativedelta.relativedelta(days=1)
        mock_echo = Mock()
        self.trakt.get = mock_get
        self.trakt.echo = mock_echo

        self.trakt.update_user("adam")

        self.assertTrue(mock_echo.called)
        self.assertEqual(mock_echo.call_args[0], (Trakt.format_activity(ACTIVITY_PRESET_EPISODE_1, "adam"),))

    def test_no_new_episodes(self):
        mock_get = Mock(side_effect=(lambda url: [ACTIVITY_PRESET_EPISODE_1] if "episodes" in url else []))
        self.trakt.users["adam"]["last_sync_episodes"] = Trakt.get_date(
            ACTIVITY_PRESET_EPISODE_1["watched_at"]) + relativedelta.relativedelta(days=1)
        mock_echo = Mock()
        self.trakt.get = mock_get
        self.trakt.echo = mock_echo

        self.trakt.update_user("adam")

        self.assertFalse(mock_echo.called)

    def test_new_activity_both_types(self):
        mock_get = Mock(
            side_effect=(lambda url: [ACTIVITY_PRESET_EPISODE_1] if "episodes" in url else [ACTIVITY_PRESET_MOVIE_1]))
        self.trakt.users["adam"]["last_sync_episodes"] = Trakt.get_date("2013-03-31T09:28:53.000Z")
        self.trakt.users["adam"]["last_sync_movies"] = Trakt.get_date("2013-03-31T09:28:53.000Z")
        mock_echo = Mock()
        self.trakt.get = mock_get
        self.trakt.echo = mock_echo

        self.trakt.update_user("adam")

        self.assertEqual(mock_echo.call_count, 2)
        mock_echo.assert_any_call(Trakt.format_activity(ACTIVITY_PRESET_EPISODE_1, "adam"))
        mock_echo.assert_any_call(Trakt.format_activity(ACTIVITY_PRESET_MOVIE_1, "adam"))
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
        self.assertEqual(self.trakt.users["adam"]["last_sync_movies"],
                         Trakt.get_date(ACTIVITY_PRESET_MOVIE_1["watched_at"]))
