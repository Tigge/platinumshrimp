import requests
import datetime
import dateutil
import dateutil.parser
import logging

from plugins.packagetracker.provider import Package

__author__ = "reeen"


# Bring API https://developer.bring.com/api/tracking/
class BringPackage(Package):
    API_URL = "https://tracking.bring.com/api/v2/tracking.json"

    @classmethod
    def get_type(cls):
        return "Bring"

    @staticmethod
    def strip_tags(text):
        clean = re.compile("<.*?>")
        return re.sub(clean, "", text)

    @staticmethod
    def create_event(event):
        e = BringPackage.Event()
        e.datetime = dateutil.parser.isoparse(event["dateIso"])
        e.description = f"{event['city']}: {strip_tags(event['description'])}"
        return e

    @classmethod
    def is_package(cls, package_id):
        data = cls._get_data(package_id)
        if not "error" in data["consignmentSet"][0]:
            return True
        return False

    @classmethod
    def _get_url(cls, package_id):
        return BringPackage.API_URL + "?q=" + package_id

    @classmethod
    def _get_data(cls, package_id):
        try:
            return requests.get(
                BringPackage._get_url(package_id),
                # More headers are listed as required, but that is only for the registered API end-point
                headers={
                    "X-Bring-Client-URL": "https://github.com/Tigge/platinumshrimp",
                },
            ).json()
        except ValueError as e:
            logging.exception("Exception while getting package")
            return {}

    def __init__(self, package_id):
        super().__init__(package_id)
        self.last_updated = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

    def update(self):

        data = self._get_data(self.id)

        # Note: will only look at first consignment and package in data
        try:
            self.consignor = data["consignmentSet"][0]["senderName"]
            self.consignee = data["consignmentSet"][0]["recipientAddress"]["postalCode"]
            self.consignee += (
                " " + data["consignmentSet"][0]["recipientAddress"]["city"]
            )

            last_updated = self.last_updated

            for bring_event in data["consignmentSet"][0]["packageSet"][0]["eventSet"]:
                event = self.create_event(bring_event)

                if event.datetime > last_updated:
                    last_updated = event.datetime

                if event.datetime > self.last_updated:
                    self.on_event(event)

            self.last_updated = last_updated

        except Exception as e:
            logging.exception("Exception while updating package")
            logging.debug("Data: %r", data)
