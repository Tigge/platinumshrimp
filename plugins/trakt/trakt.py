from __future__ import division, absolute_import, print_function, unicode_literals

import json
import sys
import datetime
import threading

import requests
import dateutil.parser
from twisted.python import log

import plugin


API_URL = "https://api.trakt.tv"
API_ACTIVITY = "/users/{0}/history/{1}"


class Trakt(plugin.Plugin):
    def __init__(self):
        log.msg("Trakt.__init__")
        plugin.Plugin.__init__(self, "Trakt")

        self.settings = {}
        self.users = []
        self.ticks = 0

    def get(self, url):
        log.msg("Trakt.get", url)
        headers = {"Content-Type": "application/json",
                   "trakt-api-version": 2,
                   "trakt-api-key": self.settings["key"]}
        r = requests.get(API_URL + url, headers=headers, verify=False)

        if r.status_code in [200, 201, 204]:
            try:
                return r.json()
            except ValueError as e:
                log.err()
                return []
            except requests.exceptions.ConnectionError as e:
                log.err()
                return []
        elif r.status_code == 400:
            raise Exception("Request couldn't be parsed")
        elif r.status_code == 401:
            raise Exception("OAuth must be provided")
        elif r.status_code == 403:
            raise Exception("Invalid API key")
        elif r.status_code == 404:
            raise Exception("Method exists, but no record found")
        elif r.status_code == 405:
            raise Exception("Method doesn't exist")
        elif r.status_code == 409:
            raise Exception("Resource already created")
        else:
            raise Exception(str(r.status_code) + ": " + r.reason)

    def started(self, settings):
        log.msg("Trakt.started", settings)
        self.settings = json.loads(settings)

        self.users = dict(map(lambda user: (user, {}), self.settings["users"]))

        self.join(0, str(self.settings["channel"]))

    def joined(self, server_id, channel):
        log.msg("Trakt.joined", server_id, channel)

    def echo(self, message):
        log.msg("Trakt.echo", message)
        self.say(0, str(self.settings["channel"]), "Trakt: " + message.encode("utf-8"))

    @staticmethod
    def get_date(date):
        return dateutil.parser.parse(date)

    def update(self):
        #log.msg("Trakt.update")
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:
            for user in self.users:
                thread = threading.Thread(target=self.update_user, args=(user,))
                thread.start()

    def update_user(self, user):
        for typ in ["episodes", "movies"]:

            try:
                res = self.get(API_ACTIVITY.format(user, typ))

                # Continue if we have no entries
                if len(res) == 0:
                    continue

                # Save latest watched datetime if we haven't fetched this feed before
                if "last_sync_" + typ not in self.users[user]:
                    self.users[user]["last_sync_" + typ] = Trakt.get_date(res[0]["watched_at"])
                    continue

                for activity in res:
                    if Trakt.get_date(activity["watched_at"]) > self.users[user]["last_sync_" + typ]:

                        message = Trakt.format_activity(activity, user)
                        if message is not None:
                            self.echo(message)

                self.users[user]["last_sync_" + typ] = Trakt.get_date(res[0]["watched_at"])

            except Exception as e:
                log.msg("Unhandled exception when fetching", API_ACTIVITY.format(user, typ))
                log.msg("User:", user)
                log.err()

    @staticmethod
    def format_activity(activity, user):
        return "{0} {1} {2} http://www.trakt.tv{3}".format(user, Trakt.format_action(activity["action"]),
                                                           Trakt.format_item(activity), Trakt.format_url(activity))

    @staticmethod
    def format_item(item):
        if "movie" in item:
            return Trakt.format_movie(item["movie"])
        elif "episode" in item:
            return Trakt.format_episode(item["show"], item["episode"])
        elif "show" in item:
            return Trakt.format_show(item["show"])

    @staticmethod
    def format_url(item):
        if "movie" in item:
            return "/movies/{0}".format(item["movie"]["ids"]["trakt"])
        elif "episode" in item:
            return "/episodes/{0}".format(item["episode"]["ids"]["trakt"])
        elif "show" in item:
            return "/shows/{0}".format(item["episode"]["ids"]["trakt"])

    @staticmethod
    def format_movie(movie):
        return "'{0[title]}' ({0[year]})".format(movie)

    @staticmethod
    def format_show(show):
        return "'{0[title]}'".format(show)

    @staticmethod
    def format_episode(show, episode):
        return "'{0[title]}', S{1[season]:02d}E{1[number]:02d} '{1[title]}'".format(show, episode)

    @staticmethod
    def format_rating(activity):
        if activity["use_rating_advanced"]:
            return unicode(activity["rating_advanced"])
        else:
            return activity["rating"]

    @staticmethod
    def format_action(action):
        if action == "scrobble":
            return "scrobbled"
        elif action == "checkin":
            return "checked in"
        elif action == "watch":
            return "watched"

if __name__ == "__main__":
    sys.exit(Trakt.run())
