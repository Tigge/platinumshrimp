import requests
import datetime
import dateutil
import dateutil.parser
import logging

from plugins.packagetracker.provider import Package

__author__ = "tigge"


class DHLPackage(Package):
    API_URL = "https://api-eu.dhl.com/track/shipments?trackingNumber="

    apikey = None

    @classmethod
    def get_type(cls):
        return "DHL"

    @classmethod
    def set_apikey(cls, id):
        cls.apikey = id

    @staticmethod
    def create_event(event):
        e = DHLPackage.Event()
        e.datetime = dateutil.parser.parse(event["timestamp"])
        e.description = f"{event['location']['address']['addressLocality']}: {event['description']}"
        return e

    @classmethod
    def is_package(cls, package_id):
        data = cls._get_data(package_id)
        if "shipments" in data and len(data["shipments"]) > 0:
            return True
        return False

    @classmethod
    def _get_url(cls, package_id):
        return DHLPackage.API_URL + package_id

    @classmethod
    def _get_data(cls, package_id):
        try:
            return requests.get(
                DHLPackage._get_url(package_id),
                headers={
                    "Accept": "application/json",
                    "DHL-API-Key": DHLPackage.apikey,
                },
            ).json()
        except ValueError as e:
            logging.exception("Exception while getting package")
            return {}

    def update(self):

        data = self._get_data(self.id)

        try:

            for dhl_shipment in data["shipments"]:

                self.consignor = dhl_shipment["origin"]["address"]["addressLocality"]
                self.consignee = dhl_shipment["destination"]["address"]["addressLocality"]

                last_updated = self.last_updated

                for dhl_event in dhl_shipment["events"]:
                    event = self.create_event(dhl_event)

                    if event.datetime > last_updated:
                        last_updated = event.datetime

                    if event.datetime > self.last_updated:
                        self.on_event(event)

                self.last_updated = last_updated

        except Exception as e:
            logging.exception("Exception while updating package")
            logging.debug("Data: %r", data)
