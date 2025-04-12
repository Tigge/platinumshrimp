# coding=utf-8
import threading
import urllib
import os
import json
import urllib.parse
import unittest
import http.server

from plugins.titlegiver.titlegiver import Titlegiver

__author__ = "tigge"
__author__ = "reggna"


class Handler(http.server.BaseHTTPRequestHandler):
    def redirect(self):
        count = int(self.url_queries["count"][0])
        url = self.url_queries["url"][0]
        if count > 1:
            url = "redirect?count={0}&url={1}".format(count - 1, self.url_queries["url"][0])

        self.send_response(301)
        self.send_header("Location", url)
        self.end_headers()

        self.wfile.write(
            "<html><head><title>Redirect</title></head><body>See {0}</body></html>".format(
                url
            ).encode("utf-8")
        )

    def page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            "<html><head><title>Simple</title></head><body>Simple</body></html>".encode("utf-8")
        )

    def pages(self):
        self.send_response(200)
        dir = os.path.join("..", os.path.dirname(__file__))

        # Read headers from JSON dict, .headers extension
        try:
            with open(dir + "/" + urllib.parse.unquote(self.path) + ".header") as fp:
                for header, value in json.load(fp).items():
                    self.send_header(header, value)

        # Default headers, if not found
        except IOError:
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        ip = "localhost:{}".format(self.server.server_port).encode("ascii")

        with open(dir + "/" + urllib.parse.unquote(self.path), "br") as fp:
            self.wfile.write(fp.read().replace("$ADDRESS".encode("ascii"), ip))

    def do_GET(self):

        self.url_parts = urllib.parse.urlparse(self.path)
        self.url_queries = urllib.parse.parse_qs(self.url_parts.query)

        if self.url_parts.path == "/redirect":
            self.redirect()
        elif self.url_parts.path == "/page":
            self.page()
        elif self.url_parts.path.startswith("/pages"):
            self.pages()

    def log_message(self, format, *args):
        return


class TitlegiverTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http_server = http.server.HTTPServer(("", 0), Handler)
        cls.http_server_thread = threading.Thread(target=cls.http_server.serve_forever)
        cls.http_server_thread.start()
        cls.URL = "http://localhost:{}".format(cls.http_server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()
        cls.http_server.server_close()
        cls.http_server_thread.join()

    def test_redirect(self):
        url = self.URL + "/page"
        result = Titlegiver.get_title_from_url(self.URL + "/redirect?count=10&url={0}".format(url))
        self.assertEqual(result, "Simple")

    def test_meta_redirect(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/meta_redirect")
        self.assertEqual(result, "Simple")

    def test_meta_redirect_in_noscript(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/meta_redirect_in_noscript")
        self.assertEqual(result, "Title without refreshing")

    def test_specialchars(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/specialchar")
        self.assertEqual(
            result,
            "Title with special characters §½!\"@#£¤$%&/{([)]=}+?\`´'^~*'<>|,;.:-_",
        )

    def test_linebreaks(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/linebreaks")
        self.assertEqual(result, "Title with line breaks and carriage returns")

    def test_attributes(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/attributes")
        self.assertEqual(result, 'Title with attribute id="pageTitle"')

    def test_entities(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/entities")
        self.assertEqual(
            result,
            "Title with entities. "
            'XML: "& '
            "HTML: <Å©†♥ "
            "Int/hex: Hello "
            "Invalid: &#x23k;&#123456789;&fail;",
        )

    def test_nonascii(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/nönàscii")
        self.assertEqual(result, "Page with nön-àscii path")

    def test_encoding_bom(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/encoding_bom")
        self.assertEqual(result, "Gådzölla - ゴジラ")

    def test_encoding_xmldecl(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/encoding_xmldecl")
        self.assertEqual(result, "Samoraj - 武家")

    def test_encoding_meta_charset(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/encoding_meta_charset")
        self.assertEqual(result, "Россия-Матушка")

    def test_encoding_meta_httpequiv(self):
        result = Titlegiver.get_title_from_url(self.URL + "/pages/encoding_meta_httpequiv")
        self.assertEqual(result, "올드보이")

    def test_split_strip_and_slice(self):
        title = Titlegiver.get_title_from_url(self.URL + "/pages/linebreaks_with_cr")
        result = Titlegiver.split_strip_and_slice(title, 2)
        self.assertEqual(result, ["Line1", "Line2"])
