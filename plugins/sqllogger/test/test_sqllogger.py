import unittest
import tempfile
import os
import json
import sqlite3
from plugins.sqllogger.sqllogger import SQLLogger  # Adjust this import as needed


class TestSQLLogger(unittest.TestCase):

    def setUp(self) -> None:
        # Create a temp SQLite DB file
        self.db_fd, self.db_path = tempfile.mkstemp()

    def tearDown(self) -> None:
        os.close(self.db_fd)
        os.remove(self.db_path)

    def init_logger(self, settings):
        logger = SQLLogger()
        logger.started(json.dumps(settings))
        return logger

    def fetch_latest_log(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT server, channel, nickname, username, hostname, timestamp, message FROM logs ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        conn.close()
        return row

    def test_logging_allowed_by_whitelist(self) -> None:
        settings = {
            "db_path": self.db_path,
            "whitelist": {"servers": {"testserver": ["#testchannel"]}},
        }
        logger = self.init_logger(settings)
        logger.on_pubmsg("testserver", "nick!user@host", "#testchannel", "Allowed msg")
        log = self.fetch_latest_log()
        self.assertIsNotNone(log)
        self.assertEqual(log[6], "Allowed msg")

    def test_logging_blocked_not_in_whitelist(self) -> None:
        settings = {"db_path": self.db_path, "whitelist": {"servers": {"testserver": ["#allowed"]}}}
        logger = self.init_logger(settings)
        logger.on_pubmsg("testserver", "nick!user@host", "#other", "Blocked msg")
        log = self.fetch_latest_log()
        self.assertIsNone(log)

    def test_logging_blocked_entire_server_blacklist(self) -> None:
        settings = {"db_path": self.db_path, "blacklist": {"servers": {"badserver": []}}}
        logger = self.init_logger(settings)
        logger.on_pubmsg("badserver", "nick!user@host", "#any", "Blocked by server")
        log = self.fetch_latest_log()
        self.assertIsNone(log)

    def test_logging_blocked_by_channel_blacklist(self) -> None:
        settings = {"db_path": self.db_path, "blacklist": {"servers": {"testserver": ["#blocked"]}}}
        logger = self.init_logger(settings)
        logger.on_pubmsg("testserver", "nick!user@host", "#blocked", "Blocked by channel")
        log = self.fetch_latest_log()
        self.assertIsNone(log)

    def test_logging_allowed_if_not_blacklisted(self) -> None:
        settings = {"db_path": self.db_path, "blacklist": {"servers": {"testserver": ["#blocked"]}}}
        logger = self.init_logger(settings)
        logger.on_pubmsg("testserver", "nick!user@host", "#allowed", "Allowed message")
        log = self.fetch_latest_log()
        self.assertIsNotNone(log)
        self.assertEqual(log[6], "Allowed message")

    def test_logging_when_no_whitelist_or_blacklist(self) -> None:
        settings = {"db_path": self.db_path}
        logger = self.init_logger(settings)
        logger.on_pubmsg("freeserver", "someone!foo@bar", "#general", "No filters")
        log = self.fetch_latest_log()
        self.assertIsNotNone(log)
        self.assertEqual(log[6], "No filters")

    def test_malformed_user_string(self) -> None:
        settings = {"db_path": self.db_path}
        logger = self.init_logger(settings)
        logger.on_pubmsg("anyserver", "badformat", "#test", "Malformed user")
        log = self.fetch_latest_log()
        self.assertEqual(log[2], "badformat")
        self.assertEqual(log[3], "badformat")
        self.assertEqual(log[4], "badformat")
