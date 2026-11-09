import unittest
from unittest.mock import Mock, patch

from utils.youtube import VideoNotFoundError, YouTube


class YouTubeTestCase(unittest.TestCase):
    @patch("utils.youtube.requests.get")
    def test_empty_items_raises_video_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        with self.assertRaises(VideoNotFoundError):
            YouTube("api-key", "video-id")

    @patch("utils.youtube.requests.get")
    def test_missing_items_raises_video_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        with self.assertRaises(VideoNotFoundError):
            YouTube("api-key", "video-id")
