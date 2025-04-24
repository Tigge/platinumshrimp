import re
import logging
import json
import requests
import datetime

from utils import number_utils


class YouTube:
    @staticmethod
    def duration_to_time_delta(duration):
        duration_regex = re.compile(
            r"P(?:(?P<days>\d+.?\d*)D){0,1}"
            r"T(?:(?P<hours>\d+.?\d*)H){0,1}"
            r"(?:(?P<minutes>\d+.?\d*)M){0,1}"
            r"(?:(?P<seconds>\d+.?\d*)S){0,1}"
        )
        m = duration_regex.fullmatch(duration)
        v = m.groupdict()
        logging.info("youtube duration_to_time_delta %s", v)
        td = datetime.timedelta(
            days=int(v["days"]) if v["days"] is not None else 0,
            hours=int(v["hours"]) if v["hours"] is not None else 0,
            minutes=int(v["minutes"]) if v["minutes"] is not None else 0,
            seconds=int(v["seconds"]) if v["seconds"] is not None else 0,
        )
        logging.info("util youtube durationToTimeDelta %s", str(td))
        return str(td)

    @staticmethod
    def find_all_ids(message):
        url_regex = re.compile(r"https?:\/\/.*youtu.*(?:\/|%3D|v=|vi=)([0-9A-Za-z-_]{11})")
        return re.findall(url_regex, message)

    def __init__(self, key, id):
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "id": id,
                "part": "id,snippet,contentDetails,statistics",
                "key": key,
            },
        )
        json = response.json()
        data = json["items"][0]
        logging.info("util youtube get_basic_info json %s", data)

        self.title = data["snippet"]["title"]
        self.duration = self.duration_to_time_delta(data["contentDetails"]["duration"])
        self.views = int(data["statistics"]["viewCount"])
