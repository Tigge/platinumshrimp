import json
import unittest
from datetime import datetime, timedelta

from plugins.predicter.predicter import HELP_MESSAGE, Predicter


class DummyPredicter(Predicter):
    def __init__(self):
        self.update_count = 0
        self.settings = {"scheduled_messages": []}
        self.privmsgs = []
        self.safe_privmsgs = []

    def privmsg(self, server, channel, message):
        self.privmsgs.append((server, channel, message))

    def safe_privmsg(self, server, channel, message):
        self.safe_privmsgs.append((server, channel, message))

    def _save_settings(self, settings):
        self.settings = json.loads(settings)


class TestPredicterPlugin(unittest.TestCase):
    def setUp(self):
        self.bot = DummyPredicter()

    def test_process_predict_relative_duration(self):
        self.bot.process_predict("irc.server", "alice", "#test", "#test 117h 32m price reaches 100")
        self.assertEqual(len(self.bot.settings["scheduled_messages"]), 1)
        scheduled = self.bot.settings["scheduled_messages"][0]
        self.assertEqual(scheduled["server"], "irc.server")
        self.assertEqual(scheduled["channel"], "#test")
        self.assertIn("price reaches 100", scheduled["message"])
        self.assertEqual(len(self.bot.privmsgs), 1)
        self.assertIn("Message scheduled for", self.bot.privmsgs[0][2])

    def test_process_predict_absolute_datetime(self):
        self.bot.process_predict(
            "irc.server", "bob", "#test", "#test 2099-01-01 12:00 new century begins"
        )
        self.assertEqual(len(self.bot.settings["scheduled_messages"]), 1)
        scheduled = self.bot.settings["scheduled_messages"][0]
        self.assertIn("2099-01-01T12:00:00", scheduled["timestamp"])
        self.assertIn("new century begins", scheduled["message"])

    def test_process_predict_missing_date_time_warning(self):
        self.bot.process_predict("irc.server", "carol", "#test", "#test just a message")
        self.assertEqual(len(self.bot.settings["scheduled_messages"]), 1)
        self.assertEqual(len(self.bot.safe_privmsgs), 1)
        self.assertEqual(
            self.bot.safe_privmsgs[0][2],
            "No time or date specified, scheduling now!",
        )

    def test_process_predict_past_time_warning(self):
        self.bot.process_predict(
            "irc.server", "dave", "#test", "#test 2000-01-01 00:00 in the past"
        )
        self.assertEqual(len(self.bot.settings["scheduled_messages"]), 1)
        self.assertEqual(len(self.bot.safe_privmsgs), 1)
        self.assertEqual(
            self.bot.safe_privmsgs[0][2],
            "Time and date is before now, scheduling now!",
        )

    def test_process_predict_invalid_args(self):
        self.bot.process_predict("irc.server", "eve", "#test", "")
        self.assertEqual(len(self.bot.safe_privmsgs), 1)
        self.assertEqual(self.bot.safe_privmsgs[0][2], HELP_MESSAGE)
        self.assertEqual(len(self.bot.settings["scheduled_messages"]), 0)

    def test_update_delivers_due_messages(self):
        past_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        self.bot.settings["scheduled_messages"] = [
            {
                "server": "irc.server",
                "channel": "#test",
                "message": "due msg",
                "timestamp": past_time,
            },
            {
                "server": "irc.server",
                "channel": "#test",
                "message": "future msg",
                "timestamp": future_time,
            },
        ]
        self.bot.update_count = 59  # Next update will trigger the check
        self.bot.update()

        # Due message should be sent
        self.assertEqual(len(self.bot.safe_privmsgs), 1)
        self.assertEqual(self.bot.safe_privmsgs[0][2], "due msg")

        # Future message remains scheduled
        self.assertEqual(len(self.bot.settings["scheduled_messages"]), 1)
        self.assertEqual(self.bot.settings["scheduled_messages"][0]["message"], "future msg")


if __name__ == "__main__":
    unittest.main()
