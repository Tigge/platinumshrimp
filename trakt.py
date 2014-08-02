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

        self.join(str(self.settings["channel"]))

    def joined(self, channel):
        log.msg("Trakt.joined", channel)

    def privmsg(self, user, channel, message):
        pass

    def echo(self, message):
        log.msg("Trakt.echo", message)
        self.say(str(self.settings["channel"]), "Trakt: " + message.encode("utf-8"))

    def update(self):
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:
            print "Trakt.update", self.ticks
            for user in self.users:
                url = URL_ACTIVITY.format(self.settings["key"], user, self.users[user]["last_sync"])
                response = urllib2.urlopen(url)
                data = json.load(response)
                print "Trakt.update", user, data
                self.users[user]["last_sync"] = data["timestamps"]["current"]
                for activity in data["activity"]:
                    self.echo_activity(activity, user)

    def echo_activity(self, activity, user):
        if activity["type"] == "list":
            if activity["action"] == "created":
                self.echo("{0} create a list '{1}'".format(user, activity["list"]["name"]))
            elif activity["action"] == "item_added":
                self.echo("{0} added {1} to the list '{2}'".format(user, self.format_item(activity["list_item"]), activity["list"]["name"]))
        else:
            message = user + " " + activity["action"] + " "

            if activity["action"] == "watching":
                message += " is watching (" + activity["elapsed"]["short"] + ") "
            elif activity["action"] == "scrobble":
                message += " scrobbled "
            elif activity["action"] == "checkin":
                message += " checked in "
            elif activity["action"] == "rating":
                message += " rated (as " + self.format_rating(activity) + ") "
            elif activity["action"] == "watchlist":
                message += " added to watchlist, "
            else:
                # TODO: seen, collection, shout, review
                return

            message += self.format_item(activity)

            self.echo(message)

    def format_item(self, item):
        if item["type"] == "movie":
            return self.format_movie(item["movie"])
        elif item["type"] == "episode":
            return self.format_episode(item["show"], item["episode"])
        elif item["type"] == "show":
            return self.format_show(item["show"])

    def format_movie(self, movie):
        return "'{0[title]} ({0[year]})' {0[url]}".format(movie)

    def format_show(self, show):
        return "'{0[title]}' {0[url]}".format(show)

    def format_episode(self, show, episode):
        return "'{0[title]}' 'S{1[season]:02d}E{1[episode]:02d} {1[title]}' {1[url]}".format(show, episode)

    def format_rating(self, activity):
        if activity["use_rating_advanced"]:
            return activity["rating_advanced"]
        else:
            return activity["rating"]

if __name__ == "__main__":
    sys.exit(Trakt.run())

