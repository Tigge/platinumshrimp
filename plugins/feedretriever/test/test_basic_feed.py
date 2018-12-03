import os
import unittest
import unittest.mock
import feedparser

from plugins.feedretriever.feedretriever import Feedpoller


def noop(*a, **kw):
    pass


feedparse = feedparser.parse


class FeedRetriverTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    @unittest.mock.patch("feedparser.parse")
    def test_basic_feed(self, read):
        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_0-entries.xml"))
        Feedpoller({'url': "MOCK_URL", "title": "MOCK_TITLE"},
                   on_created=noop, on_entry=noop, on_error=self.fail)

    @unittest.mock.patch("feedparser.parse")
    def test_no_update(self, read):
        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_0-entries.xml"))
        feed = Feedpoller({'url': "MOCK_URL", "title": "MOCK_TITLE"},
                          on_created=noop, on_entry=self.fail, on_error=self.fail)
        feed.update_now()

    @unittest.mock.patch("feedparser.parse")
    def test_initial_update(self, read):
        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_0-entries.xml"))

        def on_entry(feed, entry):
            self.assertEqual(entry.title, "Test Title")
            self.assertEqual(entry.link, "http://www.example.com")
            self.updated = True

        feed = Feedpoller({'url': 'MOCK_URL', 'title': "Test"},
                          on_created=noop, on_entry=on_entry, on_error=self.fail)
        self.updated = False

        read.return_value = feedparse(os.path.join(self.dir, "basic_rss_1-entries.xml"))
        feed.update_now()
        self.assertTrue(self.updated)
