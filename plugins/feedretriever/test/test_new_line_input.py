import os
import feedparser
import unittest
import unittest.mock

from plugins.feedretriever.feedpoller import FeedPoller


def noop(*a, **kw):
    pass


feedparse = feedparser.parse


class FeedRetriverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    @unittest.mock.patch("feedparser.parse")
    def test_title_starting_with_new_line(self, read):
        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_0-entries.xml"))
        feed_name = """
        Test feed"""
        poller = FeedPoller(
            {"url": "MOCK_URL", "title": feed_name},
            on_created=noop,
            on_entry=noop,
            on_error=self.fail,
        )
        self.assertEqual(poller.feed["title"], "Test feed")

    @unittest.mock.patch("feedparser.parse")
    def test_title_ending_with_new_line(self, read):
        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_0-entries.xml"))
        feed_name = """Test feed
        """
        poller = FeedPoller(
            {"url": "MOCK_URL", "title": feed_name},
            on_created=noop,
            on_entry=noop,
            on_error=self.fail,
        )
        self.assertEqual(poller.feed["title"], "Test feed")

    @unittest.mock.patch("feedparser.parse")
    def test_title_has_new_line_in_middle(self, read):
        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_0-entries.xml"))
        feed_name = """Test
        feed"""
        poller = FeedPoller(
            {"url": "MOCK_URL", "title": feed_name},
            on_created=noop,
            on_entry=noop,
            on_error=self.fail,
        )
        self.assertEqual(poller.feed["title"], "Test feed")
