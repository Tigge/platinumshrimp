import unittest
import re

from plugins.twitter.twitter import Twitter


class TwitterRegex(unittest.TestCase):
    def test_url_regex(self):

        urls = [
            "https://twitter.com/sr_ekot/status/1351644064869994496",
            "https://twitter.com/oneunderscore__/status/1351933819058868225",
            "https://mobile.twitter.com/jacobrask/status/1349856278454153233",
            "https://mobile.twitter.com/kaitlancollins/status/1351293994710544384",
            "https://www.twitter.com/realDonaldTrump/status/1347569870578266115",
            "twitter.com/sr_ekot/status/1351644064869994496",
            "www.twitter.com/sr_ekot/status/1351644064869994496",
            "mobile.twitter.com/sr_ekot/status/1351644064869994496",
            "http://twitter.com/CNN/status/1346925651811590149",
        ]

        for url in urls:
            self.assertIsNotNone(
                re.fullmatch(Twitter.URL_REGEX, url), f"{url} should be a twitter url"
            )
