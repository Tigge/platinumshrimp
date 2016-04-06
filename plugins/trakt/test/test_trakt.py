import json
import os
import unittest

from unittest.mock import patch
from unittest.mock import Mock, ANY, call
import requests_mock
from dateutil import relativedelta
from datetime import datetime
import time

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

    def raise_(self, ex):
        raise ex

    def test_watch_episode(self):
        with open(os.path.join(self.dir, "test_format_watch_episode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User watched 'Marvel's Agents of S.H.I.E.L.D.', "
                                      "S01E11 'The Magical Place' http://www.trakt.tv/episodes/74015")

    def test_scrobble_episode(self):
        with open(os.path.join(self.dir, "test_format_scrobble_episode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User scrobbled 'The Simpsons', "
                                      "S26E10 'The Man Who Came to Be Dinner' http://www.trakt.tv/episodes/1390653")

    def test_watch_movie(self):
        with open(os.path.join(self.dir, "test_format_watch_movie.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
            self.assertEqual(message, "User watched 'Soul Kitchen' (2009) http://www.trakt.tv/movies/19911")

    def test_utf8(self):
        with open(os.path.join(self.dir, "test_format_unicode.json")) as f:
            activity = json.load(f)
            message = Trakt.format_activity(activity, "User", activity["action"])
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
        mock_requests.get(API_URL, text="{\"movie_id\": 123abc\"}") # note: missing quote
        res = self.trakt.get("")
        self.assertEqual(res, [])

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

    def setupMocks(self, fetch_side_effect, summary_side_effect=None):
        fetch = Mock(side_effect=fetch_side_effect)
        echo = Mock()
        summary = Mock(side_effect=summary_side_effect)

        self.trakt.fetch_new_activities = fetch
        self.trakt.echo = echo
        self.trakt.create_activity_summary = summary

        return (fetch, echo, summary)

    def test_no_entries(self):
        mock_fetch, mock_echo, _ = self.setupMocks(lambda _, __: ([], None))

        self.trakt.update_user("adam")

        self.assertFalse("last_sync_episodes" in self.trakt.users["adam"])
        self.assertFalse("last_sync_movies" in self.trakt.users["adam"])
        self.assertFalse(mock_echo.called, "No message should be sent if no new activies are present")

    def test_sets_last_sync_on_first_load(self):
        mock_fetch, mock_echo, _ = self.setupMocks((lambda url, sync: (
            [], Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"])) if "episodes" in url else ([], None)))

        self.trakt.update_user("adam")

        self.assertTrue(mock_fetch.call_args_list == [call(ANY, None), call(ANY, None)])
        self.assertTrue("last_sync_episodes" in self.trakt.users["adam"])
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
        self.assertFalse("last_sync_movies" in self.trakt.users["adam"])
        self.assertFalse(mock_echo.called, "No message should be sent if no last_sync had been set before")

    @patch("plugins.trakt.trakt.Trakt.format_activity")
    def test_single_episode(self, format_):
        user_name = "adam"
        fetch_return = lambda url, sync: ([ACTIVITY_PRESET_EPISODE_1], Trakt.get_date(
                ACTIVITY_PRESET_EPISODE_1["watched_at"])) if "episodes" in url else ([], None)
        summary = {"action": "WOOT", "series": [{"data": "dummy"}]}
        summary_return = lambda _: [summary]
        mock_fetch, mock_echo, _ = self.setupMocks(fetch_return, summary_return)
        self.trakt.users["adam"]["last_sync_episodes"] = Trakt.get_date(
                ACTIVITY_PRESET_EPISODE_1["watched_at"]) - relativedelta.relativedelta(days=1)

        self.trakt.update_user(user_name)

        self.assertTrue(mock_echo.called, "A message should have been sent")
        format_.assert_called_once_with(summary["series"][0], user_name, summary["action"])
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))

    def test_no_new_episodes(self):
        fetch_return = lambda url, sync: (
            [], Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"])) if "episodes" in url else ([], None)
        mock_fetch, mock_echo, _ = self.setupMocks(fetch_return)
        self.trakt.users["adam"]["last_sync_episodes"] = Trakt.get_date(
                ACTIVITY_PRESET_EPISODE_1["watched_at"]) - relativedelta.relativedelta(days=1)

        self.trakt.update_user("adam")

        self.assertFalse(mock_echo.called, "No message should be sent if no new activities were found")
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))

    def test_new_activity_both_types(self):
        fetch_return = lambda url, sync: ([ACTIVITY_PRESET_EPISODE_1], Trakt.get_date(
                ACTIVITY_PRESET_EPISODE_1["watched_at"])) if "episodes" in url else (
            [ACTIVITY_PRESET_MOVIE_1], Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
        summary_episode = {"action": "WOOT", "series": [{"data": "dummy_episode2000"}]}
        summary_movie = {"action": "WOOT", "series": [{"data": "dummy_movie1000"}]}
        summary_return = lambda activities: [summary_episode] if activities == [ACTIVITY_PRESET_EPISODE_1] else [
            summary_movie]
        mock_fetch, mock_echo, _ = self.setupMocks(fetch_return, summary_return)
        self.trakt.users["adam"]["last_sync_episodes"] = Trakt.get_date("2013-03-31T09:28:53.000Z")
        self.trakt.users["adam"]["last_sync_movies"] = Trakt.get_date("2013-03-31T09:28:53.000Z")

        self.trakt.update_user("adam")

        self.assertEqual(mock_echo.call_count, 2)
        self.assertEqual(self.trakt.users["adam"]["last_sync_episodes"],
                         Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]))
        self.assertEqual(self.trakt.users["adam"]["last_sync_movies"],
                         Trakt.get_date(ACTIVITY_PRESET_MOVIE_1["watched_at"]))

class FetchTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()
        self.trakt.users = {"adam": {}}
        self.test_url = "http://apa"

    def setupMocks(self, get=None):
        mock_get = Mock(side_effect=get)
        self.trakt.get = mock_get

        return mock_get

    def test_no_sync_no_activities(self):
        get_return = lambda url, params: []
        self.setupMocks(get_return)

        activities, last_sync = self.trakt.fetch_new_activities(self.test_url, None)

        self.assertFalse(len(activities) > 0, "Should not have gotten any activities")
        self.assertEqual(last_sync, None, "Should not have gotten a last_sync")

    def test_no_sync_yes_activities(self):
        get_return = lambda url, params: [ACTIVITY_PRESET_EPISODE_1]
        self.setupMocks(get_return)

        activities, last_sync = self.trakt.fetch_new_activities(self.test_url, None)

        self.assertFalse(len(activities) > 0,
                         "Should not have gotten any activities if there was no previous last_sync")
        self.assertEqual(last_sync, Trakt.get_date(ACTIVITY_PRESET_EPISODE_1["watched_at"]),
                         "A new last_sync should have been added")

    def test_sync_no_activities(self):
        get_return = lambda url, params=None: []
        self.setupMocks(get_return)
        current_last_sync = Trakt.get_date("2013-03-31T09:28:53.000Z")

        activities, last_sync = self.trakt.fetch_new_activities(self.test_url, current_last_sync)

        self.assertFalse(len(activities) > 0, "No new activities found so none should be returned")
        self.assertEqual(last_sync, current_last_sync, "The new last_sync should be the same as the old one")

    def test_no_pagination_few_items(self):
        now = int(time.time()) - 60
        result = [{"watched_at": datetime.fromtimestamp(now - n * 24 * 3600).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                   "number": n + 1, "season": 1} for n in range(10)]

        get_return = lambda url, params=None: result if params["page"] == 1 else []
        self.setupMocks(get_return)
        current_last_sync = Trakt.get_date("2013-03-31T09:28:53.000Z")

        activities, last_sync = self.trakt.fetch_new_activities(self.test_url, current_last_sync)

        self.assertTrue(len(activities) == len(result),
                        "Got wrong number of activities back. Wanted %s, got %s" % (len(result), len(activities)))
        self.assertEqual(last_sync, Trakt.get_date(result[0]["watched_at"]),
                         "last_sync should be same as latest episode but was %s" % last_sync)

    def test_no_pagination_filtered_by_sync(self):
        now = int(time.time()) - 60
        result = [{"watched_at": datetime.fromtimestamp(now - n * 24 * 3600).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                   "number": n + 1, "season": 1} for n in range(10)]

        get_return = lambda url, params=None: result if params["page"] == 1 else []
        self.setupMocks(get_return)
        current_last_sync = Trakt.get_date(result[4]["watched_at"])

        activities, last_sync = self.trakt.fetch_new_activities(self.test_url, current_last_sync)

        self.assertTrue(activities == result[:4],
                        "Got wrong activities back. Wanted %s, got %s" % (result[:4], activities))
        self.assertEqual(last_sync, Trakt.get_date(result[0]["watched_at"]),
                         "last_sync should be same as latest episode but was %s" % last_sync)

    def test_tes_pagination_filtered_by_sync(self):
        now = int(time.time()) - 60
        result_1 = [{"watched_at": datetime.fromtimestamp(now - n * 24 * 3600).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                     "number": n + 1, "season": 1} for n in range(10)]
        result_2 = [{"watched_at": datetime.fromtimestamp(now - n * 24 * 3600).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                     "number": n + 1, "season": 1} for n in range(10, 20)]

        get_return = lambda url, params=None: result_1 if params["page"] == 1 else result_2 if params[
                                                                                                   "page"] == 2 else []
        self.setupMocks(get_return)
        current_last_sync = Trakt.get_date(result_2[6]["watched_at"])

        activities, last_sync = self.trakt.fetch_new_activities(self.test_url, current_last_sync)

        total_result = result_1 + result_2[:6]
        self.assertTrue(activities == total_result,
                        "Got wrong activities back. Wanted %s, got %s" % (total_result, activities))
        self.assertEqual(last_sync, Trakt.get_date(result_1[0]["watched_at"]),
                         "last_sync should be same as latest episode but was %s" % last_sync)

class SummaryTestCase(unittest.TestCase):

    def setUp(self):
        self.trakt = Trakt()
        self.trakt.users = {"adam": {}}

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
        self.assertEquals(result, [])

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
        