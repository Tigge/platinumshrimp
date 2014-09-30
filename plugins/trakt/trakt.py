import json
import sys
import urllib2

from twisted.python import log

import plugin

URL_ACTIVITY = "http://api.trakt.tv/activity/user.json/{0}/{1}/all/all/{2}"
URL_TIME = "http://api.trakt.tv/server/time.json/{0}"

class Trakt(plugin.Plugin):

    def __init__(self):
        log.msg("Trakt.__init__")
        plugin.Plugin.__init__(self, "Trakt")
        
        self.settings = {}
        self.users = []
        self.ticks = 0

    def update_time(self, users):
        log.msg("Trakt.update_time", users)
        url = URL_TIME.format(self.settings["key"])
        response = urllib2.urlopen(url)
        data = json.load(response)
        for user in users:
            self.users[user]["last_sync"] = data["timestamp"]

    def started(self, settings):
        log.msg("Trakt.started", settings)
        self.settings = json.loads(settings)

        self.users = dict(map(lambda user: (user, {"last_sync": 0}), self.settings["users"]))
        self.update_time(self.users)

        self.join(0, str(self.settings["channel"]))

    def joined(self, server_id, channel):
        log.msg("Trakt.joined", server_id, channel)

    def echo(self, message):
        log.msg("Trakt.echo", message)
        self.say(0, str(self.settings["channel"]), "Trakt: " + message.encode("utf-8"))

    def update(self):
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:
            for user in self.users:
                try:
                    url = URL_ACTIVITY.format(self.settings["key"], user, self.users[user]["last_sync"])
                    response = urllib2.urlopen(url)
                    data = json.load(response)
                    self.users[user]["last_sync"] = data["timestamps"]["current"]
                    for activity in data["activity"]:
                        message = Trakt.format_activity(activity, user)
                        if message is not None:
                            self.echo(message)
                except urllib2.HTTPError as e:
                    log.info("HTTP error when fetching", url, e.code)
                except (urllib2.URLError, ) as e:
                    log.info("URL error when fetching", url, e.args)
                except Exception as e:
                    log.error("Unhandled exception when fetching", url)
                    log.error("Data:", data, "User:", user)
                    log.err()

    @staticmethod
    def format_activity(activity, user):
        if activity["type"] == "list":
            if activity["action"] == "created":
                return "{0} create a list '{1}'".format(user, activity["list"]["name"])
            elif activity["action"] == "item_added":
                return "{0} added {1} to the list '{2}'".format(user, Trakt.format_item(activity["list_item"]), activity["list"]["name"])
        else:
            message = user

            #if activity["action"] == "watching":
            #    message += " is watching (" + activity["elapsed"]["short"] + ") "
            if activity["action"] == "scrobble":
                message += " scrobbled "
            elif activity["action"] == "checkin":
                message += " checked in "
            elif activity["action"] == "rating":
                message += " rated (as " + Trakt.format_rating(activity) + ") "
            elif activity["action"] == "watchlist":
                message += " added to watchlist, "
            else:
                # TODO: seen, collection, shout, review
                return

            return message + Trakt.format_item(activity)

    @staticmethod
    def format_item(item):
        if item["type"] == "movie":
            return Trakt.format_movie(item["movie"])
        elif item["type"] == "episode":
            return Trakt.format_episode(item["show"], item["episode"])
        elif item["type"] == "show":
            return Trakt.format_show(item["show"])

    @staticmethod
    def format_movie(movie):
        return "'{0[title]} ({0[year]})' {0[url]}".format(movie)

    @staticmethod
    def format_show(show):
        return "'{0[title]}' {0[url]}".format(show)

    @staticmethod
    def format_episode(show, episode):
        return "'{0[title]}' 'S{1[season]:02d}E{1[episode]:02d} {1[title]}' {1[url]}".format(show, episode)

    @staticmethod
    def format_rating(activity):
        if activity["use_rating_advanced"]:
            return str(activity["rating_advanced"])
        else:
            return activity["rating"]

if __name__ == "__main__":
    sys.exit(Trakt.run())

