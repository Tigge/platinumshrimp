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
        if server in self.settings:
            for channel in self.settings[server]:
                self.join(server, channel)

    def on_invite(self, server, source, target, channel):
        logging.info("Invited to '%s' on '%s' by '%s", channel, server, source)
        channels = self.settings.get(server, [])
        channels.append(channel)
        self.settings[server] = channels
        self._save_settings(json.dumps(self.settings))
        self.join(server, channel)

if __name__ == "__main__":
    sys.exit(Autojoiner.run())
