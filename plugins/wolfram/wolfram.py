import logging
import sys
import html
import json
import requests
import urllib.parse

import plugin
from utils import str_utils

RESULT_POD_START = "<pod title='Result"
DECIMAL_APPROXIMATION_POD_START = "<pod title='Decimal approximation'"
RESULT_SUB_POD = "<plaintext>"
API_URL = (
    "http://api.wolframalpha.com/v2/query?appid={key}&input={query}&format=plaintext"
)


def get_answer(query, key):
    query = urllib.parse.quote(query)
    result = requests.get(API_URL.format(key=key, query=query)).text
    if RESULT_POD_START not in result:
        if DECIMAL_APPROXIMATION_POD_START not in result:
            return
        else:
            result = result[result.index(DECIMAL_APPROXIMATION_POD_START) :]
    else:
        result = result[result.index(RESULT_POD_START) :]
    if not RESULT_SUB_POD in result:
        return
    result = result[result.index(RESULT_SUB_POD) + len(RESULT_SUB_POD) :]
    result = result[: result.index("<")]
    return str_utils.sanitize_string(result)


class Wolfram(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "wolfram")
        self.key = ""
        self.trigger = ""

    def started(self, settings):
        settings = json.loads(settings)
        self.key = settings["key"]  # str
        self.trigger = settings["trigger"]  # str

    def on_pubmsg(self, server, user, channel, message):
        if message.startswith(self.trigger):
            try:
                query = message[len(self.trigger) + 1 :]
                result = html.unescape(get_answer(query, self.key))
                self.privmsg(server, channel, result)
            except:
                logging.exception("Unable to query")


if __name__ == "__main__":
    sys.exit(Wolfram.run())
