import logging
from urllib.parse import urlparse
from plugins.feedretriever.feedpoller import FeedPoller
from plugins.feedretriever.pollerfactory import PollerFactory
from utils import auto_requests, str_utils

REDDIT_URL_TOKEN = "reddit.com"
MAX_LRU_SIZE = 50
MAX_NEW_MESSAGES = 7


class RedditEntry:
    def __init__(self, id, title, link):
        self.id = id
        self.title = title
        self.link = link


class RedditFeedMeta:
    def __init__(self, title):
        self.title = title


class RedditFeed:
    def __init__(self, title, entries):
        self.feed = RedditFeedMeta(title)
        self.entries = entries
        self.bozo = 0 if entries is not None else 1


@PollerFactory.register(REDDIT_URL_TOKEN)
class RedditPoller(FeedPoller):
    def __init__(self, feed, on_created, on_entry, on_error):
        self.seen_ids = []
        # FeedPoller.__init__ calls self.read() and self._set_last()
        super().__init__(feed, on_created, on_entry, on_error)

    def read(self, url, modified=None, etag=None):
        logging.info(f"RedditPoller.read: {url}")

        try:
            base_url_obj = urlparse(url)
            # Ensure we get JSON by appending .json to the path
            path = base_url_obj.path.rstrip("/")
            json_url = f"{base_url_obj.scheme}://{base_url_obj.netloc}{path}/.json"
            if base_url_obj.query:
                json_url += f"?{base_url_obj.query}"

            response = auto_requests.get(json_url)
            if response is None or response.status_code != 200:
                logging.error(
                    f"RedditPoller failed to fetch {json_url}, status: {getattr(response, 'status_code', 'None')}"
                )
                return RedditFeed(None, None)

            data = response.json()

            subreddit_title = "Reddit"
            entries = []

            if "data" in data and "children" in data["data"]:
                children = data["data"]["children"]
                if children:
                    # Try to get a more descriptive title if possible
                    subreddit_title = "r/" + children[0]["data"]["subreddit"]

                domain = f"{base_url_obj.scheme}://{base_url_obj.netloc}"
                for child in children:
                    post = child["data"]
                    # Skip stickied posts if desired? Usually front page has stickies.
                    # For now we include everything on the front page as requested.

                    # permalink is like /r/sweden/comments/...
                    link = domain + post["permalink"]
                    entries.append(RedditEntry(post["name"], post["title"], link))

            return RedditFeed(subreddit_title, entries)
        except Exception as e:
            logging.exception(f"RedditPoller exception during read of {url}")
            return RedditFeed(None, None)

    def _set_last(self, entries):
        # This is called during __init__ to populate the initial "seen" list
        # and would be called by FeedPoller.update_now if we didn't override it.
        if not entries:
            return

        # Process entries in reverse (bottom of page first) to populate LRU correctly
        for entry in reversed(entries):
            self._update_lru(entry.id)

    def _update_lru(self, entry_id):
        if entry_id in self.seen_ids:
            self.seen_ids.remove(entry_id)
        self.seen_ids.append(entry_id)
        if len(self.seen_ids) > MAX_LRU_SIZE:
            self.seen_ids.pop(0)

    def update_now(self):
        parsed = self.read(self.feed["url"])
        if parsed.bozo == 1:
            self.consecutive_fails += 1
            if self.consecutive_fails % 10 == 0:
                self.on_error(self.feed, "Failed to fetch Reddit feed")
            return

        new_entries = []
        # Process entries in reverse to keep LRU order consistent with "newness"
        for entry in reversed(parsed.entries):
            if entry.id not in self.seen_ids:
                new_entries.append(entry)

            # Always update LRU to keep it fresh
            self._update_lru(entry.id)

        # Report new entries. Since new_entries is [bottom_most_new, ..., top_most_new],
        # we report from the end of the list to show the top-most new post last in chat.
        report_count = 0
        for entry in reversed(new_entries):
            if report_count >= MAX_NEW_MESSAGES:
                break
            self.on_entry(self.feed, entry)
            report_count += 1

        self.consecutive_fails = 0
