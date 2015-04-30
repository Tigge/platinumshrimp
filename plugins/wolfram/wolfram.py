import sys
from HTMLParser import HTMLParser

import json
import requests
import urllib
from twisted.python import log

import plugin
from utils import str_utils

RESULT_POD_START = "<pod title='Result"
DECIMAL_APPROXIMATION_POD_START = "<pod title='Decimal approximation'"
RESULT_SUB_POD = "<plaintext>"
API_URL = "http://api.wolframalpha.com/v2/query?appid={key}&input={query}&format=plaintext"

def get_answer(query, key):
    query = urllib.quote(query)
    result = requests.get(API_URL.format(key=key, query=query)).text
    if not RESULT_POD_START in result:
        if not DECIMAL_APPROXIMATION_POD_START in result:
            return
        else:
            result = result[result.index(DECIMAL_APPROXIMATION_POD_START):]
    else:
        result = result[result.index(RESULT_POD_START):]
    if not RESULT_SUB_POD in result:
        return
    result = result[result.index(RESULT_SUB_POD) + len(RESULT_SUB_POD):]
    result = result[:result.index("<")]
    return str_utils.sanitize_string(result)

class Wolfram(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "Wolfram")
        self.key = ""
        self.trigger = ""

    def started(self, settings):
        settings = json.loads(settings)
        self.key = settings["key"] # str
        self.trigger = settings["trigger"] # str

    def privmsg(self, server, user, channel, message):
        if message.startswith(self.trigger):
            try:
                query = message[len(self.trigger) + 1:]
                result = HTMLParser().unescape(get_answer(query, self.key))
                self.say(server, channel, result)
            except:
                log.err()

if __name__ == "__main__":
    sys.exit(Wolfram.run())
