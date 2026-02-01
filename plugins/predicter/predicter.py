import json
import sys
import logging
import re
from datetime import datetime, timedelta

import plugin

HELP_MESSAGE = "Usage: !predict #channel [YYYY-MM-DD] [HH:MM] message"


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

    def process_predict(self, server, user_name, channel, full_message):
        logging.info(f"Predicter.process_predict {user_name}: {full_message}")
        target_channel, message = "", ""
        try:
            target_channel, message = full_message.split(" ", 1)
        except:
            logging.info("Failed initial parsing")
            self.safe_privmsg(server, user_name, HELP_MESSAGE)
            return

        # Regex to extract optional date and time
        datetime_match = re.match(r"(?:(\d{4}-\d{2}-\d{2}))?\s*(?:(\d{2}:\d{2}))?\s*(.*)", message)
        date_str, time_str, msg = datetime_match.groups()  # I don't think this can fail?

        now = datetime.now()
        if date_str:
            # If we got a date, we use it
            year, month, day = map(int, date_str.split("-"))
            date = datetime(year, month, day)
        else:
            # Otherwise, we use todays date
            date = now

        if time_str:
            # If we got a time, we use that together with the date
            hour, minute = map(int, time_str.split(":"))
            target_dt = datetime.combine(date.date(), datetime.min.time()) + timedelta(
                hours=hour, minutes=minute
            )
        elif date_str:
            # If we don't have a time, we send the message at noon
            target_dt = datetime.combine(date.date(), datetime.min.time()) + timedelta(hours=12)
        else:
            # Neither time nor date, send message at the next minute and send a warning to the user
            target_dt = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            self.safe_privmsg(server, user_name, "No time or date specified, scheduling now!")

        # If the time has already lapsed, give a warning to the user (but still schedule the msg):
        if target_dt <= now:
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
