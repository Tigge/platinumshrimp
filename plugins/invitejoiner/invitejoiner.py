import logging
import sys

from platinumshrimp import plugin


class Invitejoiner(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "invitejoiner")

    def on_invite(self, server, source, target, channel):
        logging.info("Invited to '%s' on '%s' by '%s", channel, server, source)
        self.join(server, channel)

if __name__ == "__main__":
    sys.exit(Invitejoiner.run())
