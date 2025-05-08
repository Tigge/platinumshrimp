import unittest
import threading
import asyncio
from unittest.mock import MagicMock, patch, call

from plugin import Plugin


# Dummy subclass to test Plugin behavior
class DummyPlugin(Plugin):
    def __init__(self):
        self.name = "dummy"
        self._call = MagicMock()
        self.privmsg = MagicMock()
        self.threading_data = threading.local()
        self.threading_data.call_socket = MagicMock()


class TestPlugin(unittest.TestCase):

    def setUp(self):
        self.plugin = DummyPlugin()

    # Test that calling a valid IRC command will invoke _call with correct arguments
    def test_irc_command_proxy_calls_call(self):
        self.plugin.action("server", "#channel", "foo bar action")
        self.plugin._call.assert_called_once_with("action", "server", "#channel", "foo bar action")

    # Test that _recieve calls the corresponding method with the given parameters
    def test_receive_calls_existing_method(self):
        self.plugin.on_message = MagicMock()
        self.plugin._recieve({"function": "on_message", "params": ["srv", "#chan", "hi"]})
        self.plugin.on_message.assert_called_once_with("srv", "#chan", "hi")

    # Test that_recieve doesn't fail or give error on function names not implemented by the plugin
    def test_receive_ignores_missing_method(self):
        self.plugin._recieve({"function": "on_fake_event", "params": []})

    # Test that safe_privmsg will unescape, wrap, and send each line using privmsg
    @patch("plugin.textwrap.wrap", return_value=["line1", "line2"])
    @patch("plugin.str_utils.unescape_entities", return_value="msg1\nmsg2")
    def test_safe_privmsg_sends_wrapped_lines(self, mock_unescape, mock_wrap):
        self.plugin.safe_privmsg("server", "#chan", "Test &amp; msg")
        self.plugin.privmsg.assert_has_calls(
            [
                call("server", "#chan", "line1"),
                call("server", "#chan", "line2"),
                call("server", "#chan", "line1"),
                call("server", "#chan", "line2"),
            ]
        )

    # Test that _run calls the corresponding method on plugin when data is available on _socket
    def test_run_receives_data_from_sockets(self):
        async def run_once():
            self.plugin._poller = MagicMock()
            self.plugin._socket_bot = MagicMock()
            self.plugin._socket_workers = MagicMock()
            self.plugin.on_message = MagicMock()

            # First poll returns a socket with data, second poll is an empty future
            first_future = asyncio.Future()
            first_future.set_result({self.plugin._socket_bot: True})
            self.plugin._poller.poll = MagicMock(side_effect=[first_future, asyncio.Future()])

            # Simulate receiving JSON data from socket
            self.plugin._socket_bot.recv_json = MagicMock(return_value=asyncio.Future())
            self.plugin._socket_bot.recv_json.return_value.set_result(
                {"function": "on_message", "params": ["test_param"]}
            )
            self.plugin._socket_workers.recv = MagicMock(return_value=asyncio.Future())

            # Call _run() in a task so that we can cancel it after a short delay
            task = asyncio.create_task(self.plugin._run())
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_once())
        self.plugin.on_message.assert_called_once_with("test_param")
