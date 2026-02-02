import unittest
import json
import os
from unittest.mock import MagicMock, patch
from plugins.saolchecker.saolchecker import SAOLChecker


class TestSAOLChecker(unittest.TestCase):
    def setUp(self):
        self.plugin = SAOLChecker()
        self.plugin.privmsg = MagicMock()
        # Mock auto_requests to avoid real network calls and missing attribute errors
        self.patcher = patch("plugins.saolchecker.saolchecker.auto_requests")
        self.mock_requests = self.patcher.start()

        # Setup dummy exceptions to avoid AttributeError in the plugin
        if not hasattr(self.mock_requests, "exceptions"):
            self.mock_requests.exceptions = MagicMock()
            self.mock_requests.exceptions.RequestException = Exception

    def tearDown(self):
        self.patcher.stop()

    def _load_data(self, filename):
        data_path = os.path.join(os.path.dirname(__file__), "data", filename)
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _mock_response(self, data):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = data
        return response

    def test_direct_definition(self):
        """Test a normal query with a definition and no redirects."""
        data = self._load_data("direct_definition.json")
        self.mock_requests.post.return_value = self._mock_response(data)

        self.plugin.process_query("testord", "server", "#channel")

        self.plugin.privmsg.assert_any_call("server", "#channel", "En test-definition")
        self.plugin.privmsg.assert_any_call("server", "#channel", "Exempel: Ett test-exempel")

    def test_single_redirect(self):
        """Test that a single redirect is followed and definitions are printed."""

        def side_effect(url, headers, content):
            query = json.loads(content)["saol"]["query"]
            if query == "ursprung":
                return self._mock_response(self._load_data("single_redirect_source.json"))
            else:
                return self._mock_response(self._load_data("single_redirect_target.json"))

        self.mock_requests.post.side_effect = side_effect

        self.plugin.process_query("ursprung", "server", "#channel")

        self.plugin.privmsg.assert_any_call(
            "server", "#channel", "'ursprung' hänvisar till: målord"
        )
        self.plugin.privmsg.assert_any_call("server", "#channel", "Definition av målord")

    def test_circular_redirect_loop(self):
        """Test that a circular redirect loop is detected and broken."""

        def side_effect(url, headers, content):
            query = json.loads(content)["saol"]["query"]
            if query == "makro":
                return self._mock_response(self._load_data("circular_makro.json"))
            elif query == "mikro-":
                return self._mock_response(self._load_data("circular_mikro_minus.json"))
            elif query == "makro-":
                return self._mock_response(self._load_data("circular_makro_minus.json"))
            return self._mock_response({"saol": {"hits": {"hits": []}}})

        self.mock_requests.post.side_effect = side_effect

        # This should not raise RecursionError or loop infinitely
        self.plugin.process_query("makro", "server", "#channel")

        # Should see 3 redirect messages before stopping
        # 1. makro -> mikro-
        # 2. mikro- -> makro-
        # 3. makro- -> mikro-
        # (The 4th step: mikro- is already in seen_queries, so it returns)
        self.assertEqual(self.plugin.privmsg.call_count, 3)

        calls = [call[0][2] for call in self.plugin.privmsg.call_args_list]
        self.assertIn("'makro' hänvisar till: mikro-", calls)
        self.assertIn("'mikro-' hänvisar till: makro-", calls)
        self.assertIn("'makro-' hänvisar till: mikro-", calls)

    def test_nested_redirects(self):
        """Test redirects found within meanings (huvudbetydelser)."""

        def side_effect(url, headers, content):
            query = json.loads(content)["saol"]["query"]
            if query == "start":
                return self._mock_response(self._load_data("nested_redirect_start.json"))
            else:
                return self._mock_response(self._load_data("nested_redirect_final.json"))

        self.mock_requests.post.side_effect = side_effect
        self.plugin.process_query("start", "server", "#channel")

        self.plugin.privmsg.assert_any_call(
            "server", "#channel", "'start' hänvisar till: annat-ord"
        )
        self.plugin.privmsg.assert_any_call("server", "#channel", "Slutgiltig definition")


if __name__ == "__main__":
    unittest.main()
