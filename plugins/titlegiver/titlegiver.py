import plugin
import re
import urllib2
from utils import url_parser

from twisted.python import log

title_re = re.compile(r'<title>([^(?!<)]*)</title>', re.IGNORECASE)

class Titlegiver(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "Titlegiver")

    def _findTitle(self, text):
        return title_re.search(text).group(1)

    def privmsg(self, server_id, user, channel, message):
        for url in url_parser.find_urls(message):
            try:
                self.say(server_id, channel, self._findTitle(urllib2.urlopen(url).read()))
            except:
                log.msg("Unable to find title for:", url)

Titlegiver.run()
