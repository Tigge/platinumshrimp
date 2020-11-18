import html
import re
import sys
import logging
import json
import requests

import plugin


class Twitter(plugin.Plugin):

    MAX_LINE_COUNT = 16

    URL_REGEX = re.compile(r"https?:\/\/twitter.com\/([A-Za-z0-9_]+)\/status\/([0-9]+)")

    def __init__(self):
        plugin.Plugin.__init__(self, "twitter")
        self.settings = {}

    def started(self, settings):
        logging.info("Twitter.started %s", settings)
        self.settings = json.loads(settings)

    def process(self, id, server, channel):
        logging.info("Twitter.process id %s", id)
        response = requests.get(
            "https://api.twitter.com/1.1/statuses/show.json",
            params={"id": id, "tweet_mode": "extended"},
            headers={"Authorization": "Bearer {}".format(self.settings["bearer"])},
        )
        logging.info("Twitter.process response %s", response)
        data = response.json()
        logging.info("Twitter.process json %s", data)
        for line in data["full_text"].splitlines():
            self.privmsg(server, channel, line)

    def on_pubmsg(self, server, user, channel, message):
        for (_, id) in re.findall(Twitter.URL_REGEX, message):
            logging.info("Twitter.on_pubmsg %s", id)
            try:
                self._thread(self.process, id, server, channel)
            except:
                logging.exception("Unable to find title for: %s", id)


if __name__ == "__main__":
    sys.exit(Twitter.run())
