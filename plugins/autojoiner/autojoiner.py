import json
import sys
import logging

import plugin


class Autojoiner(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "autojoiner")
        self.settings = {}

    def started(self, settings):
        self.settings = json.loads(settings)

    def on_welcome(self, server, source, target, message):
        logging.info(
            "Welcome to '%s' - '%s', '%s', '%s'", server, source, target, message
        )
        self.username = target
        if server in self.settings:
            for channel in self.settings[server]:
                self.join(server, channel)

    def on_invite(self, server, source, target, channel):
        if target != self.username:
            return

        logging.info(
            "Invited '%s' to '%s' on '%s' by '%s", target, channel, server, source
        )
        channels = self.settings.get(server, [])
        channels.append(channel)
        self.settings[server] = channels
        self._save_settings(json.dumps(self.settings))
        self.join(server, channel)

    def on_kick(self, server, source, channel, target, reason):
        if target != self.username:
            return

        logging.info(
            "Kicked '%s' from '%s' on '%s' by '%s' because '%s'",
            target,
            channel,
            server,
            source,
            reason,
        )
        channels = self.settings.get(server, [])
        channels.remove(channel)
        self._save_settings(json.dumps(self.settings))


if __name__ == "__main__":
    sys.exit(Autojoiner.run())
