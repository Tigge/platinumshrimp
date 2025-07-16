import logging
import re
import traceback

from plugins.feedretriever.feedpoller import FeedPoller
from plugins.feedretriever.pollerfactory import PollerFactory

from utils import auto_requests

OMNI_URL = "https://omni" + ".se"
OMNI_DEFAULT_TITLE = "Omni"


class OmniEntry(list):
    def __init__(self, link, title, publish_time):
        super().__init__()
        self.link = OMNI_URL + link
        self.title = title
        self.published_parsed = publish_time

    def __contains__(self, param):
        return param == "published_parsed"


class OmniFeedMeta:
    def __init__(self):
        # FeedPoller only use this title if the title is not set when the feed is created
        self.title = OMNI_DEFAULT_TITLE


class OmniFeed:
    def __init__(self, entries):
        self.entries = entries
        self.bozo = 1 if not entries else 0
        self.feed = OmniFeedMeta()


# This basically, with a bit of trickery, turns the Omni_URL into a feed.
@PollerFactory.register(OMNI_URL)
class OmniPoller(FeedPoller):
    def read(self, url, modified=None, etag=None):
        logging.info("Omnipoller.read")
        response = auto_requests.get(url + "/senaste")
        articles = re.findall(r'<div class="">(.*?)</div>', response.text, re.DOTALL)
        entries = []
        for article in articles:
            try:
                label = re.search(r'<a[^>]*aria-label="([^"]+)"[^>]*href="([^"]+)"', article)
                publish_time = re.search(r'dateTime="([^"]+)', article).group(1)
                logging.info("Omni founda: %s %s %s", publish_time, label.group(1), label.group(2))
                entries.append(OmniEntry(label.group(2), label.group(1), publish_time))
            except Exception as e:
                logging.error("Omnipoller.read parsing error: " + article)
                logging.error(traceback.format_exc())
        return OmniFeed(entries)
