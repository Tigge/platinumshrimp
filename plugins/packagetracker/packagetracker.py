# coding=utf-8

from __future__ import division, absolute_import, print_function, unicode_literals
import json
import datetime
import threading
import sys

from twisted.python import log
import plugin
import plugins.packagetracker.provider_postnord

__author__ = 'tigge'


class PackageTracker(plugin.Plugin):
    def __init__(self):
        log.msg("PackageTracker.__init__")
        plugin.Plugin.__init__(self, "PackageTracker")

        self.settings = {}
        self.packages = []

        self.ticks = 0

    def started(self, settings):
        log.msg("PackageTracker.started", settings)
        self.settings = json.loads(settings)

        plugins.packagetracker.provider_postnord.PostnordPackage.set_apikey(self.settings["postnord"]["apikey"])

    def update(self):
        #log.msg("PackageTracker.update")
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:

            for package in self.packages:
                # self.say(package.server, package.channel, package.user + ": Package update... " + package.id)
                thread = threading.Thread(target=self.update_package, args=(package,))
                thread.start()

    def privmsg(self, server, user, channel, message):

        if message.startswith("!"):
            if message.startswith("!addpackage "):
                package_id = message[12:].strip()
                self.add_package_id(package_id, server, user, channel)

            elif message.startswith("!removepackage "):
                package_id = message[15:].strip()
                for package in list(self.packages):
                    if package.id == package_id:
                        self.say(server, channel, "Package removed...")
                        break
                else:
                    self.say(server, channel, "Package not found...")
            elif message.startswith("!listpackages"):
                self.say(server, channel, "Listing {0} packages...".format(len(self.packages)))
                for package in self.packages:
                    self.say(server, channel, str(package.id))

    def add_package_id(self, package_id, server, user, channel):
        package = None
        if plugins.packagetracker.provider_postnord.PostnordPackage.is_package(package_id):
            package = plugins.packagetracker.provider_postnord.PostnordPackage(package_id)

        if package is not None:
            package.server = server
            package.channel = channel
            package.user = user.split('!', 1)[0]
            self.add_package(package)
            self.say(server, channel, "Package added...")
        else:
            self.say(server, channel, "Package not found in any provider...")

    def add_package(self, package):
        package.on_event = lambda event: self.on_event(package, event)
        self.packages.append(package)

    def update_package(self, package):
        package.update()

    def on_event(self, package, event):
        self.say(package.server, package.channel,
                 "{0}: {1} - {2:%Y-%m-%d %H:%M}: {3}".format(package.user, package.id, event.datetime,
                                                             event.description))


class Package:
    class Event:
        def __init__(self):
            self.datetime = datetime.datetime(1970, 1, 1)
            self.description = ""

    def __init__(self, package_id):
        self.id = package_id
        self.last = None
        self.consignor = None
        self.consignee = None
        self.last_updated = datetime.datetime(1970, 1, 1)

    def on_event(self, event):
        pass

    def update(self):
        pass


if __name__ == "__main__":
    sys.exit(PackageTracker.run())
