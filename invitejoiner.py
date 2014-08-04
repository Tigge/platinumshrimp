
import plugin

from twisted.python import log

class Invitejoiner(plugin.Plugin):

    def __init__(self):
        plugin.Plugin.__init__(self, "Invitejoiner")

    def invited(self, server_id, channel):
        log.msg("Invited to: ", channel)
        self.join(server_id, channel)

Invitejoiner.run()

