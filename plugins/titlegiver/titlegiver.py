import sys
import plugin
import re
import urllib2
from utils import url_parser

from twisted.python import log

title_re = re.compile(r'<title>(.*?)</title>', re.IGNORECASE)

class Titlegiver(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "Titlegiver")

    @staticmethod
    def find_title_url(url):
        return Titlegiver.find_title(urllib2.urlopen(url).read())

    @staticmethod
    def find_title(text):
        return title_re.search(text).group(1)

    def privmsg(self, server_id, user, channel, message):
        for url in url_parser.find_urls(message):
            try:
                self.say(server_id, channel, Titlegiver.find_title_url(url))
            except:
                log.msg("Unable to find title for:", url)

if __name__ == "__main__":
    sys.exit(Titlegiver.run())

