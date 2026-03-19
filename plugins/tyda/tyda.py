import logging
import re
import sys
from typing import Any, Dict, List, Optional

import plugin
from utils import auto_requests, str_utils

URL = "https://tyda.se/search/"


class Tyda(plugin.Plugin):
    """
    A plugin to translate words between Swedish and English using tyda.se.
    """

    def __init__(self, name="tyda"):
        plugin.Plugin.__init__(self, name)
        self.trigger = "!tyda"

    def on_pubmsg(self, server: str, user: str, channel: str, message: str) -> None:
        if not message.startswith(self.trigger):
            return

        query = message[len(self.trigger) + 1 :].strip()
        if query:
            self._thread(self.process_query, query, server, channel)

    def process_query(self, query: str, server: str, channel: str) -> None:
        translations = self.lookup(query)
        for translation in translations:
            self.safe_privmsg(server, channel, translation)

    def lookup(self, query: str) -> List[str]:
        """
        Returns a list of formatted translation strings.
        """
        response = self._make_request(query)
        if not response:
            return []

        all_results = self._parse_translations(response.text)

        # Remove deduplicates while preserving order
        unique_results = []
        for res in all_results:
            if res not in unique_results:
                unique_results.append(res)

        return unique_results

    def _make_request(self, query: str) -> Optional[auto_requests.httpx.Response]:
        try:
            response = auto_requests.get(URL + query)
            response.raise_for_status()
            return response
        except Exception as e:
            logging.exception(f"Tyda request failed: {e}")
        return None

    def _parse_translations(self, html_content: str) -> List[str]:
        """
        Parses the HTML content and extracts translations.
        Groups translations that share a domain.
        """
        results = []

        # Find all translation blocks
        # Each block is a <div class="list-translation-outer">
        blocks = re.findall(
            r'<div class="list-translation-outer">.*?</ul>\s*</div>', html_content, re.DOTALL
        )

        for block in blocks:
            # Within each block, find the translations in <li> tags
            # <li class="item text">...</li>
            items = re.findall(r'<li class="item text">.*?</li>', block, re.DOTALL)

            current_group = []

            for item in items:
                # Extract the translation text from the <a> tag
                # <a href="...">text</a>
                text_match = re.search(r'<a href="/search/[^>]+>([^<]+)</a>', item)
                if text_match:
                    translation = text_match.group(1).strip()
                    current_group.append(translation)

                    # Extract the domain if present
                    # <span class="trans-desc" ...>[&nbsp;domain&nbsp;]</span>
                    domain_match = re.search(r'<span class="trans-desc"[^>]*>(.*?)</span>', item)
                    if domain_match:
                        domain = self._clean_html(domain_match.group(1))
                        domain = str_utils.unescape_entities(domain)
                        domain = domain.replace("[", "").replace("]", "").strip()
                        # Normalize whitespace
                        domain = " ".join(domain.split())

                        results.append(f"{' '.join(current_group)} [ {domain} ]")
                        current_group = []

            # If any translations are left without a domain, add them
            if current_group:
                results.append(" ".join(current_group))

        return results

    def _clean_html(self, raw_html: str) -> str:
        """Removes HTML tags from a string."""
        return re.sub("<[^>]+>", "", raw_html)


if __name__ == "__main__":
    sys.exit(Tyda.run())
