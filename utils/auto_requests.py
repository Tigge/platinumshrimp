import codecs
import html.parser
import httpx
import re

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
                ):
                    match = re.search(r"^.*?charset=([a-zA-Z0-9-_]+)$", attributes["content"])
                    self.charset = match.group(1) if match is not None else None

    parser = MyHTMLParser()
    parser.feed(response.content[:1024].decode("ascii", "ignore"))  # As per HTML5 standard
    return parser.charset


def _request(method, url, *args, **kwargs):
    # TODO: Should we redirect on all refreshs, or only the ones with zero timeout?
    # TODO: Should we check for http-equiv="refresh"?
    no_script_re = re.compile(r"<noscript.*?<\/noscript>", re.IGNORECASE)
    redirect_re = re.compile(r'<meta[^>]*?url=(.*?)["\']', re.IGNORECASE)
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
            if method == "get":
                response = client.get(url, follow_redirects=True)
            elif method == "post":
                content = kwargs.get("content", "")
                response = client.post(url, follow_redirects=True, content=content)
            else:
                raise ValueError(f"Unsupported method: {method}")

            encoding = find_encoding(response)
            response.encoding = encoding or response.encoding or "utf-8"
            text = no_script_re.sub("", response.text)
            match = redirect_re.search(text)

            if not match or nr_redirects > 10:
                return response

            url = match.groups()[0].strip()
            nr_redirects += 1
    # All dangling connections are closed here, so we don't need to close anything anywhere else


def get(url, *args, **kwargs):
    return _request("get", url, *args, **kwargs)


def post(url, *args, **kwargs):
    return _request("post", url, *args, **kwargs)
