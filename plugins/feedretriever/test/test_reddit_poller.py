import unittest
import unittest.mock
from plugins.feedretriever.redditpoller import RedditPoller


def noop(*a, **kw):
    pass


class RedditPollerTest(unittest.TestCase):
    @unittest.mock.patch("utils.auto_requests.get")
    def test_reddit_poller_initialization(self, mock_get):
        # Mock response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_1",
                            "title": "Post 1",
                            "permalink": "/r/sweden/comments/1/",
                            "subreddit": "sweden",
                        }
                    },
                    {
                        "data": {
                            "name": "t3_2",
                            "title": "Post 2",
                            "permalink": "/r/sweden/comments/2/",
                            "subreddit": "sweden",
                        }
                    },
                ]
            }
        }
        mock_get.return_value = mock_response

        poller = RedditPoller(
            {"url": "https://old.reddit.com/r/sweden/", "title": "", "frequency": 10},
            on_created=noop,
            on_entry=noop,
            on_error=self.fail,
        )

        self.assertEqual(len(poller.seen_ids), 2)
        self.assertIn("t3_1", poller.seen_ids)
        self.assertIn("t3_2", poller.seen_ids)
        self.assertEqual(poller.feed["title"], "r/sweden")

    @unittest.mock.patch("utils.auto_requests.get")
    def test_reddit_poller_update(self, mock_get):
        # Initial read (population of seen_ids)
        mock_response_1 = unittest.mock.Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_1",
                            "title": "Post 1",
                            "permalink": "/r/sweden/comments/1/",
                            "subreddit": "sweden",
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response_1

        entries = []

        def on_entry(feed, entry):
            entries.append(entry)

        poller = RedditPoller(
            {"url": "https://old.reddit.com/r/sweden/", "title": "Reddit", "frequency": 10},
            on_created=noop,
            on_entry=on_entry,
            on_error=self.fail,
        )

        # Second read with a new post at the top
        mock_response_2 = unittest.mock.Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_2",
                            "title": "Post 2",
                            "permalink": "/r/sweden/comments/2/",
                            "subreddit": "sweden",
                        }
                    },
                    {
                        "data": {
                            "name": "t3_1",
                            "title": "Post 1",
                            "permalink": "/r/sweden/comments/1/",
                            "subreddit": "sweden",
                        }
                    },
                ]
            }
        }
        mock_get.return_value = mock_response_2

        poller.update_now()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "Post 2")
        self.assertEqual(entries[0].id, "t3_2")
        self.assertIn("t3_2", poller.seen_ids)

    @unittest.mock.patch("utils.auto_requests.get")
    def test_reddit_poller_lru(self, mock_get):
        # Mock enough posts to fill LRU (MAX_LRU_SIZE = 50)
        children = [
            {
                "data": {
                    "name": f"t3_{i}",
                    "title": f"Post {i}",
                    "permalink": f"/r/sweden/comments/{i}/",
                    "subreddit": "sweden",
                }
            }
            for i in range(60)
        ]

        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": children}}
        mock_get.return_value = mock_response

        poller = RedditPoller(
            {"url": "https://old.reddit.com/r/sweden/", "title": "Reddit", "frequency": 10},
            on_created=noop,
            on_entry=noop,
            on_error=self.fail,
        )

        # LRU should only keep 50 most recent (t3_0 to t3_49)
        self.assertEqual(len(poller.seen_ids), 50)
        self.assertIn("t3_0", poller.seen_ids)
        self.assertIn("t3_49", poller.seen_ids)
        self.assertNotIn("t3_50", poller.seen_ids)
        self.assertNotIn("t3_59", poller.seen_ids)
