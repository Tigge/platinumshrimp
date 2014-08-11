__author__ = 'tigge'

import os

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.trial import unittest
from twisted.internet.threads import deferToThread

from plugins.titlegiver.titlegiver import Titlegiver


class Server(Resource):

    isLeaf = True

    def render_GET(self, request):
        return "<html><head><title>Simple</title></head><body>Simple</body></html>"


class TitlegiverTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = os.path.join("..", os.path.dirname(__file__))

        self.port = reactor.listenTCP(8880, Site(Server()))
        self.URL = "http://localhost:8880"

    def tearDown(self):
        self.port.stopListening()

    def test_redirect(self):
        result = deferToThread(Titlegiver.find_title_url, (self.URL + "/simple"))
        result.addCallback(self.assertEqual, "Simple")
        return result
