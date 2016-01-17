import unittest

from utils.url_parser import find_urls

class TestStrUtils(unittest.TestCase):
    def test_non_ascii(self):
        self.assertEqual(find_urls("http://kött.se/å.htm"), ["http://kött.se/å.htm"])
        self.assertEqual(find_urls("http://ko.wikipedia.org/wiki/위키백과:대문"),
            ["http://ko.wikipedia.org/wiki/위키백과:대문"])
        self.assertEqual(find_urls("http://d%C3%BCsseldorf.de"),
            ["http://d%C3%BCsseldorf.de"])
        self.assertEqual(find_urls("http://en.wikipedia.org/wiki/ɸ"),
            ["http://en.wikipedia.org/wiki/ɸ"])

    def test_multiple_urls(self):
        self.assertEqual(find_urls("Text with http://mydomain.com and http://testdomain.com and more"),
            ["http://mydomain.com", "http://testdomain.com"])

    def test_with_ending_comma(self):
        self.assertEqual(find_urls("http://mydomain.com, http://testdomain.com"),
            ["http://mydomain.com", "http://testdomain.com"])

    def test_https(self):
        self.assertEqual(find_urls("https://mydomain.com"), ["https://mydomain.com"])

    def test_with_no_protocol(self):
        self.assertEqual(find_urls("mydomain.com"), ["http://mydomain.com"])
        self.assertEqual(find_urls("mydomain.com/is_awesome"), ["http://mydomain.com/is_awesome"])

    def test_auth(self):
        self.assertEqual(find_urls("https://user:pass@url.com"), ["https://user:pass@url.com"])

    def test_with_path(self):
        self.assertEqual(find_urls("http://url.com/with/multi/level_path"),
            ["http://url.com/with/multi/level_path"])

    def test_subdomain(self):
        self.assertEqual(find_urls("http://my.domain.co.uk/is.best"),
            ["http://my.domain.co.uk/is.best"])

