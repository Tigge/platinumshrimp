# Sample configuration:
#
# "titlegiver": {
#   "yt-key": "youtube-API-key",
#   "blacklist": [
#     "www.youtube.com",
#     "youtube.com",
#     "youtu.be",
#     "xcancel.com",
#     "x.com"
#   ]
# },
#
# All settings are optional, but without the YouTube API key, you will not get titles from YouTube.
#


import re
import sys
import logging
import urllib
import json

import plugin
from utils import url_parser, auto_requests, str_utils, youtube, number_utils


class Titlegiver(plugin.Plugin):

    TITLE_REGEX = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
    WHITESPACE_REGEX = re.compile(r"\s+")

    MAX_CONTENT_LENGTH = 64 * 1024
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/43.0.2357.37 Safari/537.36"
    )
    MAX_LINE_COUNT = 16

    def __init__(self):
        plugin.Plugin.__init__(self, "titlegiver")

    @staticmethod
    def get_title_from_url(url):
        # Fetch page (no need to verfiy SSL certs for titles)
        response = auto_requests.get(
            url,
            verify=False,
            headers={"User-Agent": Titlegiver.USER_AGENT, "Accept-Language": "en_US"},
        )
        content = response.text[: Titlegiver.MAX_CONTENT_LENGTH]

        # Avoid leaving dangling redirects when we've got the content
        response.connection.close()

        return Titlegiver.find_title_in_content(content).strip()

    @staticmethod
    def find_title_in_content(text):
        try:
            title = Titlegiver.WHITESPACE_REGEX.sub(
                " ", Titlegiver.TITLE_REGEX.search(text).group(1)
            )
            return str_utils.unescape_entities(title)
        except:
            logging.exception("Regexp or unescape failed")
            return None

    @staticmethod
    # Split a given string and remove empty lines
    def split_strip_and_slice(text, limit=0):
        return [line.strip() for line in text.splitlines() if line.strip()][0:limit]

    def started(self, settings):
        self.settings = json.loads(settings)
        if "blacklist" not in self.settings:
            self.settings["blacklist"] = [
                "www.youtube.com",
                "youtube.com",
                "youtu.be",
                "xcancel.com",
                "x.com",
            ]
            self._save_settings(json.dumps(self.settings))

    def process_url(self, url, server, channel):
        parts = urllib.parse.urlparse(url)
        if parts.netloc in self.settings["blacklist"]:
            logging.info("Blacklisted %s", url)
            return

        title = Titlegiver.get_title_from_url(url)
        for line in Titlegiver.split_strip_and_slice(title, Titlegiver.MAX_LINE_COUNT):
            self.privmsg(server, channel, line)

    def process_youtube(self, id, server, channel):
        if "yt-key" not in self.settings:
            return
        yt = youtube.YouTube(self.settings["yt-key"], id)
        response = "{} [{}] ({} views)".format(yt.title, yt.duration, number_utils.format(yt.views))
        self.privmsg(server, channel, response)

    def on_pubmsg(self, server, user, channel, message):
        for url in url_parser.find_urls(message):
            self._thread(self.process_url, url, server, channel)
        for id in youtube.YouTube.find_all_ids(message):
            self._thread(self.process_youtube, id, server, channel)


if __name__ == "__main__":
    sys.exit(Titlegiver.run())
