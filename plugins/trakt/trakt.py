import api
import json
import logging
import sys
import datetime

import dateutil.parser
import dateutil.tz

from platinumshrimp import plugin


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

            def is_new_item(item, typ=typ):
                return api.Trakt.get_date(item["watched_at"]) > user["last_sync_" + typ]

            try:
                activities = self.fetch_new_activities(username, typ, is_new_item)

                # Continue if we have no entries
                if len(activities) == 0:
                    continue

                # Update last sync
                for activity in activities:
                    user["last_sync_" + typ] = max(user["last_sync_" + typ],
                                                   api.Trakt.get_date(activity["watched_at"]))

                if typ == "episodes":
                    activity_summary = self.create_activity_summary(activities)
                    for activity in activity_summary:
                        message = Trakt.format_activity(activity, username, activity["action"])
                        if message is not None:
                            self.echo(message)
                else:
                    for activity in activities:
                        self.echo(Trakt.format_activity(activity, username, activity["action"]))

            except Exception as e:
                logging.exception("Unhandled exception when fetching for %s of type %s", user, typ)

    def fetch_new_activities(self, user, typ, is_new_item):
        return list(self.trakt.users_history(user, typ, is_new_item))

    def create_activity_summary(self, activities):
        """
        Returns an activity summary
        {
          "action": "scrobble",
          "show": {...}
          "seasons": {
            2: {
              "number": 2,
              "ids": {...}
                "trakt": 1,
                [...]
              },
              "episodes": {
                5: {
                  "season": 2,
                  "number": 5,
                  "title": "Episode Title",
                  "ids": {
                    "trakt": 2,
                    [...]
                  }
                }
              }
            }
          }
        }

        :param activities:
        :return:
        """
        result = {}
        for activity in activities:
            key = "%s_%s" % (activity["action"], activity["show"]["title"])
            if key not in result:
                result[key] = {
                    "show": activity["show"],
                    "action": activity["action"],
                    "seasons": {}
                }
                for season in self.trakt.seasons_summary(activity["show"]["ids"]["trakt"], extended="full"):
                    result[key]["seasons"][season["number"]] = season
                    result[key]["seasons"][season["number"]]["episodes"] = {}

            season_number = activity["episode"]["season"]
            episode_number = activity["episode"]["number"]
            result[key]["seasons"][season_number]["episodes"][episode_number] = activity["episode"]

        return [value for (key, value) in result.items()]

    @staticmethod
    def format_activity(activity={}, username="", action=""):
        return "{0} {1} {2} http://www.trakt.tv{3}".format(username, Trakt.format_action(action),
                                                           Trakt.format_item(activity), Trakt.format_url(activity))

    @staticmethod
    def format_item(item):
        if "movie" in item:
            return Trakt.format_movie(item["movie"])
        elif "seasons" in item:
            return Trakt.format_summary(item)
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
    def format_summary(summary):

        def find_episode_ranges(season):
            ranges = []
            range_test = []
            for episode in range(1, season["episode_count"] + 1):
                if episode not in season["episodes"]:
                    if len(range_test) > 0:
                        ranges.append(range_test[:])
                        range_test = []
                else:
                    range_test.append(episode)
            if len(range_test) > 0:
                ranges.append(range_test[:])
            return ranges

        episode_count = (0, None)
        for season in summary["seasons"].values():
            if len(season["episodes"]) == 0:
                continue
            episode_count = (episode_count[0] + len(season["episodes"]), next(iter(season["episodes"].values())))
            episode_ranges = find_episode_ranges(season)

            strings = []
            for episode_range in episode_ranges:
                if len(episode_range) > 1:
                    strings.append("S{:02d}E{:02d}-E{:02d}".format(season["number"], episode_range[0], episode_range[-1]))
                else:
                    strings.append("S{:02d}E{:02d}".format(season["number"], episode_range[0]))

        if episode_count[0] == 1:
            return Trakt.format_episode(summary["show"], episode_count[1])
        return Trakt.format_show(summary["show"]) + " " + ", ".join(strings)


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
