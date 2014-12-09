from twisted.trial import unittest

from plugins.feedretriever.feedretriever import Feed
class FeedRetriverTest(unittest.TestCase):
    def test_basic_feed(self):
        with open("../plugins/feedretriever/test/basic_rss_0-entries.xml") as f:
            feed = Feed(f.read())

    def test_no_update(self):
        with open("../plugins/feedretriever/test/basic_rss_0-entries.xml") as f:
            data = f.read()
            feed = Feed(data)
            # TODO: Mock
            def say(output):
                self.fail("Got output even when the feed hasn't been updated: {}".format(output))
            feed.update(data, say)
