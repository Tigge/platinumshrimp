from __future__ import division, absolute_import, print_function, unicode_literals

import json
import sys

import plugin

class Autojoiner(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "autojoiner")
        self.settings = {}

    def started(self, settings):
        self.settings = json.loads(settings)

    def on_welcome(self, server, source, target, message):
        if server in self.settings:
            for channel in self.settings[server]:
                self.join(server, channel)

if __name__ == "__main__":
    sys.exit(Autojoiner.run())
