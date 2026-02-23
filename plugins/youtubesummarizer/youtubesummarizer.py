# Plugin that summarizes given youtube videos using Gemini.
#
# Sample setting:
#
# "youtubesummarizer": {
#   "key": "your-gemini-app-key",
#   "yt-key": "your-youtube-api-key",
#   "channel": "#youtube",
#   "model": "gemini-2.5-flash",
#   "max_tokens": 4096,
#   "temperature": 0.2
# }
#
# The only required parameter is "key".
# If "yt-key" is not specified, you could get a bit worse summary as some information
# will not be passed on to gemini.
#
# Commands:
# * !gemini yt-summary https://www.youtube.com/watch?v=jNQXAC9IVRw

import logging
import sys
import json
import plugin

from youtube_transcript_api import YouTubeTranscriptApi
from utils import youtube, gemini

YT_PROMPT = """
            Summarize the content of this YouTube video.  End by giving a highlight link to the
            most important part of the video in the form of https://youtu.be/[id]?t=[timestamp]
            """
DEFAULT_MODEL = "gemini-2.5-flash"


class youtubesummarizer(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "youtubesummarizer")

    def started(self, settings):
        s = json.loads(settings)
        self.key = s["key"]
        self.yt_key = s["yt-key"] if "yt-key" in s else ""
        self.channel = s["channel"] if "channel" in s else ""
        self.model = s["model"] if "model" in s else DEFAULT_MODEL
        self.max_tokens = int(s["max_tokens"]) if "max_tokens" in s else 4096
        self.temperature = int(s["temperature"]) if "temperature" in s else 0.2
        logging.info(
            "YouTubeSummarizer: channel: %s, model: %s, max_tokens: %i, temp: %i",
            self.channel,
            self.model,
            self.max_tokens,
            self.temperature,
        )

    def process_youtube(self, id, server, channel):
        title = ""
        if self.yt_key:
            yt = youtube.YouTube(self.yt_key, id)
            title = yt.title
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(id)
        trans_str = f"ID: {id}\nTitle: {title}\n\n"
        for snippet in transcript:
            trans_str += str(snippet.start) + ": " + snippet.text
        logging.info(trans_str)
        messages = [
            {"role": "system", "content": YT_PROMPT},
            {"role": "user", "content": trans_str},
        ]
        result = gemini.get_response(
            self.key, messages, self.model, self.max_tokens, self.temperature
        )
        logging.info(result)
        self.safe_privmsg(server, channel, result)

    def on_pubmsg(self, server, user, channel, message):
        if self.channel and channel != self.channel:
            return
        if message.startswith("!gemini yt-summary"):
            for id in youtube.YouTube.find_all_ids(message):
                self._thread(self.process_youtube, id, server, channel)


if __name__ == "__main__":
    sys.exit(youtubesummarizer.run())
