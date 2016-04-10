import dateutil.parser
import logging
import requests


class Trakt(object):

    API_URL = "https://api-v2launch.trakt.tv"

    API_USERS_HISTORY = "/users/{0}/history/{1}"

    API_SEASONS_SUMMARY = "/shows/{0}/seasons"

    def __init__(self, key):
        self.key = key

    @staticmethod
    def get_date(date):
        return dateutil.parser.parse(date)

    def _get(self, url, params={}):
        logging.info("Trakt.get %s", url)
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": 2,
            "trakt-api-key": self.key
        }
        response = requests.get(Trakt.API_URL + url, headers=headers, verify=False, params=params)

        if response.status_code not in [200, 201, 204]:
            if response.status_code == 400:
                raise Exception("Request couldn't be parsed")
            elif response.status_code == 401:
                raise Exception("OAuth must be provided")
            elif response.status_code == 403:
                raise Exception("Invalid API key or unapproved app")
            elif response.status_code == 404:
                raise Exception("Method exists, but no record found")
            elif response.status_code == 405:
                raise Exception("Method doesn't exist")
            elif response.status_code == 409:
                raise Exception("Resource already created")
            else:
                raise Exception(str(response.status_code) + ": " + response.reason)

        return response

    def _to_json(self, response):
        try:
            return response.json()
        except ValueError as e:
            logging.exception("")
            return []
        except requests.exceptions.ConnectionError as e:
            logging.exception("")
            return []

    def _get_all(self, url, accept_function=None, extended="min"):
        params = {"page": 1, "extended": extended}
        while True:
            response = self._get(url, params)
            items = self._to_json(response)

            for item in items:
                if accept_function is not None and not accept_function(item):
                    return
                yield item

            if "X-Pagination-Page" not in response.headers or "X-Pagination-Page-Count" not in response.headers:
                return
            if response.headers["X-Pagination-Page"] >= response.headers["X-Pagination-Page-Count"]:
                return
            params["page"] = int(response.headers["X-Pagination-Page"]) + 1

    def users_history(self, user, typ, accept_function=None, extended="min"):
        return self._get_all(Trakt.API_USERS_HISTORY.format(user, typ), accept_function, extended)

    def seasons_summary(self, show, extended="min"):
        return self._get_all(Trakt.API_SEASONS_SUMMARY.format(show), extended=extended)
