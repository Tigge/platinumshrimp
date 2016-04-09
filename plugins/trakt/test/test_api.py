import json
import unittest
import requests_mock

from api import Trakt


class GetTestCase(unittest.TestCase):
    def setUp(self):
        self.trakt = Trakt("thekey")

    @requests_mock.mock()
    def test_get_valid(self, mock_requests):
        response = "{\"movie_id\": 123}"
        mock_requests.get(Trakt.API_URL, text=response)
        res = self.trakt._to_json(self.trakt._get(""))
        self.assertEqual(res, {"movie_id": 123})

    @requests_mock.mock()
    def test_get_error_code(self, mock_requests):
        mock_requests.get(Trakt.API_URL, text="", status_code=400)
        self.assertRaises(Exception, self.trakt._get, "")

    @requests_mock.mock()
    def test_get_error_json(self, mock_requests):
        mock_requests.get(Trakt.API_URL, text="{\"movie_id\": 123abc\"}")  # NOTE: missing quote
        res = self.trakt._to_json(self.trakt._get(""))
        self.assertEqual(res, [])


class GetAllTestCase(unittest.TestCase):
    def setUp(self):
        self.trakt = Trakt("thekey")

    @requests_mock.mock()
    def test_none(self, mock_requests):
        mock_requests.get("/FAKEURL", text="[]",
                          headers={"x-pagination-page": "1", "x-pagination-page-count": "1"})
        items = list(self.trakt._get_all("/FAKEURL"))

        self.assertFalse(len(items) > 0, msg="Should not have gotten any activities")

    @requests_mock.mock()
    def test_all(self, mock_requests):
        mock_requests.get("/FAKEURL", text="[1,2,3,4,5,6]",
                          headers={"x-pagination-page": "1", "x-pagination-page-count": "1"})

        items = list(self.trakt._get_all("/FAKEURL"))
        self.assertEqual(len(items), 6, msg="Should have gotten all (6) activities")

    @requests_mock.mock()
    def test_filter(self, mock_requests):
        mock_requests.get("/FAKEURL", text="[1,2,3,4,5,6]",
                          headers={"x-pagination-page": "1", "x-pagination-page-count": "1"})

        items_none = list(self.trakt._get_all("/FAKEURL", lambda a: a < 0))
        items_some = list(self.trakt._get_all("/FAKEURL", lambda a: a < 4))

        self.assertEqual(len(items_none), 0, msg="Should filter out all items")
        self.assertEqual(len(items_some), 3, msg="Should filter out 3 items")

    @requests_mock.mock()
    def test_pages_all(self, mock_requests):
        mock_requests.get("/FAKEURL?page=1", text="[1,2,3,4,5]",
                          headers={"x-pagination-page": "1", "x-pagination-page-count": "2"})
        mock_requests.get("/FAKEURL?page=2", text="[6,7,8,9,10]",
                          headers={"x-pagination-page": "2", "x-pagination-page-count": "2"})

        items_all = list(self.trakt._get_all("/FAKEURL"))
        self.assertEqual(items_all, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], msg="Got wrong items back.")

    @requests_mock.mock()
    def test_pages_filter(self, mock_requests):
        mock_requests.get("/FAKEURL?page=1", text="[1,2,3,4,5]",
                          headers={"x-pagination-page": "1", "x-pagination-page-count": "2"})
        mock_requests.get("/FAKEURL?page=2", text="[6,7,8,9,10]",
                          headers={"x-pagination-page": "2", "x-pagination-page-count": "2"})

        items_all = list(self.trakt._get_all("/FAKEURL", lambda a: a < 9))
        self.assertEqual(items_all, [1, 2, 3, 4, 5, 6, 7, 8], msg="Got wrong items back.")
