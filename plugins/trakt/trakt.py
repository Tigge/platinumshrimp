from plugins.trakt import api
import json
import sys
import logging
import datetime

import dateutil.parser
import dateutil.tz

import plugin


class Trakt(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "trakt")
        logging.info("Trakt.__init__")

        self.trakt = None
        self.settings = {}
        self.users = {}
        self.ticks = 0

    def started(self, settings):
        logging.info("Trakt.started %s", settings)
        self.settings = json.loads(settings)
        self.trakt = api.Trakt(self.settings["key"])

        for user in self.settings["users"]:
            self.users[user] = {
                "last_sync_movies": datetime.datetime.now(tz=dateutil.tz.tzutc()),
                "last_sync_episodes": datetime.datetime.now(tz=dateutil.tz.tzutc()),

            }

    def on_welcome(self, server, source, target, message):
        logging.info("Trakt.onconnected %s", server)
        self.join(str(self.settings["server"]), str(self.settings["channel"]))

    def on_join(self, server, source, channel):
        logging.info("Trakt.joined %s %s", server, channel)

    def echo(self, message):
        logging.info("Trakt.echo %s", message)
        self.privmsg(self.settings["server"], self.settings["channel"], "Trakt: " + message)

    def update(self):
        #logging.info("Trakt.update")
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:
            for user in self.users:
                self._thread(self.update_user, user)

    def update_user(self, username):
        user = self.users[username]

        for typ in ["episodes", "movies"]:

            def is_new_item(item):
                return api.Trakt.get_date(item["watched_at"]) > user["last_sync_" + typ]

            activities = self.fetch_new_activities(user, typ, is_new_item)

            # Continue if we have no entries
            if len(activities) == 0:
                continue

            for activity in activities:
                self.users[username]["last_sync_" + typ] = max(self.users[username]["last_sync_" + typ],
                                                               api.Trakt.get_date(activity["watched_at"]))

            activity_summary = self.create_activity_summary(activities)

            #print("got activites2 %s" % activity_summary)

            for entry in activity_summary:
                print("loop", entry)
                for series in entry["series"]:
                    print("get message", series)
                    message = Trakt.format_activity(series, username, entry["action"])
                    print("message %s" % message)
                    if message is not None:
                        print("echo function %s" % self.echo)
                        self.echo(message)

            #except Exception as e:
            #    print("EXCEPTION", repr(e), sys.exc_info()[2].tb_lineno)
            #    logging.exception("Unhandled exception when fetching for %s of type %s", user, typ)

    def fetch_new_activities(self, user, typ, is_new_item):
        return list(self.trakt.users_history(user, typ, is_new_item))

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
            return "/shows/{0}".format(item["show"]["ids"]["trakt"])

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
