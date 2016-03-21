import json
import logging
import re
import sys

import requests

from platinumshrimp import plugin


class Yogscaster(plugin.Plugin):

    ARTICLE_REGEX = re.compile(r'<article id="latest"[^>]*>(.*)</article>', re.IGNORECASE | re.DOTALL)
    LI_REGEX = re.compile(r'<li><figure data-code="([^"]*)" title="([^"]*)" class="([^"]*)">.*</li>', re.IGNORECASE | re.DOTALL)
    WHITESPACE_REGEX = re.compile(r'\s+')
    SITE_URL = "http://www.yogscast.com"

    def __init__(self):
        plugin.Plugin.__init__(self, "Yogscaster")
        self.latest = None
        self.update_freq = 60 * 5
        self.count = -1
        self.settings = {}

    @staticmethod
    def poll_site():
        request = requests.get(Yogscaster.SITE_URL)
        return Yogscaster.find_latest(request.text)

    @staticmethod
    def find_latest(text):
        article = Yogscaster.ARTICLE_REGEX.search(text).group(0)
        item = Yogscaster.LI_REGEX.search(article)
        video = dict()
        video["link"] = Yogscaster.SITE_URL + '/video/' + item.group(1)
        video["title"] = item.group(2)
        video["author"] = item.group(3).split(' ')[1]
        return video

    def echo(self, message):
        logging.info("Echo: ", message.encode("utf-8"))
        self.say(0, str(self.settings["channel"]), message)

    def started(self, settings):
        logging.info("Yogscaster.started", settings)
        self.settings = json.loads(settings)
        self.join(0, str(self.settings["channel"]))

    def update(self):
        self.count += 1
        if self.count % self.update_freq == 0:
            logging.info("Yogscaster.update")
            latest = Yogscaster.poll_site()
            if self.latest != latest["title"] and latest["author"] in self.settings["whitelist"]:
                logging.info("Latest: ", latest)
                self.latest = latest["title"]
                message = "%s: %s %s" % (latest["author"], latest["link"], latest["title"])
                self.echo(message)


if __name__ == "__main__":
    sys.exit(Yogscaster.run())
