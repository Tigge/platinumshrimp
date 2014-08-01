import urllib2
import json

import plugin

APIKEY = "XXX_KEY"
URL_ACTIVITY = "http://api.trakt.tv/activity/user.json/{0}/{1}/all/all/{2}"
URL_TIME = "http://api.trakt.tv/server/time.json/{0}"

class Trakt(plugin.Plugin):

    INTERVAL = 60 * 5
    CHANNEL = "#platinumshrimp"

    def __init__(self):

        self.ticks = 0
        self.users = {"XXX": {"last_sync": 0},}

        self.update_time(self.users)

    def update_time(self, users):
        url = URL_TIME.format(APIKEY)
        response = urllib2.urlopen(url)
        data = json.load(response)
        for user in users:
            self.users[user]["last_sync"] = data["timestamp"]

    def started(self):
        print "Trakt.started"
        self.join(Trakt.CHANNEL)

    def joined(self, channel):
        if channel == Trakt.CHANNEL:
            self.say(channel, "Woooooot")

    def update(self):
        print "Trakt.update", self.ticks
        self.ticks += 1
        if self.ticks % Trakt.INTERVAL == 0:
            for user in self.users:
                url = URL_ACTIVITY.format(APIKEY, user, self.users[user]["last_sync"])
                response = urllib2.urlopen(url)
                data = json.load(response)
                self.users[user]["last_sync"] = data["timestamps"]["current"]
                for activity in data["activity"]:
                    self.print_activity(activity, user)

    def print_activity(self, activity, user):
        if activity["type"] == "movie":
            self.say(Trakt.CHANNEL, "Trakt: {0} watched '{1} ({2})' - {3}".format(user, activity["movie"]["title"], activity["movie"]["year"], activity["movie"]["url"]))
        else:
            self.say(Trakt.CHANNEL, "Trakt: {0} did something {1} related".format(user, activity["type"]))

Trakt.run()
