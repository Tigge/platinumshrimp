import codecs
import html
import html.parser
import httpx
import re
import urllib.parse

from datetime import datetime
from email.message import Message


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
    if "content-type" in response.headers:
        message = Message()
        message["content-type"] = response.headers.get("content-type", "")
        params = dict(message.get_params())
        if "charset" in params:
            return params["charset"].strip("'\"")

    # 3. XML declaration
    xmldecl_regex = re.compile(
        rb'<\?xml(?:.*?)encoding=(?:"|\')([a-zA-Z0-9-_]+)(?:"|\')(?:.*?)\?>',
        re.IGNORECASE | re.DOTALL,
    )
    xmldecl = xmldecl_regex.search(response.content[:1024])
    if xmldecl is not None:
        return xmldecl.group(1).lower().decode("ascii")

    # 4. Meta http-equiv "content-type"
    # 5. Meta charset
    class MyHTMLParser(html.parser.HTMLParser):
        def __init__(self):
            html.parser.HTMLParser.__init__(self)
            self.charset = None

        def handle_starttag(self, tag, attrs):
            if tag == "meta" and self.charset is None:
                attributes = dict(attrs)
                if "charset" in attributes:
                    self.charset = attributes["charset"]
                elif (
                    "http-equiv" in attributes
                    and attributes["http-equiv"].lower() == "content-type"
                    and "content" in attributes
                ):
                    match = re.search(r"^.*?charset=([a-zA-Z0-9-_]+)$", attributes["content"])
                    self.charset = match.group(1) if match is not None else None

    parser = MyHTMLParser()
    parser.feed(response.content[:1024].decode("ascii", "ignore"))  # As per HTML5 standard
    return parser.charset


def get(url, *args, **kwargs):
    # TODO: Should we redirect on all refreshs, or only the ones with zero timeout?
    no_script_re = re.compile(r"<noscript.*?<\/noscript>", re.IGNORECASE)
    nr_redirects = 0

    headers = kwargs.pop("headers", {})
    # Rough calculation of the latest firefox version, released every 4 weeks
    ff_version = 140 + ((datetime.today() - datetime(2025, 7, 7)).days // 28)
    default_headers = {
        "User-Agent": f"Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/{ff_version}.0",
        "Accept-Language": "en-US",
        "Sec-GPC": "1",
        "Accept-Encoding": "gzip, deflate",  # Might consider adding br here to handle Brotli
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    final_headers = {**default_headers, **headers}  # Combine defaults with given headers
    final_verify = kwargs.get("verify", True)

    with httpx.Client(http2=True, headers=final_headers, verify=final_verify) as client:
        while True:
            response = client.get(url, follow_redirects=True)
            content_type = response.headers.get("content-type", "")
            # Should we consider removing this?
            if not content_type.startswith("text/html"):
                return ""

            encoding = find_encoding(response)
            response.encoding = encoding or response.encoding or "utf-8"

            # Technically, we're not doing this correctly.  We're ignoring meta tags that appear
            # in noscript tags while, according to the spec, we should still adhear to them (as
            # we're not executing scripts).  However, I want to remember that we added this a long
            # time ago as there were some pages breaking if you don't support scripts.  But we don't
            # care if a page works or not, we just want the data as a regular browser would.
            text_wo_noscript = no_script_re.sub("", response.text)

            # Only follow meta redirects if http-equiv="refresh" is present
            match = None
            for tag in re.findall(r"<meta[^>]*>", text_wo_noscript, re.IGNORECASE | re.DOTALL):
                if re.search(r'http-equiv=["\']refresh["\']', tag, re.IGNORECASE):
                    # Found a refresh tag, now extract the URL from the content attribute
                    url_match = re.search(r"url=(.*?)[\"']", tag, re.IGNORECASE)
                    if url_match:
                        match = url_match
                        break

            if not match or nr_redirects > 10:
                return response

            url = html.unescape(match.groups()[0].strip())
            url = urllib.parse.urljoin(str(response.url), url)
            nr_redirects += 1
    # All dangling connections are closed here, so we don't need to close anything anywhere else
