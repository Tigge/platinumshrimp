import feedparser
import logging

from utils import str_utils

from plugins.feedretriever.pollerfactory import PollerFactory, PollerBase

FAIL_MESSAGE = (
    "Unable to download or parse feed.  Remove unused feeds using "
    "the !listfeed and !removefeed commands."
)

# Spam control, don't print more than 10 new messages:
MAX_NEW_MESSAGES = 7


# Simple polling class, fetches the feed in a regular interval and passes
# the information on to the Feed object
@PollerFactory.register("*")
class FeedPoller(PollerBase):
    def __init__(self, feed, on_created, on_entry, on_error):
        self.feed = feed
        self.feed["title"] = str_utils.sanitize_string(self.feed["title"])

        self.last_entry = None
        self.modified = None
        self.etag = None
        self.consecutive_fails = 0
        self.update_count = 0
        self.on_created = on_created
        self.on_entry = on_entry
        self.on_error = on_error

        parsed = self.read(feed["url"])
        if parsed.bozo == 0:
            self._set_last(parsed.entries)
            if self.feed["title"] == "":
                self.feed["title"] = str_utils.sanitize_string(parsed.feed.title)
            on_created(self.feed)
        else:
            self.modified = ""
            raise Exception("Could not parse feed")

    def read(self, url, modified=None, etag=None):
        parsed = feedparser.parse(url, modified=modified, etag=etag)
        if parsed.bozo == 0:
            self.modified = parsed.get("modified", None)
            self.etag = parsed.get("etag", None)
        return parsed

    def force_update(self):
        self.update_count = self.feed["frequency"]

    def update(self):
        self.update_count += 1
        if self.update_count < self.feed["frequency"]:
            return

        self.update_count = 0
        self.update_now()

    def update_now(self):
        parsed = self.read(self.feed["url"], self.modified, self.etag)
        if parsed.bozo == 1:
            self.consecutive_fails += 1
            if self.consecutive_fails % 10 == 0:
                self.on_error(self.feed, FAIL_MESSAGE)
            return

        for index, entry in enumerate(parsed.entries):
            # TODO: Check id, link, etc
            # Maybe save the entire data.entries and remove all duplicate when
            # a new update happens?
            if self.last_entry is not None:
                if "published_parsed" in entry:
                    if entry.published_parsed <= self.last_entry.published_parsed:
                        break
                elif entry.title == self.last_entry.title:
                    break
                elif index >= MAX_NEW_MESSAGES:
                    break

            self.on_entry(self.feed, entry)

        self._set_last(parsed.entries)
        self.consecutive_fails = 0

    def reset_latest(self):
        parsed = self.read(self.feed["url"], self.modified, self.etag)
        if len(parsed.entries) > 0:
            parsed.entries.pop(0)
        self._set_last(parsed.entries)

    def _set_last(self, entries):
        if len(entries) > 0:
            self.last_entry = entries[0]
