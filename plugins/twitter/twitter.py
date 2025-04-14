import html
import re
import sys
import logging
import json
import requests
import datetime
import dateutil
import dateutil.parser

import plugin

from utils import str_utils
from utils import date_utils
from utils import number_utils


class Twitter(plugin.Plugin):

    MAX_LINE_COUNT = 16

    URL_REGEX = re.compile(
        r"(?:(?:https?\:)?//)?((?:www|mobile)[\.])?twitter.com/([a-zA-Z0-9_]{1,15})/status/([0-9]+)"
    )

    def __init__(self):
        plugin.Plugin.__init__(self, "twitter")
        self.settings = {}

    def started(self, settings):
        logging.info("Twitter.started %s", settings)
        self.settings = json.loads(settings)

    def process(self, id, server, channel):
        logging.info("Twitter.process id %s", id)
        response = requests.get(
            f"https://api.twitter.com/2/tweets/{id}",
            params={
                "expansions": "author_id",
                "tweet.fields": "created_at,public_metrics",
            },
            headers={"Authorization": "Bearer {}".format(self.settings["bearer"])},
        )
        logging.info("Twitter.process response %s", response)
        data = response.json()
        logging.info("Twitter.process json %s", data)

        for line in str_utils.unescape_entities(data["data"]["text"]).splitlines():
            message = line if line != "" else " "
            self.privmsg(server, channel, message)

        user = data["includes"]["users"][0]
        author = f'@{user["username"]} ({user["name"]})'

        date = dateutil.parser.parse(data["data"]["created_at"])
        date_diff = date_utils.format(date, datetime.datetime.now(datetime.timezone.utc))

        metrics = data["data"]["public_metrics"]
        stats = f'🗩 {number_utils.format(metrics["reply_count"])} • 🗘 {number_utils.format(metrics["retweet_count"])} • ♥ {number_utils.format(metrics["like_count"])}'

        self.privmsg(server, channel, " ")
        self.privmsg(server, channel, f"- {author} • {date_diff} • {stats}")

    def on_pubmsg(self, server, user, channel, message):
        for _, _, id in re.findall(Twitter.URL_REGEX, message):
            logging.info("Twitter.on_pubmsg %s", id)
            try:
                self._thread(self.process, id, server, channel)
            except:
                logging.exception("Unable to find title for: %s", id)


if __name__ == "__main__":
    sys.exit(Twitter.run())
