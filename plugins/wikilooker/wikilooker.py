import json
import logging
import sys
import urllib.parse
from typing import Optional

import plugin
from utils import auto_requests

API_URL_TEMPLATE = "https://{lang}.wikipedia.org/w/api.php"
# To avoid spamming, we only print the first few sentences of the summary.
MAX_SUMMARY_SENTENCES = 3


class WikiLooker(plugin.Plugin):
    """
    A plugin that looks up and prints summaries from Wikipedia.
    It supports multiple languages.  You can set a "default_lang" in settings:
    "wikilooker": {
        "default_lang": "sv"
    }

    You can specify the language in your query:
    !wiki[_lang] Mikael Persbrandt
    """

    def __init__(self):
        plugin.Plugin.__init__(self, "wikilooker")
        self.default_lang = "en"

    def started(self, settings: str) -> None:
        try:
            self.settings = json.loads(settings)
            self.default_lang = self.settings.get("default_lang", "en")
        except Exception:
            logging.exception("Failed to load settings for WikiLooker")
            self.default_lang = "en"

    def on_pubmsg(self, server: str, user: str, channel: str, message: str) -> None:
        if not message.startswith("!wiki"):
            return

        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            return

        trigger = parts[0]
        query = parts[1]

        if trigger == "!wiki":
            lang = self.default_lang
        elif trigger.startswith("!wiki_"):
            lang = trigger[len("!wiki_") :]
            if not lang:
                return
        else:
            # Matches something like !wikifoo, which we ignore.
            return

        self._thread(self.process_wiki_query, query, lang, server, channel)

    def process_wiki_query(self, query: str, lang: str, server: str, channel: str) -> None:
        result = self._get_wiki_summary(query, lang)
        if result:
            self._send_wiki_summary(result, lang, server, channel)
        else:
            suggestions = self._opensearch(query, lang)
            if len(suggestions) == 1:
                suggestion = suggestions[0]
                self.safe_privmsg(server, channel, f"Did you mean: {suggestion}")
                result = self._get_wiki_summary(suggestion, lang)
                if result:
                    self._send_wiki_summary(result, lang, server, channel)
            elif len(suggestions) > 1:
                self.safe_privmsg(
                    server,
                    channel,
                    f"Could not find '{query}'. Did you mean: " + ", ".join(suggestions),
                )
            else:
                self.safe_privmsg(
                    server, channel, f"Could not find a Wikipedia page for '{query}'."
                )

    def _send_wiki_summary(self, result: dict, lang: str, server: str, channel: str) -> None:
        summary = result["extract"]
        title = result["title"]

        # Split summary into sentences and send the first few to avoid spam.
        sentences = summary.split(". ")
        # Filter out any empty strings that might result from the split
        sentences = [s for s in sentences if s]

        output = ". ".join(sentences[:MAX_SUMMARY_SENTENCES]).strip()
        # Add ellipsis if the summary was truncated
        if len(sentences) > MAX_SUMMARY_SENTENCES:
            output += "..."

        # Construct the page URL
        quoted_title = urllib.parse.quote(title.replace(" ", "_"))
        url = f"https://{lang}.wikipedia.org/wiki/{quoted_title}"

        self.safe_privmsg(server, channel, f"{output} {url}")

    def _opensearch(self, query: str, lang: str) -> list:
        params = {
            "action": "opensearch",
            "search": query,
            "limit": 7,
            "namespace": 0,
            "format": "json",
        }
        # Manually encode parameters as auto_requests may not handle the 'params' dict.
        query_string = urllib.parse.urlencode(params)
        url = f"{API_URL_TEMPLATE.format(lang=lang)}?{query_string}"

        # Wikipedia's API etiquette requires a custom User-Agent header.
        headers = {"User-Agent": "PlatinumShrimpBot/1.0 (https://github.com/Tigge/platinumshrimp)"}

        try:
            response = auto_requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            # Opensearch returns [query, [titles], [descriptions], [urls]]
            if len(data) >= 2 and isinstance(data[1], list):
                suggestions = data[1]
                # Filter out the original query to avoid redundant "did you mean"
                return [s for s in suggestions if s.lower() != query.lower()]
        except Exception:
            logging.exception(f"An error occurred during Opensearch for '{query}'")

        return []

    def _get_wiki_summary(self, query: str, lang: str) -> Optional[dict]:
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,  # Get only the content before the first section
            "explaintext": True,  # Get plain text instead of HTML
            "format": "json",
            "redirects": 1,  # Automatically resolve redirects
            "titles": query,
        }

        # Manually encode parameters as auto_requests may not handle the 'params' dict.
        query_string = urllib.parse.urlencode(params)
        url = f"{API_URL_TEMPLATE.format(lang=lang)}?{query_string}"

        # Wikipedia's API etiquette requires a custom User-Agent header.
        headers = {"User-Agent": "PlatinumShrimpBot/1.0 (https://github.com/Tigge/platinumshrimp)"}

        try:
            response = auto_requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            if not pages:
                logging.warning(f"Wikipedia API returned no pages for query: {query}")
                return None

            # The page ID is the first key in the 'pages' dict.
            # A page_id of -1 means the page does not exist.
            page_id = next(iter(pages))
            if page_id == "-1":
                return None

            page_data = pages[page_id]
            extract = page_data.get("extract")
            title = page_data.get("title")

            # The extract can be empty for disambiguation pages.
            if extract and title:
                return {"extract": extract, "title": title}

            return None
        except Exception as e:
            logging.exception(
                f"An error occurred while fetching Wikipedia summary for '{query}': {e}"
            )

        return None


if __name__ == "__main__":
    sys.exit(WikiLooker.run())
