from __future__ import division, absolute_import, print_function, unicode_literals

import sys

import plugin

from twisted.python import log


class Invitejoiner(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "Invitejoiner")

    def invited(self, server, channel):
        log.msg("Invited to: ", channel)
        self.join(server, channel)

if __name__ == "__main__":
    sys.exit(Invitejoiner.run())

