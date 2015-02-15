from __future__ import division, absolute_import, print_function, unicode_literals

import json
import sys

import plugin

from twisted.python import log


class Autojoin(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "Autojoin")
        self.settings = {}

    def started(self, settings):
        self.settings = json.loads(settings)

    def onconnected(self, server):
        if server in self.settings:
            for channel in self.settings[server]:
                self.join(server, str(channel))

if __name__ == "__main__":
    sys.exit(Autojoin.run())
