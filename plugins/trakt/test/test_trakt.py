import json
import os
import unittest
from unittest.mock import Mock, patch

import requests_mock
from dateutil import relativedelta

from plugins.trakt.trakt import Trakt
from plugins.trakt import api


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
            "tvrage": None,
        },
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
            "tvrage": 21686,
        },
    },
}

ACTIVITY_PRESET_SERIES_1 = {
    "number": 2,
    "ids": {"trakt": 18965, "tvdb": 83141, "tmdb": 18456, "tvrage": None},
    "rating": 8.49162,
    "votes": 179,
    "episode_count": 24,
    "aired_episodes": 24,
    "overview": "...",
    "first_aired": "2009-09-18T00:00:00.000Z",
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
            "tmdb": 155,
        },
    },
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
            "tvrage": None,
        },
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
            "tvrage": 21686,
        },
    },
}


class FormatTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def test_watch_episode(self):
        with open(
            os.path.join(self.dir, "format", "test_format_watch_episode.json")
        ) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(
                message,
                "User watched 'Marvel's Agents of S.H.I.E.L.D.', "
                "S01E11 'The Magical Place' https://www.trakt.tv/search/trakt/74015?id_type=episode",
            )

    def test_scrobble_episode(self):
        with open(
            os.path.join(self.dir, "format", "test_format_scrobble_episode.json")
        ) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(
                message,
                "User scrobbled 'The Simpsons', "
                "S26E10 'The Man Who Came to Be Dinner' https://www.trakt.tv/search/trakt/1390653?id_type=episode",
            )

    def test_watch_movie(self):
        with open(
            os.path.join(self.dir, "format", "test_format_watch_movie.json")
        ) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(
                message,
                "User watched 'Soul Kitchen' (2009) https://www.trakt.tv/search/trakt/19911?id_type=movie",
            )

    def test_utf8(self):
        with open(os.path.join(self.dir, "format", "test_format_unicode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(
                message,
                "User watched 'The Walking Dead \u263b', "
                "S05E09 'What Happened and What\u2019s Going On \u263b' "
                "https://www.trakt.tv/search/trakt/998958?id_type=episode",
            )


class StartTestCase(unittest.TestCase):
    def setUp(self):
        self.trakt = Trakt()

    @patch("plugins.trakt.trakt.datetime")
    def test_user_setup(self, mock_datetime):
        data_users = ["adam", "dave", "sue", "eva"]
        user_json = {"users": data_users, "key": "fakekey"}
        mock_datetime.datetime.now = lambda **_: "fakedate"
        self.trakt.started(json.dumps(user_json))
        self.assertEqual(
            self.trakt.users,
            dict(
                map(
                    lambda u: (
                        u,
                        {
                            "last_sync_episodes": "fakedate",
                            "last_sync_movies": "fakedate",
                        },
                    ),
                    data_users,
                )
            ),
        )


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

    @patch("plugins.trakt.trakt.Trakt.format_activity")
    def test_single_episode(self, format_):
        user_name = "adam"

        def mock_fetch_new_activities(url, typ, func):
            if typ != "episodes":
                return []
            else:
                return [ACTIVITY_PRESET_EPISODE_1]

        summary = {"action": "WOOT", "series": [{"data": "dummy"}]}
        summary_return = lambda _: [summary]
        mock_fetch, mock_echo, _ = self.setupMocks(
            mock_fetch_new_activities, summary_return
        )

        self.trakt.trakt.users_history = summary_return

        self.trakt.users["adam"]["last_sync_episodes"] = api.Trakt.get_date(
            ACTIVITY_PRESET_EPISODE_1["watched_at"]
        ) - relativedelta.relativedelta(days=1)

        self.trakt.update_user(user_name)

        self.assertTrue(mock_echo.called, "A message should have been sent")
        format_.assert_called_once_with(summary, user_name, summary["action"])
        self.assertEqual(
            self.trakt.users["adam"]["last_sync_episodes"],
            api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]),
        )

    def test_no_new_episodes(self):
        mock_fetch, mock_echo, _ = self.setupMocks(
            lambda url, typ, func: [ACTIVITY_PRESET_EPISODE_1]
            if typ == "episodes"
            else [],
            lambda _: [],
        )
        self.trakt.users["adam"]["last_sync_episodes"] = api.Trakt.get_date(
            "2013-03-31T09:28:53.000Z"
        )

        self.trakt.update_user("adam")

        self.assertFalse(
            mock_echo.called,
            "No message should be sent if no new activities were found",
        )
        self.assertEqual(
            self.trakt.users["adam"]["last_sync_episodes"],
            api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]),
        )

    @requests_mock.mock()
    def test_new_activity_both_types(self, mock_requests):
        mock_requests.get(
            "/users/adam/history/episodes", text=json.dumps([ACTIVITY_PRESET_EPISODE_1])
        )
        mock_requests.get(
            "/users/adam/history/movies", text=json.dumps([ACTIVITY_PRESET_MOVIE_1])
        )
        mock_requests.get(
            "/shows/4/seasons", text=json.dumps([ACTIVITY_PRESET_SERIES_1])
        )
        mock_requests.get("/users/adam/ratings/movies", text="[]")
        self.trakt.echo = Mock()

        self.trakt.users["adam"]["last_sync_episodes"] = api.Trakt.get_date(
            "2013-03-31T09:28:53.000Z"
        )
        self.trakt.users["adam"]["last_sync_movies"] = api.Trakt.get_date(
            "2013-03-31T09:28:53.000Z"
        )

        self.trakt.update_user("adam")

        self.trakt.echo.assert_any_call(
            "adam watched 'Parks and Recreation', S02E03 'Beauty Pageant' https://www.trakt.tv/search/trakt/253?id_type=episode"
        )
        self.trakt.echo.assert_any_call(
            "adam scrobbled 'The Dark Knight' (2008) https://www.trakt.tv/search/trakt/4?id_type=movie"
        )
        self.assertEqual(self.trakt.echo.call_count, 2)

        self.assertEqual(
            self.trakt.users["adam"]["last_sync_episodes"],
            api.Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]),
        )
        self.assertEqual(
            self.trakt.users["adam"]["last_sync_movies"],
            api.Trakt.get_date(ACTIVITY_PRESET_MOVIE_1["watched_at"]),
        )


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
            "episode": {"season": season, "number": number},
            "show": {"title": title, "year": year},
        }

    def test_empty_list(self):
        result = self.trakt.create_activity_summary([])
        self.assertEqual(result, [])

    def test_single_episode(self):
        with open(
            os.path.join(self.dir, "summaries", "single_episode_episodes.json")
        ) as episodes_json, open(
            os.path.join(self.dir, "summaries", "single_episode_show.json")
        ) as show_json:
            self.trakt.trakt.seasons_summary = Mock(return_value=json.load(show_json))
            result = self.trakt.create_activity_summary([json.load(episodes_json)[0]])

            self.assertTrue(
                len(result) == 1,
                "Should have gotten one show back. Got: %s" % len(result),
            )
            res = result[0]
            self.assertTrue(res["action"], "scrobble")
            self.assertEqual(res["show"]["title"], "CGP Grey")
            self.assertEqual(res["show"]["year"], 2011)
            self.assertEqual(len(res["seasons"]), 1)
            self.assertEqual(len(res["seasons"][2016]["episodes"]), 1)
            self.assertEqual(
                res["seasons"][2016]["episodes"][8]["title"],
                "The Simple Solution to Traffic",
            )

            self.assertEqual(
                Trakt.format_activity(result[0], "user", "watch"),
                "user watched 'CGP Grey', S2016E08 'The Simple Solution to Traffic' https://www.trakt.tv/search/trakt/2327792?id_type=episode",
            )

    def test_single_season(self):
        with open(
            os.path.join(self.dir, "summaries", "single_season_episodes.json")
        ) as fe:
            with open(
                os.path.join(self.dir, "summaries", "single_season_show.json")
            ) as fs:
                self.trakt.trakt.seasons_summary = Mock(return_value=json.load(fs))
                result = self.trakt.create_activity_summary(json.load(fe))
                self.assertTrue(
                    len(result) == 1,
                    "Should have gotten one show back. Got: %s" % len(result),
                )
                res = result[0]
                self.assertTrue(res["action"], "scrobble")
                self.assertEqual(res["show"]["title"], "The Cyanide & Happiness Show")
                self.assertEqual(res["show"]["year"], 2014)
                self.assertEqual(len(res["seasons"]), 1)
                self.assertEqual(len(res["seasons"][2]["episodes"]), 3)

                self.assertEqual(
                    Trakt.format_activity(result[0], "user", "watch"),
                    "user watched 'The Cyanide & Happiness Show' S02E05-E07 https://www.trakt.tv/search/trakt/117827?id_type=season",
                )

    def test_multiple_seasons(self):

        with open(
            os.path.join(self.dir, "summaries", "multiple_seasons_episodes.json")
        ) as episodes_json, open(
            os.path.join(self.dir, "summaries", "multiple_seasons_show.json")
        ) as shows_json:

            self.trakt.trakt.seasons_summary = Mock(return_value=json.load(shows_json))
            result = self.trakt.create_activity_summary(json.load(episodes_json))
            self.assertTrue(
                len(result) == 1,
                "Should have gotten one show back. Got: %s" % len(result),
            )
            res = result[0]

            # Verify season information
            self.assertTrue(res["action"], "scrobble")
            self.assertEqual(res["show"]["title"], "Silicon Valley")
            self.assertEqual(res["show"]["year"], 2014)
            self.assertEqual(len(res["seasons"]), 3)
            self.assertEqual(len(res["seasons"][1]["episodes"]), 8)
            self.assertEqual(len(res["seasons"][2]["episodes"]), 10)
            self.assertEqual(len(res["seasons"][3]["episodes"]), 10)

            self.assertEqual(
                Trakt.format_activity(result[0], "user", "watch"),
                "user watched 'Silicon Valley' S01E01-E08, S02E01-E10, S03E01-E10 https://www.trakt.tv/search/trakt/60157?id_type=show",
            )
