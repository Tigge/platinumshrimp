# coding=utf-8

from __future__ import division, absolute_import, print_function, unicode_literals

import json
import os

import mock

from twisted.trial import unittest
from plugins.packagetracker.provider_postnord import PostnordPackage

__author__ = 'tigge'


class PostnordTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(PostnordTestCase, self).__init__(*args, **kwargs)
        self.dir = os.path.join("..", os.path.dirname(__file__))

    @mock.patch.object(PostnordPackage, '_get_data')
    def test_package_format(self, mock_get_data):
        PostnordPackage.set_apikey("FAKE_APIKEY")
        package = PostnordPackage("FAKE_ID")

        mock_get_data.return_value = json.load(open(os.path.join(self.dir, "postnord_package.json")))
        package.update()
        self.assertEqual(mock_get_data.call_count, 1)

        self.assertEqual(package.id, "FAKE_ID")
        self.assertEqual(package.consignee, "22738 LUND, Sweden")
        self.assertEqual(package.consignor, "Dustin Sverige, Metallvägen 36, 19572 Rosersberg, Sweden")

    @mock.patch.object(PostnordPackage, '_get_data')
    def test_is_package(self, mock_get_data):
        PostnordPackage.set_apikey("FAKE_APIKEY")

        mock_get_data.return_value = json.load(open(os.path.join(self.dir, "postnord_invalid_id.json"), "r"))
        self.assertFalse(PostnordPackage.is_package("FAKE_ID"))

        mock_get_data.return_value = json.load(open(os.path.join(self.dir, "postnord_no_package.json"), "r"))
        self.assertFalse(PostnordPackage.is_package("FAKE_ID"))

        mock_get_data.return_value = json.load(open(os.path.join(self.dir, "postnord_package.json"), "r"))
        self.assertTrue(PostnordPackage.is_package("FAKE_ID"))

    @mock.patch.object(PostnordPackage, '_get_data')
    def test_fetch(self, mock_get_data):
        PostnordPackage.set_apikey("FAKE_APIKEY")
        package = PostnordPackage("FAKE_ID")
        package.on_event = mock.MagicMock()

        mock_get_data.return_value = json.load(open(os.path.join(self.dir, "postnord_package_event1.json"), "r"))

        package.update()
        self.assertEqual(package.on_event.call_args[0][0].description,
                         "The electronic shipping instructions have been received (Dustin Sverige)")
        self.assertEqual(package.on_event.call_count, 1)

        mock_get_data.return_value = json.load(open(os.path.join(self.dir, "postnord_package_event2.json"), "r"))

        package.update()
        self.assertEqual(package.on_event.call_args[0][0].description,
                         "The shipment item is under transportation (Veddesta)")
        self.assertEqual(package.on_event.call_count, 2)
