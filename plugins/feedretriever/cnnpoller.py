import logging
import re

from plugins.feedretriever.feedpoller import FeedPoller
from plugins.feedretriever.pollerfactory import PollerFactory

from utils import auto_requests

CNN_URL = "https://lite.cnn.com"
CNN_DEFAULT_TITLE = "CNN"


class CNNEntry:
    def __init__(self, link, title):
        self.link = link
        self.title = title

    def __contains__(self, _):
        return False


class CNNFeedMeta:
    def __init__(self):
        # FeedPoller only use this title if the title is not set when the feed is created
        self.title = CNN_DEFAULT_TITLE


class CNNFeed:
    def __init__(self, entries):
        self.entries = entries
        self.bozo = 1 if not entries else 0
        self.feed = CNNFeedMeta()


# This basically, with a bit of trickery, turns the CNN_URL into a feed.
@PollerFactory.register(CNN_URL)
class CNNPoller(FeedPoller):
    def read(self, url, modified=None, etag=None):
        logging.info("CNNpoller.read")
        response = auto_requests.get(url)
        pattern = r'<li.*?(<a href="(.*?)">\s*(.*?)\s*</a>).*?</li>'
        matches = re.findall(pattern, response.text, re.DOTALL)
        response.connection.close()
        return CNNFeed([CNNEntry(url + link, title) for _, link, title in matches])
