# coding=utf-8

import datetime
import logging
import requests

import xml.etree.ElementTree as etree

from plugins.packagetracker.provider import Package

__author__ = "tigge"


class SchenkerPackage(Package):
    API_URL = "http://privpakportal.schenker.nu"
    FIND_IDENTIFIER = API_URL + "/TrackAndTrace/packagexml.aspx?packageid={id}"

    @classmethod
    def get_type(cls):
        return "Schenker"

    @staticmethod
    def create_event(event):
        e = SchenkerPackage.Event()
        datestring = event.find("date").text + " " + event.find("time").text
        e.datetime = datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M")
        e.description = event.find("description").text
        return e

    @classmethod
    def is_package(cls, package_id):
        try:
            res = cls._get_data(package_id)
            return res.find("body/programevent") is None
        except Exception as e:
            logging.exception("Exception on SchenkerPackage.is_package")
            return False

    @classmethod
    def _get_url(cls, package_id):
        return SchenkerPackage.FIND_IDENTIFIER.format(id=package_id)

    @classmethod
    def _get_data(cls, package_id):
        response = requests.get(SchenkerPackage._get_url(package_id), allow_redirects=False)
        if response.status_code == 200:
            return etree.fromstring(response.content)
        else:
            raise Exception("Redirected away")

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
