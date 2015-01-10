from twisted.trial import unittest

from plugins.feedretriever.feedretriever import Feed
class FeedRetriverTest(unittest.TestCase):
    def test_basic_feed(self):
        with open("../plugins/feedretriever/test/basic_rss_0-entries.xml") as f:
            feed = Feed(f.read(), "Basic Feed")

    def test_no_update(self):
        with open("../plugins/feedretriever/test/basic_rss_0-entries.xml") as f:
            data = f.read()
            feed = Feed(data, "No update")
            # TODO: Mock
            def say(output):
                self.fail("Got output even when the feed hasn't been updated: {}".format(output))
            feed.update(data, say)

    def test_no_update(self):

        f1 = open("../plugins/feedretriever/test/basic_rss_0-entries.xml").read()
        f2 = open("../plugins/feedretriever/test/basic_rss_1-entries.xml").read()

        self.updated = False

        feed = Feed(f1, "Update")

        # TODO: Mock
        def say(output):
            self.assertEqual(output, u"Update: Test Title <http://www.example.com>")
            self.updated = True

        feed.update(f2, say)
        self.assertTrue(self.updated)