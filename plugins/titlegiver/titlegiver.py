import htmlentitydefs
import re
import sys

from twisted.python import log

import plugin
from utils import url_parser, auto_requests

class Titlegiver(plugin.Plugin):

    TITLE_REGEX = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
    WHITESPACE_REGEX = re.compile(r'\s+')

    MAX_CONTENT_LENGTH = 64 * 1024

    def __init__(self):
        plugin.Plugin.__init__(self, "Titlegiver")

    @staticmethod
    def get_title_from_url(url):
        # Fetch page (no need to verfiy SSL certs for titles)
        response = auto_requests.get(url, verify=False)
        content = response.text[:Titlegiver.MAX_CONTENT_LENGTH]

        # Avoid leaving dangling redirects when we've got the content
        response.connection.close()

        return Titlegiver.find_title_in_content(content).strip()

    @staticmethod
    def find_title_in_content(text):
        try:
            title = Titlegiver.WHITESPACE_REGEX.sub(" ", Titlegiver.TITLE_REGEX.search(text).group(1))
            return Titlegiver.unescape_entities(title)
        except:
            log.err()
            return None

    @staticmethod
    def unescape_entities(text):
        def replace_entity(match):
            try:
                if match.group(1) in htmlentitydefs.name2codepoint:
                    return unichr(htmlentitydefs.name2codepoint[match.group(1)])
                elif match.group(1).lower().startswith("#x"):
                    return unichr(int(match.group(1)[2:], 16))
                elif match.group(1).startswith("#"):
                    return unichr(int(match.group(1)[1:]))
            except (ValueError, KeyError):
                pass  # Fall through to default return
            return match.group(0)

        return re.sub(r'&([#a-zA-Z0-9]+);', replace_entity, text)

    def privmsg(self, server, user, channel, message):
        for url in url_parser.find_urls(message):
            try:
                self.say(server, channel, Titlegiver.get_title_from_url(url))
            except:
                log.msg("Unable to find title for:", url)
                log.err()


if __name__ == "__main__":
    sys.exit(Titlegiver.run())
