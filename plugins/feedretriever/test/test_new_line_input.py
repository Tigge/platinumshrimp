import os
import unittest

from feedretriever import Feed


class FeedRetriverTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    def test_title_starting_with_new_line(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f:
            feed_name = """
            Test feed"""
            feed = Feed(f.read(), feed_name)
            self.assertEqual(feed.title, "Test feed")

    def test_title_ending_with_new_line(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f:
            feed_name = """Test feed
            """
            feed = Feed(f.read(), feed_name)
            self.assertEqual(feed.title, "Test feed")

    def test_title_has_new_line_in_middle(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f:
            feed_name = """Test
            feed"""
            feed = Feed(f.read(), feed_name)
            self.assertEqual(feed.title, "Test feed")

    def test_feed_item_has_new_lines(self):
        with open(os.path.join(self.dir, "basic_rss_0-entries.xml")) as f1:
            data = f1.read()
            feed_name = """
            Test
            feed
            """
            feed = Feed(data, feed_name)
            self.assertEqual(feed.title, "Test feed")
            self.updated = False

            def say(output):
                self.assertEqual(output, "Test feed: Test Title <http://www.example.com>")
                self.updated = True
            with open(os.path.join(self.dir, "basic_rss_1-entries_new_line.xml")) as f2:
                data = f2.read()
                feed.update(data, say)
                self.assertTrue(self.updated)
