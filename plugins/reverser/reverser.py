import sys
import plugin
import logging


class Reverser(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "reverser")
        logging.info("Reverser.__init__")

    @staticmethod
    def _reverse_string(text):
        return text[::-1]

    def on_pubmsg(self, server, source, target, message):
        if message.startswith("!reverse"):
            self.privmsg(server, target, Reverser._reverse_string(message[8:]))


if __name__ == "__main__":
    sys.exit(Reverser.run())
