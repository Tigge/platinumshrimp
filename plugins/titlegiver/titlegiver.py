import sys
import re
import urllib2
import urlparse
import htmlentitydefs

from twisted.python import log

import plugin
from utils import url_parser


class Titlegiver(plugin.Plugin):

    TITLE_REGEX = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
    WHITESPACE_REGEX = re.compile(r'\s+')

    def __init__(self):
        plugin.Plugin.__init__(self, "Titlegiver")

    @staticmethod
    def idnaify(url):
        parts = urlparse.urlsplit(url)
        netloc = parts.netloc.encode('idna')
        return urlparse.urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

    @staticmethod
    def find_title_url(url):
        url = url.decode('utf-8') if isinstance(url, str) else url # TODO: move to bot
        data = urllib2.urlopen(Titlegiver.idnaify(url)).read().decode('utf-8')
        return Titlegiver.find_title(data).strip()

    @staticmethod
    def find_title(text):
        return Titlegiver.unescape_entities(Titlegiver.WHITESPACE_REGEX.sub(" ", Titlegiver.TITLE_REGEX.search(text).group(1)))

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

    def privmsg(self, server_id, user, channel, message):
        for url in url_parser.find_urls(message):
            try:
                self.say(server_id, channel, Titlegiver.find_title_url(url).encode("utf-8"))
            except:
                log.msg("Unable to find title for:", url)
                log.err()


if __name__ == "__main__":
    sys.exit(Titlegiver.run())
