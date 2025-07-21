import logging
import sys
import html
import json
import requests
import urllib.parse
import xml.etree.ElementTree as ET

import plugin
from utils import str_utils

API_URL = "http://api.wolframalpha.com/v2/query?appid={key}&input={query}&format=plaintext"


def get_answer(query, key):
    query = urllib.parse.quote(query)
    url = API_URL.format(key=key, query=query)
    try:
        response = requests.get(url)
        if not response.ok:
            return None
        root = ET.fromstring(response.content)
    except Exception:
        logging.exception("Unable to query or parse Wolfram response")
        return None

    if root.attrib.get("success") != "true":
        return None

    # Priority 1: primary pods
    for pod in root.findall("pod"):
        if pod.attrib.get("primary") == "true":
            plaintext = pod.find(".//plaintext")
            if plaintext is not None and plaintext.text:
                return str_utils.sanitize_string(plaintext.text)

    # Priority 2: pods with specific titles
    target_titles = ["Result", "Value", "Decimal approximation"]
    for title in target_titles:
        for pod in root.findall("pod"):
            if pod.attrib.get("title") == title:
                plaintext = pod.find(".//plaintext")
                if plaintext is not None and plaintext.text:
                    return str_utils.sanitize_string(plaintext.text)

    return None


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
                if not query:
                    return
                answer = get_answer(query, self.key)
                if answer:
                    result = html.unescape(answer)
                    self.privmsg(server, channel, result)
            except:
                logging.exception("Unable to query")


if __name__ == "__main__":
    sys.exit(Wolfram.run())
