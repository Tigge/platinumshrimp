import json
import logging
import sys
import re

import plugin
from utils import str_utils, auto_requests
from plugins.feedretriever.feedpoller import Feedpoller
import plugins.feedretriever.cnnpoller


HELP_MESSAGE = (
    "!addfeed url [fetch time [custom title]] where:\n"
    "url - is the url of the atom or rss feed\n"
    "fetch time - is the number of minutes between each request\n"
    "custom title - is the title used for this feed.\n"
    "If no title is given, the default title parsed from the "
    "feed will be used instead."
)

REMOVING_FEED_MESSAGE = "Removing: #{} - {}"
LIST_FEED_ITEM_MESSAGE = "#{}: {}"
NO_FEED_MESSAGE = "No feeds"

DEFAULT_FETCH_TIME = 10 * 60


def FeedItemToString(title, link, feed_title=""):
    return str_utils.sanitize_string("{}: {} <{}>".format(feed_title, title, link))


def GetFeedIndexArrayFromCommand(message, feed_size, select_all=False):
    feeds = []
    # If no feed is specified, we might want to return all of them:
    if select_all and not " " in message:
        feeds = list(range(feed_size))
    # Otherwise, only return the specified ones:
    for i in message.split(" "):
        i = int(i) if i.isdecimal() else -1
        if i >= 0 and i < feed_size:
            feeds.append(i)
    return feeds


# Aggregator class for adding and handling feeds
class Feedretriever(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "feedretriever")
        self.feeds = []

    def started(self, settings):
        logging.info("Feedretriever.started %s", settings)
        self.settings = json.loads(settings)

        logging.info("Feedretriever.started %s", self.settings)
        if "feeds" not in self.settings:
            self.settings["feeds"] = []
        for feed in self.settings["feeds"]:
            self.add_feed(feed, new=False)

    def add_feed(self, feed, new=True):
        def on_created(feed):
            self.privmsg(feed["server"], feed["channel"], "Added feed: " + feed["title"])
            self.settings["feeds"].append(feed)
            self._save_settings(json.dumps(self.settings))

        def on_entry(feed, entry):
            self.safe_privmsg(
                feed["server"],
                feed["channel"],
                FeedItemToString(entry.title, entry.link, feed["title"]),
            )

        def on_error(feed, message):
            self.privmsg(feed["server"], feed["channel"], feed["title"] + ": " + message)

        try:
            if feed["url"] == plugins.feedretriever.cnnpoller.CNN_URL:
                poller = plugins.feedretriever.cnnpoller.CNNpoller(
                    feed,
                    on_created=on_created if new else lambda *a, **kw: None,
                    on_entry=on_entry,
                    on_error=on_error,
                )
                self.feeds.append(poller)
                return
            poller = Feedpoller(
                feed,
                on_created=on_created if new else lambda *a, **kw: None,
                on_entry=on_entry,
                on_error=on_error,
            )
            self.feeds.append(poller)
        except Exception as e:
            logging.info("Failed to add feed: %r", e)
            self.privmsg(feed["server"], feed["channel"], "Failed to add: " + feed["url"])

    def remove_feed(self, feed):
        self.feeds.remove(feed)
        self.settings["feeds"].remove(feed.feed)
        self._save_settings(json.dumps(self.settings))

    def get_feeds(self, server, channel):
        return list(
            filter(
                lambda f: f.feed["server"] == server and f.feed["channel"] == channel,
                self.feeds,
            )
        )

    def on_pubmsg(self, server, user, channel, message):
        if message.startswith("!feed") or message.startswith("!addfeed"):
            _, url, frequency, title = str_utils.split(message, " ", 4)
            if url == "":
                self.privmsg(server, channel, HELP_MESSAGE)
                return

            try:
                frequency = int(frequency) * 60
            except ValueError:
                frequency = DEFAULT_FETCH_TIME

            feed = {
                "url": url,
                "title": title,
                "server": server,
                "channel": channel,
                "frequency": frequency,
            }
            self.add_feed(feed)
        elif message.startswith("!removefeed"):
            feeds = self.get_feeds(server, channel)
            feeds_to_remove = GetFeedIndexArrayFromCommand(message, len(feeds))
            for i in sorted(feeds_to_remove, reverse=True):
                self.privmsg(
                    server,
                    channel,
                    REMOVING_FEED_MESSAGE.format(i, feeds[i].feed["title"]),
                )
                self.remove_feed(feeds[i])
                logging.info("Removed feed: %d", i)
        elif message.startswith("!listfeed"):
            feeds = self.get_feeds(server, channel)
            if len(feeds) == 0:
                self.privmsg(server, channel, NO_FEED_MESSAGE)
            for i, feed in enumerate(feeds):
                self.privmsg(
                    server,
                    channel,
                    LIST_FEED_ITEM_MESSAGE.format(i, feed.feed["title"]),
                )
        elif message.startswith("!forceupdate"):
            feeds = self.get_feeds(server, channel)
            feeds_to_update = GetFeedIndexArrayFromCommand(message, len(feeds), select_all=True)
            for i in feeds_to_update:
                feed = feeds[i]
                logging.info("Force updating feed: %s", feed.feed["title"])
                feed.force_update()

        elif message.startswith("!printlatest"):
            feeds = self.get_feeds(server, channel)
            feeds_to_update = GetFeedIndexArrayFromCommand(message, len(feeds), select_all=True)
            for i in feeds_to_update:
                feed = feeds[i]
                logging.info("Printing latest for feed: %s", feed.feed["title"])
                feed.reset_latest()
                feed.force_update()

    def update(self):
        for feed in self.feeds:
            feed.update()


if __name__ == "__main__":
    sys.exit(Feedretriever.run())
