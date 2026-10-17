import json
import logging
import sys
from datetime import datetime

import plugin
from utils.schedule_parser import parse_schedule

HELP_MESSAGE = "Usage: !predict #channel [YYYY-MM-DD] [HH:MM] | [duration] message"


class Predicter(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "predicter")
        self.update_count = 0
        self.settings = {}

    def started(self, settings):
        self.settings = json.loads(settings)
        if "scheduled_messages" not in self.settings:
            self.settings["scheduled_messages"] = []
            self._save_settings(json.dumps(self.settings))

    parse_schedule = staticmethod(parse_schedule)

    def process_predict(self, server, user_name, channel, full_message):
        logging.info(f"Predicter.process_predict {user_name}: {full_message}")
        target_channel, message = "", ""
        try:
            target_channel, message = full_message.split(" ", 1)
        except:
            logging.info("Failed initial parsing")
            self.safe_privmsg(server, user_name, HELP_MESSAGE)
            return

        now = datetime.now()
        target_dt, msg, is_specified = self.parse_schedule(message, now)

        if not is_specified:
            # Neither time nor date, send message at the next minute and send a warning to the user
            self.safe_privmsg(server, user_name, "No time or date specified, scheduling now!")
        elif target_dt <= now:
            # If the time has already lapsed, give a warning to the user (but still schedule the msg):
            self.safe_privmsg(server, user_name, "Time and date is before now, scheduling now!")

        if "scheduled_messages" not in self.settings:
            self.settings["scheduled_messages"] = []

        self.settings["scheduled_messages"].append(
            {
                "server": server,
                "channel": target_channel,
                "message": "From " + user_name + " on " + str(now)[:16] + ": " + msg,
                "timestamp": target_dt.isoformat(),
            }
        )

        self._save_settings(json.dumps(self.settings))
        logging.info(f"Message scheduled for {target_dt} to {target_channel}")
        self.privmsg(server, user_name, f"Message scheduled for {target_dt} to {target_channel}")

    def on_privmsg(self, server, user, channel, message):
        user_name = user.split("!", 1)[0]
        if message.startswith("!predict "):
            self._thread(self.process_predict, server, user_name, channel, message[9:])
        elif message.startswith("!help"):
            self.safe_privmsg(server, user_name, HELP_MESSAGE)

    def on_pubmsg(self, server, user, channel, message):
        user_name = user.split("!", 1)[0]
        if message.startswith("!predict "):
            self._thread(self.process_predict, server, user_name, channel, message[9:])

    def update(self):
        if "scheduled_messages" not in self.settings:
            return
        # Only check once a minute:
        self.update_count += 1
        if self.update_count < 60:
            return
        now = datetime.now()
        self.update_count = now.second

        due = []
        remaining = []
        for msg in self.settings["scheduled_messages"]:
            if datetime.fromisoformat(msg["timestamp"]) <= now:
                due.append(msg)
            else:
                remaining.append(msg)
        for msg in due:
            self.safe_privmsg(msg["server"], msg["channel"], msg["message"])
        if due:
            self.settings["scheduled_messages"] = remaining
            self._save_settings(json.dumps(self.settings))


if __name__ == "__main__":
    sys.exit(Predicter.run())
