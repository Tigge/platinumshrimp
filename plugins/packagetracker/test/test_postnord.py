# coding=utf-8

import os
import unittest
import requests_mock

from unittest import mock

from plugins.packagetracker.provider_postnord import PostnordPackage

__author__ = "tigge"


class PostnordTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = os.path.join("..", os.path.dirname(__file__))

    @requests_mock.mock()
    def test_package_format(self, mock_requests):
        PostnordPackage.set_apikey("FAKE_APIKEY")
        package = PostnordPackage("FAKE_ID")

        with open(os.path.join(self.dir, "postnord_package.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())
        package.update()

        self.assertEqual(package.id, "FAKE_ID")
        self.assertEqual(package.consignee, "22738 LUND, Sweden")
        self.assertEqual(
            package.consignor,
            "Dustin Sverige, Metallvägen 36, 19572 Rosersberg, Sweden",
        )

        package2 = PostnordPackage("FAKE_ID")
        with open(os.path.join(self.dir, "postnord_package2.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())
        package2.update()

        self.assertEqual(package2.id, "FAKE_ID")
        self.assertEqual(package2.consignee, "41762")
        self.assertEqual(package2.consignor, "CDON.COM")

        package3 = PostnordPackage("FAKE_ID2")

        with open(os.path.join(self.dir, "postnord_package_import.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID2"), text=f.read())
        package3.update()

        self.assertEqual(package3.id, "FAKE_ID2")
        self.assertEqual(package3.consignee, "41327 GÖTEBORG, Sweden")
        self.assertEqual(
            package3.consignor, "Posten Logistik AB / IMPORT, 10500 STOCKHOLM"
        )

    @requests_mock.mock()
    def test_is_package(self, mock_requests):
        PostnordPackage.set_apikey("FAKE_APIKEY")

        with open(os.path.join(self.dir, "postnord_invalid_id.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())
        self.assertFalse(PostnordPackage.is_package("FAKE_ID"))

        with open(os.path.join(self.dir, "postnord_no_package.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())
        self.assertFalse(PostnordPackage.is_package("FAKE_ID"))

        with open(os.path.join(self.dir, "postnord_broken_package.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())
        self.assertFalse(PostnordPackage.is_package("FAKE_ID"))

        with open(os.path.join(self.dir, "postnord_package.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())
        self.assertTrue(PostnordPackage.is_package("FAKE_ID"))

    @requests_mock.mock()
    def test_fetch(self, mock_requests):
        PostnordPackage.set_apikey("FAKE_APIKEY")
        package = PostnordPackage("FAKE_ID")
        package.on_event = mock.MagicMock()

        with open(os.path.join(self.dir, "postnord_package_event1.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())

        package.update()
        self.assertEqual(
            package.on_event.call_args[0][0].description,
            "The electronic shipping instructions have been received (Dustin Sverige)",
        )
        self.assertEqual(package.on_event.call_count, 1)

        with open(os.path.join(self.dir, "postnord_package_event2.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())

        package.update()
        self.assertEqual(
            package.on_event.call_args[0][0].description,
            "The shipment item is under transportation (Veddesta)",
        )
        self.assertEqual(package.on_event.call_count, 2)

    @requests_mock.mock()
    def test_fetch_broken(self, mock_requests):
        PostnordPackage.set_apikey("FAKE_APIKEY")
        package = PostnordPackage("FAKE_ID")

        with open(os.path.join(self.dir, "postnord_broken_package.json"), "r") as f:
            mock_requests.get(PostnordPackage._get_url("FAKE_ID"), text=f.read())

        package.update()
