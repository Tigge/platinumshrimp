from __future__ import division, absolute_import, print_function, unicode_literals

import datetime

from twisted.trial import unittest

from utils import date_utils


class TestDateUtils(unittest.TestCase):

    def test_seconds(self):

        date_old = datetime.datetime(2009, 02, 01, 16, 35, 23)
        date_new = datetime.datetime(2009, 02, 01, 16, 35, 25)
        string = date_utils.format(date_old, date_new)
        self.assertTrue(string, "2 seconds ago")

    def test_minutes(self):
        date_old = datetime.datetime(2009, 02, 01, 16, 35, 23)
        date_new = datetime.datetime(2009, 02, 01, 16, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertTrue(string, "3 minute ago")

    def test_hours(self):
        date_old = datetime.datetime(2009, 02, 01, 16, 35, 23)
        date_new = datetime.datetime(2009, 02, 01, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertTrue(string, "1 hour ago")

    def test_days(self):
        date_old = datetime.datetime(2009, 02, 01, 16, 35, 23)
        date_new = datetime.datetime(2009, 02, 07, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertTrue(string, "6 days ago")

    def test_months(self):
        date_old = datetime.datetime(2009, 02, 01, 16, 35, 23)
        date_new = datetime.datetime(2009, 07, 07, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertTrue(string, "5 month ago")

    def test_years(self):
        date_old = datetime.datetime(2009, 02, 01, 16, 35, 23)
        date_new = datetime.datetime(2015, 07, 07, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertTrue(string, "6 years ago")