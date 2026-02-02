import json
import logging
import re
import sys
from typing import Any, Dict, List, Optional

import plugin
from utils import auto_requests

URL = "https://svenska.se/api/msearch"
CONTENT = {
    "saol": {"index": "sa-svenska-saol", "query": "", "exact_match": True, "from": 0, "size": 10},
    "so": {"index": "sa-svenska-so", "query": "", "exact_match": True, "from": 0, "size": 0},
    "saob": {"index": "sa-svenska-saob", "query": "", "exact_match": True, "from": 0, "size": 0},
}


class SAOLChecker(plugin.Plugin):
    """
    A plugin to check words against the Swedish dictionary SAOL (Svenska Akademiens ordlista).
    It can handle definitions, examples, and various types of redirects.
    """

    def __init__(self):
        plugin.Plugin.__init__(self, "saolchecker")
        self.trigger = "!saol"

    def on_pubmsg(self, server: str, user: str, channel: str, message: str) -> None:
        if not message.startswith(self.trigger):
            return

        query = message[len(self.trigger) + 1:].strip()
        if query:
            self._thread(self.process_query, query, server, channel)

    def process_query(self, query: str, server: str, channel: str) -> None:
        """
        Orchestrates the process of querying SAOL and printing the results.

        1. Makes a request to the API.
        2. If the response contains redirects, follows them.
        3. If not, prints definitions, examples, and suggestions.
        """
        response_json = self._make_request(query)
        if not response_json:
            return

        # If any redirects are found and processed, we stop here.
        if self._handle_redirects(query, response_json, server, channel):
            return

        # If no redirects, process the content of the response.
        self._print_definitions(response_json, server, channel)
        self._print_did_you_mean(response_json, server, channel)

    def _make_request(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Performs the POST request to the SAOL API and returns the parsed JSON response.
        Returns None on failure.
        """
        content_json = CONTENT
        content_json["saol"]["query"] = query
        content = json.dumps(content_json)

        try:
            response = auto_requests.post(
                URL, headers={"content-type": "application/json"}, content=content
            )
            response.raise_for_status()  # Raises an exception for bad status codes
            return response.json()
        except auto_requests.exceptions.RequestException as e:
            logging.exception(f"SAOL request failed: {e}")
        except json.JSONDecodeError as e:
            logging.exception(f"Failed to parse SAOL response: {e}")
        
        return None

    def _handle_redirects(self, query: str, response_json: Dict[str, Any], server: str, channel: str) -> bool:
        """
        Checks for and handles all types of redirects.

        Returns:
            bool: True if a redirect was found and handled, False otherwise.
        """
        saol_hits = response_json.get("saol", {}).get("hits", {}).get("hits", [])
        if not saol_hits:
            return False

        redirected_queries: List[str] = []

        # First, check for top-level redirects which are considered final.
        # If one is found, we process it and immediately stop.
        for hit in saol_hits:
            source = hit.get("_source", {})
            if "enbartDigitalaHänvisningar" in source:
                self._process_redirect_list(
                    query,
                    source["enbartDigitalaHänvisningar"],
                    redirected_queries,
                    server,
                    channel,
                )
                return True

        # Second, check for nested redirects within the word's meanings.
        # We collect and process all of them.
        redirects_found = False
        for hit in saol_hits:
            source = hit.get("_source", {})
            if "huvudbetydelser" in source:
                for meaning in source["huvudbetydelser"]:
                    if "hänvisningar" in meaning:
                        redirects_found = True
                        refs = [ref["hänvisning"] for ref in meaning["hänvisningar"]]
                        self._process_redirect_list(
                            query, refs, redirected_queries, server, channel
                        )

        return redirects_found

    def _process_redirect_list(
        self,
        original_query: str,
        redirects: List[str],
        redirected_queries: List[str],
        server: str,
        channel: str,
    ) -> None:
        """Helper to process a list of raw redirect strings."""
        for redirect_raw in redirects:
            # The redirect text can be like "word 1", so we clean it and take the first part.
            new_query = self._clean_html(redirect_raw).strip().split(" ")[0]
            if new_query and new_query not in redirected_queries:
                redirected_queries.append(new_query)
                self.privmsg(server, channel, f"'{original_query}' hänvisar till: {new_query}")
                self.process_query(new_query, server, channel)

    def _print_definitions(self, response_json: Dict[str, Any], server: str, channel: str) -> None:
        """Finds and prints the definitions and examples for a word."""
        saol_hits = response_json.get("saol", {}).get("hits", {}).get("hits", [])
        for hit in saol_hits:
            source = hit.get("_source", {})
            if "huvudbetydelser" in source:
                for meaning in source["huvudbetydelser"]:
                    if "definition" in meaning:
                        result = self._clean_html(meaning["definition"])
                        self.privmsg(server, channel, result)
                    if "exempel" in meaning:
                        for example in meaning["exempel"]:
                            example_text = self._clean_html(example["text"])
                            self.privmsg(server, channel, "Exempel: " + example_text)

    def _print_did_you_mean(self, response_json: Dict[str, Any], server: str, channel: str) -> None:
        """Finds and prints 'did you mean' suggestions."""
        suggestions = response_json.get("saol", {}).get("didYouMean", [])
        for suggestion in suggestions:
            result = self._clean_html(suggestion["text"])
            self.privmsg(server, channel, "Menade du: " + result)

    def _clean_html(self, raw_html: str) -> str:
        """Removes HTML tags from a string."""
        return re.sub("<[^>]+>", "", raw_html)


if __name__ == "__main__":
    sys.exit(SAOLChecker.run())
