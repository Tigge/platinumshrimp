import json
import os
import unittest
from unittest.mock import Mock, ANY, call, patch
import requests_mock
from dateutil import relativedelta
from datetime import datetime
import time

#from trakt import API_ACTIVITY
#from trakt import API_URL
from trakt import Trakt
import api


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

ACTIVITY_TEMPLATE_1 = {
    "watched_at": "",
    "action": "watch",
    "episode": {
        "season": -1,
        "number": -1,
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


class FormatTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def test_watch_episode(self):
        with open(os.path.join(self.dir, "format", "test_format_watch_episode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User watched 'Marvel's Agents of S.H.I.E.L.D.', "
                                      "S01E11 'The Magical Place' http://www.trakt.tv/episodes/74015")

    def test_scrobble_episode(self):
        with open(os.path.join(self.dir, "format", "test_format_scrobble_episode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User scrobbled 'The Simpsons', "
                                      "S26E10 'The Man Who Came to Be Dinner' http://www.trakt.tv/episodes/1390653")

    def test_watch_movie(self):
        with open(os.path.join(self.dir, "format", "test_format_watch_movie.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User watched 'Soul Kitchen' (2009) http://www.trakt.tv/movies/19911")

    def test_utf8(self):
        with open(os.path.join(self.dir, "format", "test_format_unicode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User watched 'The Walking Dead \u263b', "
                                      "S05E09 'What Happened and What\u2019s Going On \u263b' "
                                      "http://www.trakt.tv/episodes/998958")


class StartTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()

    @patch('trakt.datetime')
    def test_user_setup(self, mock_datetime):
        data_users = ['adam', 'dave', 'sue', 'eva']
        user_json = {'users': data_users, 'key': 'fakekey'}
        mock_datetime.datetime.now = lambda **_: "fakedate"
        self.trakt.started(json.dumps(user_json))
        self.assertEqual(self.trakt.users, dict(map(lambda u: (u, {"last_sync_episodes": "fakedate", "last_sync_movies": "fakedate"}), data_users)))


class UpdateTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()
        self.trakt.started('{"key": "[FAKEKEY]", "users": ["adam"]}')

    def setupMocks(self, fetch_side_effect, summary_side_effect=None):
        fetch = Mock(side_effect=fetch_side_effect)
        echo = Mock()
        summary = Mock(side_effect=summary_side_effect)

        self.trakt.fetch_new_activities = fetch
        self.trakt.echo = echo
        self.trakt.create_activity_summary = summary

        return fetch, echo, summary

    # def test_no_entries(self):
    #     mock_fetch, mock_echo, _ = self.setupMocks(lambda _, __: ([], None))
    #
    #     self.trakt.update_user("adam")
    #
    #     self.assertFalse("last_sync_episodes" in self.trakt.users["adam"])
    #     self.assertFalse("last_sync_movies" in self.trakt.users["adam"])
    #     self.assertFalse(mock_echo.called, "No message should be sent if no new activies are present")
    #
    # def test_sets_last_sync_on_first_load(self):
    #     mock_fetch, mock_echo, _ = self.setupMocks((lambda url, sync: (
    #         [], api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"])) if "episodes" in url else ([], None)))
    #
    #     self.trakt.update_user("adam")
    #
    #     #self.assertTrue(mock_fetch.call_args_list == [call(ANY, None), call(ANY, None)])
    #     self.assertTrue("last_sync_episodes" in self.trakt.users["adam"])
    #     self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
    #                      api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
    #     #self.assertFalse("last_sync_movies" in self.trakt.users["adam"])
    #     self.assertFalse(mock_echo.called, "No message should be sent if no last_sync had been set before")

    @patch("trakt.Trakt.format_activity")
    def test_single_episode(self, format_):
        user_name = "adam"

        def mock_fetch_new_activities(url, typ, func):
            if typ != "episodes":
                return []
            else:
                return [ACTIVITY_PRESET_EPISODE_1]

        summary = {"action": "WOOT", "series": [{"data": "dummy"}]}
        summary_return = lambda _: [summary]
        mock_fetch, mock_echo, _ = self.setupMocks(mock_fetch_new_activities, summary_return)

        self.trakt.trakt.users_history = summary_return

        self.trakt.users["adam"]["last_sync_episodes"] = api.Trakt.get_date(
                ACTIVITY_PRESET_EPISODE_1["watched_at"]) - relativedelta.relativedelta(days=1)

        self.trakt.update_user(user_name)

        self.assertTrue(mock_echo.called, "A message should have been sent")
        format_.assert_called_once_with(summary["series"][0], user_name, summary["action"])
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))

    def test_no_new_episodes(self):
        mock_fetch, mock_echo, _ = self.setupMocks(
            lambda url, typ, func: [ACTIVITY_PRESET_EPISODE_1],
            lambda _: [])
        self.trakt.users["adam"]["last_sync_episodes"] = api.Trakt.get_date("2013-03-31T09:28:53.000Z")

        self.trakt.update_user("adam")

        self.assertFalse(mock_echo.called, "No message should be sent if no new activities were found")
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))

    def test_new_activity_both_types(self):
        fetch_return = lambda url, typ, func: [ACTIVITY_PRESET_EPISODE_1] if typ == "episodes" else [ACTIVITY_PRESET_MOVIE_1]
        summary_episode = {"action": "WOOT", "series": [{"data": "dummy_episode2000"}]}
        summary_movie = {"action": "WOOT", "series": [{"data": "dummy_movie1000"}]}
        summary_return = lambda activities: [summary_episode] if activities == [ACTIVITY_PRESET_EPISODE_1] else [
            summary_movie]
        mock_fetch, mock_echo, _ = self.setupMocks(fetch_return, summary_return)
        self.trakt.users["adam"]["last_sync_episodes"] = api.Trakt.get_date("2013-03-31T09:28:53.000Z")
        self.trakt.users["adam"]["last_sync_movies"] = api.Trakt.get_date("2013-03-31T09:28:53.000Z")

        self.trakt.update_user("adam")

        self.assertEqual(mock_echo.call_count, 2)
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
        self.assertEqual(self.trakt.users["adam"]["last_sync_movies"],
                         api.Trakt.get_date(ACTIVITY_PRESET_MOVIE_1["watched_at"]))


class SummaryTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def setUp(self):
        self.trakt = Trakt()
        self.trakt.started('{"key": "[FAKEKEY]", "users": ["adam"]}')

    def create_activity(self, action, title, year, season, number):
        return {
            "action": action,
            "episode": {
                "season": season,
                "number": number
            },
            "show": {
                "title": title,
                "year": year
            }
        }

    def test_empty_list(self):
        result = self.trakt.create_activity_summary([])
        self.assertEqual(result, [])

    def test_single_activity(self):
        result = self.trakt.create_activity_summary([ACTIVITY_PRESET_EPISODE_1])

        self.assertTrue(len(result) == 1, "Should have gotten one show back. Got: %s" % len(result))
        res = result[0]
        res_show = res["show"]
        res_episodes = res["episodes"]
        self.assertTrue(res["action"] == ACTIVITY_PRESET_EPISODE_1["action"], "Wrong action. Value: %s" % result[0]["action"])
        self.assertEqual(res_show["title"] == ACTIVITY_PRESET_EPISODE_1["show"]["title"])
        self.assertEqual(res_show["year"] == ACTIVITY_PRESET_EPISODE_1["show"]["year"])
        self.assertEqual(res_episodes, [(2, 3)])

    def test_single_season_range(self):
        list_ = []
        result = self.trakt.create_activity_summary()
        