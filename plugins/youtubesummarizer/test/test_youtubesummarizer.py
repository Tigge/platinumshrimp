import unittest
from unittest.mock import MagicMock, patch

from plugins.youtubesummarizer.youtubesummarizer import youtubesummarizer
from utils.youtube import VideoNotFoundError


class YouTubeSummarizerTestCase(unittest.TestCase):
    def test_process_youtube_continues_without_video_details(self):
        summarizer = youtubesummarizer.__new__(youtubesummarizer)
        summarizer.yt_key = "api-key"
        summarizer.key = "gemini-key"
        summarizer.model = "model"
        summarizer.max_tokens = 100
        summarizer.temperature = 0.2
        summarizer.safe_privmsg = MagicMock()

        with patch(
            "plugins.youtubesummarizer.youtubesummarizer.youtube.YouTube",
            side_effect=VideoNotFoundError("No video details"),
        ):
            with patch(
                "plugins.youtubesummarizer.youtubesummarizer.YouTubeTranscriptApi"
            ) as transcript_api:
                transcript_api.return_value.fetch.return_value = []
                with patch(
                    "plugins.youtubesummarizer.youtubesummarizer.gemini.get_response",
                    return_value="summary",
                ):
                    summarizer.process_youtube("video-id", "server", "#channel")

        summarizer.safe_privmsg.assert_called_once_with("server", "#channel", "summary")
