import os
import unittest

from plugins.feedretriever.feedretriever import Feed, FeedItemToString


class FeedRetriverTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def test_runkeeper_feed(self):
        with open(os.path.join(self.dir, "runkeeper_rss_0-entries.xml")) as f:
            feed = Feed(f.read(), "Runkeeper Feed")

    def test_runkeeper_no_update(self):
        with open(os.path.join(self.dir, "runkeeper_rss_0-entries.xml")) as f:
            data = f.read()
            feed = Feed(data, "No update")

            def say(output):
                self.fail("Got output even when the feed hasn't been updated: {}".format(output))
            feed.update(data, say)

    def test_runkeeper_initial_update(self):
        with open(os.path.join(self.dir, "runkeeper_rss_0-entries.xml")) as f1:
            data = f1.read()
            feed_name = "Test"
            feed = Feed(data, feed_name)
            self.updated = False

            def say(output):
                self.assertEqual(output, FeedItemToString("Walking Activity on 2016-07-11 07:45:01", "https://runkeeper.com/user/mikesir87/activity/823368881", feed_name))
                self.updated = True
            with open(os.path.join(self.dir, "runkeeper_rss_1-entries.xml")) as f2:
                data = f2.read()
                feed.update(data, say)
                self.assertTrue(self.updated)
    def test_runkeeper_multiple_updates(self):
        with open(os.path.join(self.dir, "runkeeper_rss_0-entries.xml")) as f1:
            data = f1.read()
            feed_name = "Test"
            feed = Feed(data, feed_name)
            self.updated = False

            def say(output):
                self.assertEqual(output, FeedItemToString("Walking Activity on 2016-07-11 07:45:01", "https://runkeeper.com/user/mikesir87/activity/823368881", feed_name))
                self.updated = True
            with open(os.path.join(self.dir, "runkeeper_rss_1-entries.xml")) as f2:
                data = f2.read()
                feed.update(data, say)
                self.assertTrue(self.updated)
                self.updated = False
                def say2(output):
                    self.assertEqual(output, FeedItemToString("Walking Activity on 2016-07-11 17:33:27", "https://runkeeper.com/user/mikesir87/activity/823715917", feed_name))
                    self.updated = True
                with open(os.path.join(self.dir, "runkeeper_rss_2-entries.xml")) as f3:
                    data = f3.read()
                    feed.update(data, say2)
                    self.assertTrue(self.updated)

