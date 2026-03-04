import unittest
from unittest.mock import MagicMock, patch
import json
import datetime
from plugins.shrimpgemini.shrimpgemini import shrimpgemini


class TestShrimpGemini(unittest.TestCase):
    def setUp(self):
        self.plugin = shrimpgemini()
        # Mock settings for started()
        self.settings = json.dumps(
            {"key": "test-key", "trigger": "gemini:", "channel": "#test", "temperature": "0.5"}
        )
        self.plugin.started(self.settings)

    def test_started_temperature_is_float(self):
        self.assertEqual(self.plugin.temperature, 0.5)
        self.assertIsInstance(self.plugin.temperature, float)

    @patch("utils.gemini.get_response")
    def test_respond_to_message_includes_date_time(self, mock_get_response):
        mock_get_response.return_value = "Test response"
        self.plugin.safe_privmsg = MagicMock()

        # Test query
        query = "What time is it?"
        server = "test-server"
        channel = "#test"

        # Call the method
        self.plugin.respond_to_message(query, server, channel)

        # Check call arguments
        # messages should be the second argument
        args, kwargs = mock_get_response.call_args
        messages = args[1]

        # The system message should be the first in the list
        system_msg = messages[0]
        self.assertEqual(system_msg["role"], "system")

        # Check if "Current date and time" is in the system message content
        self.assertIn("Current date and time:", system_msg["content"])

        # Verify the date format
        now_str = datetime.datetime.now().astimezone().strftime("%A, %B %d, %Y")
        self.assertIn(now_str, system_msg["content"])

        # Verify timezone is present (e.g., UTC, CET, etc.)
        tz_str = datetime.datetime.now().astimezone().strftime("%Z")
        self.assertIn(tz_str, system_msg["content"])


if __name__ == "__main__":
    unittest.main()
