import unittest
from unittest.mock import MagicMock, patch
from plugins.wikilooker.wikilooker import WikiLooker


class TestWikiLooker(unittest.TestCase):
    def setUp(self):
        # Mocking Plugin.__init__ to avoid ZMQ socket setup
        with patch("plugin.Plugin.__init__") as mock_init:
            self.plugin = WikiLooker()
            self.plugin.default_lang = "en"
            self.plugin._thread = MagicMock()
            self.plugin.main_thread_ident = "main"

    def test_on_pubmsg_default_lang(self):
        self.plugin.on_pubmsg("server", "user", "#channel", "!wiki search query")
        self.plugin._thread.assert_called_once_with(
            self.plugin.process_wiki_query, "search query", "en", "server", "#channel"
        )

    def test_on_pubmsg_custom_lang(self):
        self.plugin.on_pubmsg("server", "user", "#channel", "!wiki_sv search query")
        self.plugin._thread.assert_called_once_with(
            self.plugin.process_wiki_query, "search query", "sv", "server", "#channel"
        )

    def test_on_pubmsg_no_query(self):
        self.plugin.on_pubmsg("server", "user", "#channel", "!wiki")
        self.plugin._thread.assert_not_called()

    def test_on_pubmsg_invalid_trigger(self):
        self.plugin.on_pubmsg("server", "user", "#channel", "!wikifoo bar")
        self.plugin._thread.assert_not_called()

    def test_started_sets_default_lang(self):
        self.plugin.started('{"default_lang": "sv"}')
        self.assertEqual(self.plugin.default_lang, "sv")

    def test_started_defaults_to_en(self):
        self.plugin.started("{}")
        self.assertEqual(self.plugin.default_lang, "en")

    @patch("plugins.wikilooker.wikilooker.WikiLooker._get_wiki_summary")
    @patch("plugins.wikilooker.wikilooker.WikiLooker._send_wiki_summary")
    def test_process_wiki_query_exact_match(self, mock_send, mock_get):
        mock_get.return_value = {"title": "Test Title", "extract": "Test Extract"}
        self.plugin.process_wiki_query("query", "en", "server", "#channel")
        mock_get.assert_called_once_with("query", "en")
        mock_send.assert_called_once_with(mock_get.return_value, "en", "server", "#channel")

    @patch("plugins.wikilooker.wikilooker.WikiLooker._get_wiki_summary")
    @patch("plugins.wikilooker.wikilooker.WikiLooker._opensearch")
    @patch("plugins.wikilooker.wikilooker.WikiLooker._send_wiki_summary")
    def test_process_wiki_query_single_suggestion(self, mock_send, mock_search, mock_get):
        expected_suggestion = {"title": "Suggestion", "extract": "Summary"}
        mock_get.side_effect = [None, expected_suggestion]
        mock_search.return_value = ["Suggestion"]
        self.plugin.safe_privmsg = MagicMock()

        self.plugin.process_wiki_query("query", "en", "server", "#channel")

        self.plugin.safe_privmsg.assert_called_once_with(
            "server", "#channel", "Did you mean: Suggestion"
        )
        self.assertEqual(mock_get.call_count, 2)
        mock_send.assert_called_once_with(expected_suggestion, "en", "server", "#channel")

    @patch("plugins.wikilooker.wikilooker.WikiLooker._get_wiki_summary")
    @patch("plugins.wikilooker.wikilooker.WikiLooker._opensearch")
    def test_process_wiki_query_multiple_suggestions(self, mock_search, mock_get):
        mock_get.return_value = None
        mock_search.return_value = ["Sug1", "Sug2", "Sug3"]
        self.plugin.safe_privmsg = MagicMock()

        self.plugin.process_wiki_query("query", "en", "server", "#channel")

        self.plugin.safe_privmsg.assert_called_once_with(
            "server", "#channel", "Could not find 'query'. Did you mean: Sug1, Sug2, Sug3"
        )

    @patch("plugins.wikilooker.wikilooker.WikiLooker._get_wiki_summary")
    @patch("plugins.wikilooker.wikilooker.WikiLooker._opensearch")
    def test_process_wiki_query_no_match(self, mock_search, mock_get):
        mock_get.return_value = None
        mock_search.return_value = []
        self.plugin.safe_privmsg = MagicMock()

        self.plugin.process_wiki_query("query", "en", "server", "#channel")

        self.plugin.safe_privmsg.assert_called_once_with(
            "server", "#channel", "Could not find a Wikipedia page for 'query'."
        )

    @patch("utils.auto_requests.get")
    def test_opensearch_filters_query(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = ["query", ["query", "suggestion"], [], []]
        mock_get.return_value = mock_response

        suggestions = self.plugin._opensearch("query", "en")
        self.assertEqual(suggestions, ["suggestion"])


if __name__ == "__main__":
    unittest.main()
