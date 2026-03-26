# This plugin logs IRC events to an SQLite database.
# It tracks public messages, private messages, actions, joins, parts, quits, nick changes, and kicks.
#
# You can configure which servers and channels to log using a whitelist or a blacklist.
# If a whitelist is defined, only those servers/channels will be logged.
# If no whitelist is defined, the blacklist will be used to exclude specific servers/channels.
#
# Sample setting:
#
# "sqllogger": {
#   "db_path": "tools/sqllogger/log.db",
#   "whitelist": {
#     "servers": {
#       "irc.example.net": ["#channel1", "#channel2"],
#       "irc.another.net": [] # Log all channels on this server
#     }
#   },
#   "blacklist": {
#     "servers": {
#       "irc.noisy.net": [] # Do not log anything from this server
#     }
#   }
# }
#
# All parameters are optional.
# "db_path" defaults to "tools/sqllogger/log.db".

import plugin
import logging

import sqlite3
import os
import json
import sys
from time import time

DEFAULT_DB_PATH = "tools/sqllogger/log.db"


class SQLLogger(plugin.Plugin):

    def __init__(self) -> None:
        plugin.Plugin.__init__(self, "sqllogger")

    def started(self, settings) -> None:
        logging.info("SQLLogger.started: " + settings)
        self.settings = json.loads(settings)
        if "db_path" not in self.settings:
            self.settings["db_path"] = DEFAULT_DB_PATH
            self._save_settings(json.dumps(self.settings))

        db_path = self.settings["db_path"]

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server TEXT,
                channel TEXT,
                nickname TEXT,
                username TEXT,
                hostname TEXT,
                timestamp INTEGER,
                event_type TEXT,
                message TEXT
            )
        """)
        self.conn.commit()

        # Load optional whitelist/blacklist structure
        self.whitelist = self.settings.get("whitelist", {}).get("servers", {})
        self.blacklist = self.settings.get("blacklist", {}).get("servers", {})

    def close(self):
        """Close database connection and call parent close."""
        if hasattr(self, "conn"):
            self.conn.close()
        super().close()

    def _is_listed(self, listing, server, channel) -> bool:
        """Returns True if server/channel is in the provided whitelist/blacklist."""
        if server in listing:
            channels = listing[server]
            if not channels:  # Entire server is listed
                return True
            elif channel in channels:  # Specific channel is listed
                return True
        return False

    def _should_log(self, server, channel):
        # Whitelist takes precedence if defined
        if self.whitelist:
            return self._is_listed(self.whitelist, server, channel)

        # Otherwise, exclude if blacklisted
        if self.blacklist and self._is_listed(self.blacklist, server, channel):
            return False

        return True

    def _log(self, server, user, channel, event_type, message="") -> None:
        if not self._should_log(server, channel):
            return

        if "!" in user and "@" in user:
            nickname, rest = user.split("!", 1)
            username, hostname = rest.split("@", 1)
        else:
            nickname = username = hostname = user

        timestamp = int(time())
        self.cursor.execute(
            """
            INSERT INTO logs (server, channel, nickname, username, hostname, timestamp, event_type, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (server, channel, nickname, username, hostname, timestamp, event_type, message),
        )
        self.conn.commit()

    def on_pubmsg(self, server, user, channel, message) -> None:
        self._log(server, user, channel, "pubmsg", message)

    def on_privmsg(self, server, user, channel, message) -> None:
        self._log(server, user, channel, "privmsg", message)

    def on_action(self, server, user, channel, message) -> None:
        self._log(server, user, channel, "action", message)

    def on_me_pubmsg(self, server, user, channel, message) -> None:
        self._log(server, user, channel, "pubmsg", message)

    def on_me_privmsg(self, server, user, channel, message) -> None:
        self._log(server, user, channel, "privmsg", message)

    def on_me_action(self, server, user, channel, message) -> None:
        self._log(server, user, channel, "action", message)

    def on_join(self, server, user, channel, *args) -> None:
        self._log(server, user, channel, "join")

    def on_part(self, server, user, channel, *args) -> None:
        message = args[0] if args else ""
        self._log(server, user, channel, "part", message)

    def on_quit(self, server, user, channel, *args) -> None:
        message = args[0] if args else ""
        self._log(server, user, "", "quit", message)

    def on_nick(self, server, user, channel, *args) -> None:
        new_nick = channel
        self._log(server, user, "", "nick", new_nick)

    def on_kick(self, server, user, channel, *args) -> None:
        kicked_nick = args[0] if len(args) > 0 else ""
        reason = args[1] if len(args) > 1 else ""
        self._log(server, user, channel, "kick", f"{kicked_nick} ({reason})")


if __name__ == "__main__":
    sys.exit(SQLLogger.run())
