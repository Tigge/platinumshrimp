# coding=utf-8

from __future__ import division, absolute_import, print_function, unicode_literals
import requests
import dateutil
import dateutil.parser

from plugins.packagetracker.packagetracker import Package


__author__ = 'tigge'


class PostnordPackage(Package):
    API_URL = "https://api2.postnord.com"
    FIND_IDENTIFIER = (API_URL + "/rest/shipment/v1/trackandtrace/findByIdentifier.json" +
                       "?id={id}&locale={locale}&apikey={apikey}")

    apikey = None

    @classmethod
    def set_apikey(cls, id):
        cls.apikey = id

    @staticmethod
    def format_address(address):
        result = ""
        if "street1" in address:
            result += address["street1"]
        if "street2" in address:
            result += ", " + address["street2"]
        if len(result) > 0:
            result += ", "
        result += address["postCode"] + " " + address["city"]
        result += ", " + address["country"]
        return result

    @staticmethod
    def create_event(event):
        e = PostnordPackage.Event()
        e.datetime = dateutil.parser.parse(event["eventTime"])
        e.description = "{0} ({1})".format(event["eventDescription"], event["location"]["displayName"])
        return e

    @classmethod
    def is_package(cls, package_id):
        data = cls._get_data(package_id)
        if "TrackingInformationResponse" in data:
            if "shipments" in data["TrackingInformationResponse"]:
                if len(data["TrackingInformationResponse"]["shipments"]) > 0:
                    return True
        return False


    @classmethod
    def _get_data(cls, package_id, locale="en"):
        url = PostnordPackage.FIND_IDENTIFIER.format(id=package_id, locale=locale, apikey=PostnordPackage.apikey)
        return requests.get(url).json()

    def update(self):

        res = self._get_data(self.id)

        data = res["TrackingInformationResponse"]

        for shipment in data["shipments"]:
            self.service = shipment["service"]["name"]
            self.consignor = shipment["consignor"]["name"] + ", " + PostnordPackage.format_address(
                shipment["consignor"]["address"])
            self.consignee = PostnordPackage.format_address(shipment["consignee"]["address"])

            self.weight = shipment["totalWeight"]["value"] + " " + shipment["totalWeight"]["unit"]
            self.volume = shipment["totalVolume"]["value"] + " " + shipment["totalVolume"]["unit"]

            self.status = shipment["statusText"]["header"] + ": " + shipment["statusText"]["body"]

            last_updated = self.last_updated

            for postnord_item in shipment["items"]:

                for postnord_event in postnord_item["events"]:
                    event = self.create_event(postnord_event)

                    if event.datetime > last_updated:
                        last_updated = event.datetime

                    if event.datetime > self.last_updated:
                        self.on_event(PostnordPackage.create_event(postnord_event))

            self.last_updated = last_updated
