import logging
import re

from plugins.feedretriever.feedpoller import FeedPoller
from plugins.feedretriever.pollerfactory import PollerFactory

from utils import auto_requests

CNN_URL = "https://lite.cnn.com/"


# This basically, with a bit of trickery, turns the CNN_URL into a feed.
@PollerFactory.register(CNN_URL)
class CNNPoller(FeedPoller):
    def read(self, url, modified=None, etag=None):
        logging.info("CNNpoller.read")
        response = auto_requests.get(url)
        pattern = r'<li.*?(<a href="(.*?)">\s*(.*?)\s*</a>).*?</li>'
        matches = re.findall(pattern, response.text, re.DOTALL)
        response.connection.close()
        entries_ = []
        for _, link_, title_ in matches:

            class CNNEntry(list):
                link = url + link_
                title = title_

            entries_.append(CNNEntry())

        class CNNFeed:
            entries = entries_
            if len(entries) == 0:
                bozo = 1
            else:
                bozo = 0

        return CNNFeed()
