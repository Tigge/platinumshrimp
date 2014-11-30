import json
import sys
import feedparser

from twisted.python import log

import plugin


# The Feed class handles printing out new entries
class Feed():
    def __init__(self, data) :
        self.set_last(data.entries)

    def update(self, data, say):
        log.msg("Updating feed: " + data.feed.title.encode("utf-8"))
        for entry in data.entries:
            # TODO: Check id, etc
            if entry.published_parsed <= self.last_entry:
                break
            say(str(entry.title.encode("utf-8")) + ": " + entry.link.encode("utf-8"))
        self.set_last(data.entries)

    def set_last(self, entries):
        self.last_entry = entries[0].published_parsed if len(entries) > 0 else 0


# Simple polling class, fetches the feed in a regular intervall and passes
# the information on to the Feed object
class Feedpoller():
  def __init__(self, say, url, update_freq=5*60):
      parsed = feedparser.parse(url)
      self.feed = Feed(parsed)
      if parsed.bozo == 0:
          say("Feed added: " + parsed.feed.title.encode("utf-8"))
      self.say = say
      self.url = url
      self.consecutive_fails = 0
      self.update_freq = update_freq
      self.update_count = 0

  def update(self):
      self.update_count += 1
      if self.update_count >= self.update_freq:
          self.update_count = 0
          parsed = feedparser.parse(self.url)
          if parsed.bozo == 1:
              self.consecutive_fails += 1
          else:
              self.feed.update(parsed, self.say)
              self.consecutive_fails = 0
          #TODO: remove if too many consecutive fails?


# Aggregator class for adding and handling feeds
class Feedretriever(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "Feedretriever")
        self.feeds = []

    def started(self, settings):
        log.msg("Feedretriever.started", settings)
        #self.settings = json.loads(settings)
        #TODO: Save feeds to file and recreate when the bot is restarted

    def privmsg(self, server_id, user, channel, message):
        if message.startswith("!feed "):
            #TODO: Parse update frequency
            self.feeds.append(Feedpoller(
                lambda msg: self.say(server_id, channel, msg),
                message[6:].encode("utf-8")))
        #TODO: List feeds and remove feeds

    def update(self):
        for feed in self.feeds:
            feed.update()

if __name__ == "__main__":
    sys.exit(Feedretriever.run())
