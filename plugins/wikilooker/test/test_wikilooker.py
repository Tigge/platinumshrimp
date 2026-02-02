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


if __name__ == "__main__":
    unittest.main()
