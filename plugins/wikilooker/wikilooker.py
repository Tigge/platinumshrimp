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
    It supports both English and Swedish Wikipedia.
    """

    def __init__(self):
        plugin.Plugin.__init__(self, "wikilooker")
        self.triggers = {
            "!wiki": "sv",
            "!wiki_en": "en",
        }
        # Sort triggers by length, longest first, to avoid partial matches like
        # '!wiki' matching a query for '!wiki_en'.
        self._sorted_triggers = sorted(self.triggers.keys(), key=len, reverse=True)

    def on_pubmsg(self, server: str, user: str, channel: str, message: str) -> None:
        """Handles public messages and triggers the Wikipedia lookup."""
        for trigger in self._sorted_triggers:
            if message.startswith(trigger):
                # Ensure the trigger is followed by a space, or is the whole message.
                # This prevents `!wikifoo` from triggering `!wiki`.
                if len(message) > len(trigger) and not message[len(trigger)].isspace():
                    continue

                lang = self.triggers[trigger]
                query = message[len(trigger):].strip()
                if query:
                    self._thread(self.process_wiki_query, query, lang, server, channel)
                
                # Found the correct trigger, no need to check for others.
                break

    def process_wiki_query(self, query: str, lang: str, server: str, channel: str) -> None:
        """
        Fetches and prints a Wikipedia summary for a given query and language.
        This method is intended to be run in a separate thread.
        """
        result = self._get_wiki_summary(query, lang)
        if result:
            summary = result["extract"]
            title = result["title"]
            
            # Split summary into sentences and send the first few to avoid spam.
            sentences = summary.split('. ')
            # Filter out any empty strings that might result from the split
            sentences = [s for s in sentences if s]
            
            output = '. '.join(sentences[:MAX_SUMMARY_SENTENCES]).strip()
            # Add ellipsis if the summary was truncated
            if len(sentences) > MAX_SUMMARY_SENTENCES:
                output += '...'

            # Construct the page URL
            quoted_title = urllib.parse.quote(title.replace(' ', '_'))
            url = f"https://{lang}.wikipedia.org/wiki/{quoted_title}"

            self.safe_privmsg(server, channel, f"{output} {url}")
        else:
            self.safe_privmsg(server, channel, f"Could not find a Wikipedia page for '{query}'.")

    def _get_wiki_summary(self, query: str, lang: str) -> Optional[dict]:
        """
        Queries the Wikipedia API for a given search term and returns a dictionary
        containing the page extract and title. Handles redirects automatically.
        """
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,       # Get only the content before the first section
            "explaintext": True,   # Get plain text instead of HTML
            "format": "json",
            "redirects": 1,        # Automatically resolve redirects
            "titles": query,
        }
        
        # Manually encode parameters as auto_requests may not handle the 'params' dict.
        query_string = urllib.parse.urlencode(params)
        url = f"{API_URL_TEMPLATE.format(lang=lang)}?{query_string}"
        
        # Wikipedia's API etiquette requires a custom User-Agent header.
        headers = {
            'User-Agent': 'PlatinumShrimpBot/1.0 (https://github.com/Tigge/platinumshrimp)'
        }

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
            logging.exception(f"An error occurred while fetching Wikipedia summary for '{query}': {e}")
        
        return None


if __name__ == "__main__":
    sys.exit(WikiLooker.run())
