import os
import unittest

from plugins.feedretriever.feedretriever import Feed, FeedItemToString


class FeedRetriverTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def test_basic_feed(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f:
            feed = Feed(f.read(), "Basic Feed")

    def test_no_update(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f:
            data = f.read()
            feed = Feed(data, "No update")

            def say(output):
                self.fail("Got output even when the feed hasn't been updated: {}".format(output))
            feed.update(data, say)

    def test_initial_update(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f1:
            data = f1.read()
            feed_name = "Test"
            feed = Feed(data, feed_name)
            self.updated = False

            def say(output):
                self.assertEqual(output, FeedItemToString("Test Title", "http://www.example.com", feed_name))
                self.updated = True
            with open(os.path.join(self.dir, "basic_rss_1-entries.xml")) as f2:
                data = f2.read()
                feed.update(data, say)
                self.assertTrue(self.updated)
