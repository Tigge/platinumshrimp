import json
import sys
import datetime
import threading
import logging

import requests
import dateutil.parser

import plugin


API_URL = "https://api-v2launch.trakt.tv"
API_ACTIVITY = "/users/{0}/history/{1}"


class Trakt(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "trakt")
        logging.info("Trakt.__init__")

        self.settings = {}
        self.users = {}
        self.ticks = 0

    def get(self, url, params=None):
        logging.info("Trakt.get %s", url)
        headers = {"Content-Type": "application/json",
                   "trakt-api-version": 2,
                   "trakt-api-key": self.settings["key"]}
        r = requests.get(API_URL + url, headers=headers, verify=False, params=params)

        if r.status_code in [200, 201, 204]:
            try:
                return r.json()
            except ValueError as e:
                logging.exception("")
                return []
            except requests.exceptions.ConnectionError as e:
                logging.exception("")
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

    def fetch_new_activities(self, url, last_sync):
        if last_sync == None:
            latest_activity = self.get(url, {"limit":1})
            return ([], Trakt.get_date(latest_activity[0]["watched_at"]) if len(latest_activity) > 0 else None)
        else:
            result = []
            """ This could be a while loop but the limited range adds a safety
            to the operation and we need an index anyways so... """
            for index in range(1, 11):
                activities = self.get(url, {"page":index})
                if len(activities) == 0:
                    break
                else:
                    has_more = True
                    for activity in activities:
                        if Trakt.get_date(activity["watched_at"]) > last_sync:
                            result.append(activity)
                        else:
                            has_more = False
                            break
                    if not has_more:
                        break

            return (result, Trakt.get_date(result[0]["watched_at"]) if len(result) > 0 else last_sync)

    def started(self, settings):
        logging.info("Trakt.started %s", settings)
        self.settings = json.loads(settings)

        self.users = dict(map(lambda user: (user, {}), self.settings["users"]))

    def on_welcome(self, server, source, target, message):
        logging.info("Trakt.onconnected %s", server)
        self.join(str(self.settings["server"]), str(self.settings["channel"]))

    def on_join(self, server, source, channel):
        logging.info("Trakt.joined %s %s", server, channel)

    def echo(self, message):
        logging.info("Trakt.echo %s", message)
        self.privmsg(self.settings["server"], self.settings["channel"], "Trakt: " + message)

    @staticmethod
    def get_date(date):
        return dateutil.parser.parse(date)

    def update(self):
        #logging.info("Trakt.update")
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:
            for user in self.users:
                self._thread(self.update_user, user)

    def update_user(self, userName):
        user = self.users[userName]
        print("update_user")
        for typ in ["episodes", "movies"]:

            try:
                activities, new_last_sync = self.fetch_new_activities(API_ACTIVITY.format(userName, typ), user["last_sync_" + typ] if "last_sync_" + typ in user else None)

                # Save latest watched datetime
                if new_last_sync != None:
                    user["last_sync_" + typ] = new_last_sync

                # Continue if we have no entries
                if len(activities) == 0:
                    continue

                activity_summary = self.create_activity_summary(activities)

                print("got activites2 %s" % activity_summary)

                for entry in activity_summary:
                    print("loop")
                    for series in entry["series"]:
                        print("get message")
                        message = Trakt.format_activity(series, userName, entry["action"])
                        print("message %s" % message)
                        if message is not None:
                            print("echo function %s" % self.echo)
                            self.echo(message)

            except Exception as e:
                logging.exception("Unhandled exception when fetching (for %s) on %s", user, API_ACTIVITY.format(user, typ))

    def create_activity_summary(self, activities):
        result = {}
        for activity in activities:
            print("aqqs %s" % activity)
            key = "%s_%s" % (activity["action"], activity["show"]["title"])
            if key not in result:
                result[key] = {
                    "show": activity["show"]["title"],
                    "action": activity["action"],
                    "episodes": (),
                }

        return [ value for (key, value) in result.items() ]

    @staticmethod
    def format_activity(activity={}, userName="", action=""):
        return "{0} {1} {2} http://www.trakt.tv{3}".format(userName, Trakt.format_action(action),
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
    def format_action(action):
        if action == "scrobble":
            return "scrobbled"
        elif action == "checkin":
            return "checked in"
        elif action == "watch":
            return "watched"

if __name__ == "__main__":
    sys.exit(Trakt.run())
