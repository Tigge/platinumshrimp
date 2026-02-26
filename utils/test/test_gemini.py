import unittest
from unittest.mock import MagicMock, patch
from utils import gemini
from google.genai import types


class TestGemini(unittest.TestCase):
    @patch("google.genai.Client")
    def test_get_response(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "Hello, I am Gemini!"
        mock_client.models.generate_content.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi there!"},
        ]

        result = gemini.get_response("fake-key", messages, "gemini-1.5-flash", 256, 0.2)

        mock_client_class.assert_called_once_with(api_key="fake-key")
        mock_client.models.generate_content.assert_called_once()
        args, kwargs = mock_client.models.generate_content.call_args
        self.assertEqual(kwargs["model"], "gemini-1.5-flash")
        self.assertEqual(kwargs["config"].system_instruction, "You are a helpful assistant.")
        self.assertEqual(kwargs["config"].max_output_tokens, 256)
        self.assertEqual(kwargs["config"].temperature, 0.2)
        self.assertEqual(result, "Hello, I am Gemini!")

    @patch("google.genai.Client")
    def test_get_response_with_history(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "I remember you!"
        mock_client.models.generate_content.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice!"},
            {"role": "user", "content": "What is my name?"},
        ]

        result = gemini.get_response("fake-key", messages, "gemini-1.5-flash", 256, 0.2)

        mock_client.models.generate_content.assert_called_once()
        args, kwargs = mock_client.models.generate_content.call_args

        contents = kwargs["contents"]
        self.assertEqual(len(contents), 3)
        self.assertEqual(contents[0].role, "user")
        self.assertEqual(contents[0].parts[0].text, "My name is Alice.")
        self.assertEqual(contents[1].role, "model")
        self.assertEqual(contents[1].parts[0].text, "Hello Alice!")
        self.assertEqual(contents[2].role, "user")
        self.assertEqual(contents[2].parts[0].text, "What is my name?")

        self.assertEqual(result, "I remember you!")


if __name__ == "__main__":
    unittest.main()
