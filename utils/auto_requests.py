import cgi
import codecs
import HTMLParser
import re
import requests


def encoding_from_bom(string):
    if string.startswith(codecs.BOM_UTF8):
        return "utf-8"
    elif string.startswith(codecs.BOM_UTF16_LE):
        return "utf_16_le"
    elif string.startswith(codecs.BOM_UTF16_BE):
        return "utf_16_be"
    else:
        return None

def find_encoding(response):
    # 1. Byte Order Mark
    bom_encoding = encoding_from_bom(response.content[:16])
    if bom_encoding is not None:
        return bom_encoding

    # 2. Content-Type
    if 'content-type' in response.headers:
        content_type, params = cgi.parse_header(response.headers.get('content-type'))
        if 'charset' in params:
            return params['charset'].strip("'\"")

    # 3. XML declaration
    xmldecl_regex = re.compile(
        r'<\?xml(?:.*?)encoding=(?:"|\')([a-zA-Z0-9-_]+)(?:"|\')(?:.*?)\?>',
        re.IGNORECASE | re.DOTALL)
    xmldecl = xmldecl_regex.search(response.content[:1024])
    if xmldecl is not None:
        return xmldecl.group(1).lower()

    # 4. Meta http-equiv
    # 5. Meta charset
    class MyHTMLParser(HTMLParser.HTMLParser):

        def __init__(self):
            HTMLParser.HTMLParser.__init__(self)
            self.charset = None

        def handle_starttag(self, tag, attrs):
            if tag == "meta" and self.charset is None:
                attributes = dict(attrs)
                if "charset" in attributes:
                    self.charset = attributes["charset"]
                elif "http-equiv" in attributes and attributes["http-equiv"].lower() == "content-type":
                    match = re.search(r'^.*?charset=([a-zA-Z0-9-_]+)$', attributes["content"])
                    self.charset = match.group(1) if match is not None else None

    parser = MyHTMLParser()
    parser.feed(response.content[:1024])  # As per HTML5 standard
    return parser.charset

def get(*args, **kwargs):
    response = requests.get(*args, **kwargs)
    response.encoding = find_encoding(response)
    return response

