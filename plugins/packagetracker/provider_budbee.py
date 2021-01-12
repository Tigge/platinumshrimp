import requests
import datetime
import dateutil
import dateutil.parser
import logging

from plugins.packagetracker.provider import Package

__author__ = "tigge"


class BudbeePackage(Package):
    API_URL = "https://tracking.budbee.com/api/orders/"

    @classmethod
    def get_type(cls):
        return "Budbee"

    @staticmethod
    def create_event(event):
        e = BudbeePackage.Event()
        e.datetime = dateutil.parser.parse(event["date"])
        e.description = f"{event['sender']}: {event['message']}"
        return e

    @classmethod
    def is_package(cls, package_id):
        data = cls._get_data(package_id)
        if "token" in data:
            return True
        return False

    @classmethod
    def _get_url(cls, package_id):
        return BudbeePackage.API_URL + package_id

    @classmethod
    def _get_data(cls, package_id):
        try:
            return requests.get(BudbeePackage._get_url(package_id)).json()
        except ValueError as e:
            logging.exception("Exception while getting package")
            return {}

    def __init__(self, package_id):
        super().__init__(package_id)
        self.last_updated = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

    def update(self):

        data = self._get_data(self.id)

        try:
            self.consignor = data["merchant"]["name"]
            self.consignee = data["consumer"]["name"]
            self.consignee += ", " + data["deliveryAddress"]["street"]
            self.consignee += ", " + data["deliveryAddress"]["postalCode"]
            self.consignee += ", " + data["deliveryAddress"]["city"]

            last_updated = self.last_updated

            for budbee_event in data["events"]:
                event = self.create_event(budbee_event)

                if event.datetime > last_updated:
                    last_updated = event.datetime

                if event.datetime > self.last_updated:
                    self.on_event(event)

            self.last_updated = last_updated

        except Exception as e:
            logging.exception("Exception while updating package")
            logging.debug("Data: %r", data)
