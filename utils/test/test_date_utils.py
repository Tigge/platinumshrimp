import datetime
import unittest

from utils import date_utils


class TestDateUtils(unittest.TestCase):
    def test_seconds(self):

        date_old = datetime.datetime(2009, 2, 1, 16, 35, 23)
        date_new = datetime.datetime(2009, 2, 1, 16, 35, 25)
        string = date_utils.format(date_old, date_new)
        self.assertEqual(string, "2 seconds ago")

    def test_minutes(self):
        date_old = datetime.datetime(2009, 2, 1, 16, 35, 23)
        date_new = datetime.datetime(2009, 2, 1, 16, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertEqual(string, "3 minutes ago")

    def test_hours(self):
        date_old = datetime.datetime(2009, 2, 1, 16, 35, 23)
        date_new = datetime.datetime(2009, 2, 1, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertEqual(string, "1 hour ago")

    def test_days(self):
        date_old = datetime.datetime(2009, 2, 1, 16, 35, 23)
        date_new = datetime.datetime(2009, 2, 5, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertEqual(string, "4 days ago")

    def test_months(self):
        date_old = datetime.datetime(2009, 2, 1, 16, 35, 23)
        date_new = datetime.datetime(2009, 7, 7, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertEqual(string, "5 months ago")

    def test_years(self):
        date_old = datetime.datetime(2009, 2, 1, 16, 35, 23)
        date_new = datetime.datetime(2015, 7, 7, 17, 38, 30)
        string = date_utils.format(date_old, date_new)
        self.assertEqual(string, "6 years ago")
