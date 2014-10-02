# coding=utf-8
__author__ = 'tigge'

import urllib
import os
import json

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.server import Request
from twisted.web.resource import Resource
from twisted.trial import unittest
from twisted.internet.threads import deferToThread

from plugins.titlegiver.titlegiver import Titlegiver


class Redirect(Resource):
    isLeaf = True

    def render_GET(self, request):
        assert isinstance(request, Request)
        count = int(request.args["count"][0])
        url = request.args["url"][0]

        if count == 1:
            request.redirect(url)
            return "<html><head><title>Redirect</title></head><body>See {0}</body></html>".format(url)
        else:
            request.redirect("redirect?count={0}&url={1}".format(count - 1, url))
            return "<html><head><title>Redirect</title></head><body>See {0}</body></html>".format(url)


class Page(Resource):
    isLeaf = True

    def render_GET(self, request):
        assert isinstance(request, Request)
        return "<html><head><title>Simple</title></head><body>Simple</body></html>"


class Pages(Resource):
    isLeaf = True

    def __init__(self):
        self.dir = os.path.join("..", os.path.dirname(__file__))

    def render(self, request):
        assert isinstance(request, Request)

        # Read headers from JSON dict, .headers extensions
        try:
            fp = open(self.dir + "/" + urllib.unquote(request.path) + ".header")

            def ascii_encode_dict(data):
                ascii_encode = lambda x: x.encode('ascii')
                return dict(map(ascii_encode, pair) for pair in data.items())

            for header, value in json.load(fp, object_hook=ascii_encode_dict).iteritems():
                request.setHeader(header, value)

        # Default headers, if not found
        except IOError:
            request.setHeader("Content-Type", "text/html; charset=utf-8")

        data = open(self.dir + "/" + urllib.unquote(request.path)).read()
        return data


class Server(Resource):

    def __init__(self):
        Resource.__init__(self)
        self.putChild("redirect", Redirect())
        self.putChild("page", Page())
        self.putChild("pages", Pages())


class TitlegiverTestCase(unittest.TestCase):

    def setUp(self):
        self.port = reactor.listenTCP(8880, Site(Server()))
        self.URL = "http://localhost:8880"

    def tearDown(self):
        self.port.stopListening()

    def test_redirect(self):
        url = self.URL + "/page"
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/redirect?count=10&url={0}".format(url)))
        result.addCallback(self.assertEqual, u"Simple")
        return result

    def test_specialchars(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/specialchar"))
        result.addCallback(self.assertEqual, u"Title with special characters §½!\"@#£¤$%&/{([)]=}+?\`´'^~*'<>|,;.:-_")
        return result

    def test_linebreaks(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/linebreaks"))
        result.addCallback(self.assertEqual, u"Title with line breaks and carriage returns")
        return result

    def test_attributes(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/attributes"))
        result.addCallback(self.assertEqual, u"Title with attribute id=\"pageTitle\"")
        return result

    def test_entities(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/entities"))
        result.addCallback(self.assertEqual, u"Title with entities. "
                                             u"XML: \"& "
                                             u"HTML: <Å©†♥ "
                                             u"Int/hex: Hello "
                                             u"Invalid: &#x23k;&#123456789;&fail;")
        return result

    def test_nonascii(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/nönàscii"))
        result.addCallback(self.assertEqual, u"Page with nön-àscii path")
        return result

    def test_encoding_bom(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/encoding_bom"))
        result.addCallback(self.assertEqual, u"Gådzölla - ゴジラ")
        return result

    def test_encoding_xmldecl(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/encoding_xmldecl"))
        result.addCallback(self.assertEqual, u"Samoraj - 武家")
        return result

    def test_encoding_meta_charset(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/encoding_meta_charset"))
        result.addCallback(self.assertEqual, u"Россия-Матушка")
        return result

    def test_encoding_meta_httpequiv(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/pages/encoding_meta_httpequiv"))
        result.addCallback(self.assertEqual, u"올드보이")
        return result
