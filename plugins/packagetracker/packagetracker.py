# coding=utf-8

import datetime
import json
import logging
import sys

from platinumshrimp import plugin
import provider_postnord

__author__ = 'tigge'


class PackageTracker(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "packagetracker")
        logging.info("PackageTracker.__init__")

        self.settings = {}
        self.providers = []
        self.packages = []
        self.packages_pending = set()

        self.ticks = 0

    def started(self, settings):
        logging.info("PackageTracker.started %s", settings)
        self.settings = json.loads(settings)

        provider_postnord.PostnordPackage.set_apikey(self.settings["postnord"]["apikey"])
        self.providers.append(provider_postnord.PostnordPackage)

    def update(self):
        self.ticks += 1
        if self.ticks % self.settings["interval"] == 0:
            logging.info("PackageTracker.update")
            for package in self.packages:
                self._thread(self.update_package, package)

    def on_pubmsg(self, server, user, channel, message):

        if message.startswith("!addpackage "):
            package_id = message[12:].strip()
            self.add_package_id(package_id, server, user, channel)

        elif message.startswith("!removepackage "):
            package_id = message[15:].strip()
            for package in list(self.packages):
                if package.id == package_id:
                    self.remove_package(package)
                    self.privmsg(server, channel, "Package removed...")
                    break
            else:
                self.privmsg(server, channel, "Package not found...")
        elif message.startswith("!listpackages"):
            self.privmsg(server, channel, "Listing {0} packages...".format(len(self.packages)))
            for package in self.packages:
                self.privmsg(server, channel, str(package.id))

    def add_package_id(self, package_id, server, user, channel):
        package = None
        for provider in self.providers:
            if provider.is_package(package_id):
                package = provider(package_id)
                break
        else:
            self.packages_pending.add({package_id, server, user, channel})
            self.privmsg(server, channel, "Package pending.")
            return

        package.server = server
        package.channel = channel
        package.user = user.split('!', 1)[0]
        self.add_package(package)
        self.privmsg(server, channel, "Package added...")

    def add_package(self, package):
        logging.info("PackageTracker.add_package '%s'", package.id)
        package.on_event = lambda event: self.on_event(package, event)
        self.packages.append(package)

    def update_package(self, package):
        logging.info("PackageTracker.update_package '%s'", package.id)
        package.update()

    def remove_package(self, package):
        logging.info("PackageTracker.remove_package '%s'", package.id)
        self.packages.remove(package)

    def on_event(self, package, event):
        self.privmsg(package.server, package.channel,
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
