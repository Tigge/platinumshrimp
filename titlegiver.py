import plugin
import re
import urllib2
from utils import url_parser

title_re = re.compile(r'<title>([^(?!<)]*)</title>', re.IGNORECASE)

class Titlegiver(plugin.Plugin):
    def _findTitle(self, text):
        return title_re.search(text).group(1)

    def privmsg(self, user, channel, message):
        for url in url_parser.FindUrls(message):
            try:
                print self._findTitle(urllib2.urlopen(url).read())
            except:
                print "Unable to find title for: {}".format(url)

Titlegiver.run()
