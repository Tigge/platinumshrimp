import feedparser
import os
import unittest
import unittest.mock

from plugins.feedretriever.feedretriever import Feedpoller


def noop(*a, **kw):
    pass


feedparse = feedparser.parse


class FeedRetriverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    @unittest.mock.patch("feedparser.parse")
    def test_runkeeper_feed(self, read):
        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_0-entries.xml")
        )
        Feedpoller(
            {"url": "MOCK_URL", "title": "Runkeeper Feed"},
            on_created=noop,
            on_entry=noop,
            on_error=self.fail,
        )

    @unittest.mock.patch("feedparser.parse")
    def test_runkeeper_no_update(self, read):
        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_0-entries.xml")
        )
        poller = Feedpoller(
            {"url": "MOCK_URL", "title": "Runkeeper Feed"},
            on_created=noop,
            on_entry=self.fail,
            on_error=self.fail,
        )
        poller.update_now()

    @unittest.mock.patch("feedparser.parse")
    def test_runkeeper_initial_update(self, read):
        def on_entry(feed, entry):
            self.assertEqual(entry.title, "Walking Activity on 2016-07-11 07:45:01")
            self.assertEqual(
                entry.link, "https://runkeeper.com/user/mikesir87/activity/823368881"
            )
            self.updated = True

        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_0-entries.xml")
        )
        poller = Feedpoller(
            {"url": "MOCK_URL", "title": "Test"},
            on_created=noop,
            on_entry=on_entry,
            on_error=self.fail,
        )
        self.updated = False

        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_1-entries.xml")
        )
        poller.update_now()
        self.assertTrue(self.updated)

    @unittest.mock.patch("feedparser.parse")
    def test_runkeeper_multiple_updates(self, read):
        def on_entry1(feed, entry):
            self.assertEqual(entry.title, "Walking Activity on 2016-07-11 07:45:01")
            self.assertEqual(
                entry.link, "https://runkeeper.com/user/mikesir87/activity/823368881"
            )
            self.updated = True

        def on_entry2(feed, entry):
            self.assertEqual(entry.title, "Walking Activity on 2016-07-11 17:33:27")
            self.assertEqual(
                entry.link, "https://runkeeper.com/user/mikesir87/activity/823715917"
            )
            self.updated = True

        def on_entry(feed, entry):
            self.on_entry(feed, entry)

        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_0-entries.xml")
        )
        poller = Feedpoller(
            {"url": "MOCK_URL", "title": "Test"},
            on_created=noop,
            on_entry=on_entry,
            on_error=self.fail,
        )

        self.updated = False
        self.on_entry = on_entry1
        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_1-entries.xml")
        )
        poller.update_now()
        self.assertTrue(self.updated)

        self.updated = False
        self.on_entry = on_entry2
        read.return_value = feedparse(
            os.path.join(self.dir, "runkeeper_rss_2-entries.xml")
        )
        poller.update_now()
        self.assertTrue(self.updated)
