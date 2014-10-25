import sys
import re
import htmlentitydefs
import codecs
import HTMLParser
import cgi
import time

import requests
from twisted.python import log

import plugin
from utils import url_parser


class Titlegiver(plugin.Plugin):

    TITLE_REGEX = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
    WHITESPACE_REGEX = re.compile(r'\s+')
    XMLDECL_REGEX = re.compile(r'<\?xml(?:.*?)encoding=(?:"|\')([a-zA-Z0-9-_]+)(?:"|\')(?:.*?)\?>',
                               re.IGNORECASE | re.DOTALL)

    MAX_CONTENT_LENGTH = 4096

    def __init__(self):
        plugin.Plugin.__init__(self, "Titlegiver")

    @staticmethod
    def encoding_from_bom(string):
        if string.startswith(codecs.BOM_UTF8):
            return "utf-8"
        elif string.startswith(codecs.BOM_UTF16_LE):
            return "utf_16_le"
        elif string.startswith(codecs.BOM_UTF16_BE):
            return "utf_16_be"
        else:
            return None

    @staticmethod
    def find_encoding(request):
        # 1. Byte Order Mark
        bom_encoding = Titlegiver.encoding_from_bom(request.content[:16])
        if bom_encoding is not None:
            return bom_encoding

        # 2. Content-Type
        if 'content-type' in request.headers:
            content_type, params = cgi.parse_header(request.headers.get('content-type'))
            if 'charset' in params:
                return params['charset'].strip("'\"")

        # 3. XML declaration
        xmldecl = Titlegiver.XMLDECL_REGEX.search(request.content[:1024])
        if xmldecl is not None:
            return xmldecl.group(1).lower()

        # 4. Meta http-equiv
        # 5. Meta charset
        class MyHTMLParser(HTMLParser.HTMLParser):

            def __init__(self):
                HTMLParser.HTMLParser.__init__(self)
                self.charset = None

            def handle_starttag(self, tag, attrs):
                if tag == "meta":
                    if "charset" in attrs:
                        self.charset = attrs["charset"]
                        self.close()
                    elif "http-equiv" in attrs and attrs["http-equiv"].lower() == "content-type":
                        match = re.search(r'^.*?charset=([a-zA-Z0-9-_]+)$', attrs["content"])
                        self.charset = match.group(1) if match is not None else None
                        self.close()

        parser = MyHTMLParser()
        parser.feed(request.content[:1024])  # As per HTML5 standard
        return parser.charset

    @staticmethod
    def find_title_url(url):
        url = url.decode('utf-8') if isinstance(url, str) else url  # TODO: move to bot

        # Fetch page (no need to verfiy SSL certs for titles)
        request = requests.get(url, verify=False)
        request.encoding = Titlegiver.find_encoding(request)

        content = request.text[:Titlegiver.MAX_CONTENT_LENGTH]

        # Avoid leaving dangling redirect requests when we've got the content
        request.connection.close()

        return Titlegiver.find_title(content).strip()

    @staticmethod
    def find_title(text):
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

    def privmsg(self, server_id, user, channel, message):
        for url in url_parser.find_urls(message):
            try:
                self.say(server_id, channel, Titlegiver.find_title_url(url).encode("utf-8"))
            except:
                log.msg("Unable to find title for:", url)
                log.err()


if __name__ == "__main__":
    sys.exit(Titlegiver.run())
