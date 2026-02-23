import unittest
from unittest.mock import MagicMock, patch
from utils import gemini

class TestGemini(unittest.TestCase):
    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_get_response(self, mock_configure, mock_model_class):
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_chat = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_response = MagicMock()
        mock_response.text = "Hello, I am Gemini!"
        mock_chat.send_message.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi there!"}
        ]

        result = gemini.get_response("fake-key", messages, "gemini-1.5-flash", 256, 0.2)

        mock_configure.assert_called_once_with(api_key="fake-key")
        mock_model_class.assert_called_once_with(
            model_name="gemini-1.5-flash",
            system_instruction="You are a helpful assistant."
        )
        mock_model.start_chat.assert_called_once_with(history=[])
        mock_chat.send_message.assert_called_once()
        self.assertEqual(result, "Hello, I am Gemini!")

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_get_response_with_history(self, mock_configure, mock_model_class):
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_chat = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_response = MagicMock()
        mock_response.text = "I remember you!"
        mock_chat.send_message.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice!"},
            {"role": "user", "content": "What is my name?"}
        ]

        result = gemini.get_response("fake-key", messages, "gemini-1.5-flash", 256, 0.2)

        mock_model.start_chat.assert_called_once_with(history=[
            {"role": "user", "parts": ["My name is Alice."]},
            {"role": "model", "parts": ["Hello Alice!"]}
        ])
        mock_chat.send_message.assert_called_once_with(
            "What is my name?",
            generation_config=unittest.mock.ANY
        )
        self.assertEqual(result, "I remember you!")

if __name__ == "__main__":
    unittest.main()
