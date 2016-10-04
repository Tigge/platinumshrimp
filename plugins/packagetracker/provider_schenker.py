# coding=utf-8

import datetime
import logging
import requests

import xml.etree.ElementTree as etree

from plugins.packagetracker.provider import Package

__author__ = 'tigge'


class SchenkerPackage(Package):
    API_URL = "http://privpakportal.schenker.nu"
    FIND_IDENTIFIER = API_URL + "/TrackAndTrace/packagexml.aspx?packageid={id}"

    @staticmethod
    def create_event(event):
        e = SchenkerPackage.Event()
        datestring = event.find("date").text + " " + event.find("time").text
        e.datetime = datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M")
        e.description = event.find("description").text
        return e

    @classmethod
    def is_package(cls, package_id):
        data = cls._get_data(package_id)
        return data.find("body/programevent") is None

    @classmethod
    def _get_url(cls, package_id):
        return SchenkerPackage.FIND_IDENTIFIER.format(id=package_id)

    @classmethod
    def _get_data(cls, package_id):
        response = requests.get(SchenkerPackage._get_url(package_id))
        return etree.fromstring(response.content)

    def update(self):

        try:
            res = self._get_data(self.id)
            parcel = res.find("body/parcel")

            self.service = "Schenker"

            self.consignor = parcel.find("customername").text
            self.consignee = parcel.find("receiverzipcode").text + parcel.find("receivercity").text

            self.totalWeight = parcel.find("actualweight").text

            last_updated = self.last_updated

            for schenker_event in parcel.findall("event"):
                event = self.create_event(schenker_event)

                if event.datetime > last_updated:
                    last_updated = event.datetime

                if event.datetime > self.last_updated:
                    self.on_event(event)

            self.last_updated = last_updated

        except Exception as e:
            logging.exception("Exception while updating package")
            logging.debug("Data: %r", res)
