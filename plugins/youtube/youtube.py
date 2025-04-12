import html
import re
import sys
import logging
import json
import requests
import datetime
import locale

import plugin

from utils import number_utils


class Youtube(plugin.Plugin):

    URL_REGEX = re.compile(r"https?:\/\/.*youtu.*(?:\/|%3D|v=|vi=)([0-9A-z-_]{11})")

    DURATION_REGEX = re.compile(
        r"P(?:(?P<days>\d+.?\d*)D){0,1}"
        r"T(?:(?P<hours>\d+.?\d*)H){0,1}"
        r"(?:(?P<minutes>\d+.?\d*)M){0,1}"
        r"(?:(?P<seconds>\d+.?\d*)S){0,1}"
    )

    @staticmethod
    def durationToTimeDelta(duration):
        m = Youtube.DURATION_REGEX.fullmatch(duration)
        v = m.groupdict()
        logging.info("Youtube.durationToTimeDelta %s", v)
        td = datetime.timedelta(
            days=int(v["days"]) if v["days"] is not None else 0,
            hours=int(v["hours"]) if v["hours"] is not None else 0,
            minutes=int(v["minutes"]) if v["minutes"] is not None else 0,
            seconds=int(v["seconds"]) if v["seconds"] is not None else 0,
        )
        logging.info("Youtube.durationToTimeDelta %s", str(td))
        return str(td)

    def __init__(self):
        plugin.Plugin.__init__(self, "youtube")
        self.settings = {}

    def started(self, settings):
        logging.info("Youtube.started %s", settings)
        self.settings = json.loads(settings)

    def process(self, id, server, channel):
        logging.info("Youtube.process id %s", id)
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "id": id,
                "part": "id,snippet,contentDetails,statistics",
                "key": self.settings["key"],
            },
        )
        logging.info("Youtube.process response %s", response)
        json = response.json()
        data = json["items"][0]
        logging.info("Youtube.process json %s", data)

        title = data["snippet"]["title"]
        duration = Youtube.durationToTimeDelta(data["contentDetails"]["duration"])
        views = int(data["statistics"]["viewCount"])

        logging.info(
            "Youtube.process msg %s",
            "{} [{}] ({} views)".format(title, duration, number_utils.format(views)),
        )

        self.privmsg(
            server,
            channel,
            "{} [{}] ({} views)".format(title, duration, number_utils.format(views)),
        )

    def on_pubmsg(self, server, user, channel, message):
        logging.info("Youtube.process response %r", re.findall(Youtube.URL_REGEX, message))
        for id in re.findall(Youtube.URL_REGEX, message):
            logging.info("Youtube.on_pubmsg %s", id)
            try:
                self._thread(self.process, id, server, channel)
            except:
                logging.exception("Unable to find title for: %s", id)


if __name__ == "__main__":
    sys.exit(Youtube.run())
