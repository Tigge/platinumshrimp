import asyncio
import irc.client_aio
import signal

import unittest
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from bot import Bot, PluginInterface


class TestBot(unittest.TestCase):
    @staticmethod
    def create_bot(mock_settings, valid=True):
        mock_settings.load_settings.return_value = {
            "nickname": "testbot",
            "realname": "Test Bot",
            "username": "testuser",
            "servers": {"test_server": {"host": "irc.test.net", "port": 6667, "ssl": False}},
            "plugins": {"test_plugin": {}},
        }
        mock_settings.validate_settings.return_value = valid

        with tempfile.TemporaryDirectory(prefix="platinumshrimp_unittest") as temp_folder:
            return Bot(temp_folder)

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)  # Detache the loop and make sure nothing else will using it

    def tearDown(self):
        self.loop.close()

    # Test that the Bot initializes without error given a valid settings.
    @patch("bot.settings")
    def test_bot_initialization(self, mock_settings):
        bot = self.create_bot(mock_settings)
        self.assertIsInstance(bot.plugins, list)
        self.assertIsInstance(bot.servers, dict)

    # Test that the Bot doesn't initialize if a bad settings is given:
    @patch("bot.settings")
    def test_bot_initialization_error(self, mock_settings):
        with self.assertRaises(SystemExit):
            bot = self.create_bot(mock_settings, False)

    # Test that the Bot.load_plugin method adds a plugin if everything is correct
    @patch("bot.settings")
    @patch("bot.PluginInterface")
    @patch("os.path.isfile", return_value=True)
    @patch("os.spawnvpe", return_value=1234)
    def test_load_plugin_work(self, mock_spawn, mock_isfile, mock_plugin_interface, mock_settings):
        bot = self.create_bot(mock_settings)
        bot.load_plugin("test", {})
        mock_plugin_interface.assert_called()
        self.assertEqual(len(bot.plugins), 1)

    # Test that the Bot.load_plugin method fails if the plugin doesn't exist
    @patch("bot.settings")
    @patch("bot.PluginInterface")
    @patch("os.path.isfile", return_value=False)
    @patch("os.spawnvpe", return_value=1234)
    def test_load_plugin_do_not_exist(
        self, mock_spawn, mock_isfile, mock_plugin_interface, mock_settings
    ):
        bot = self.create_bot(mock_settings)
        bot.load_plugin("test", {})
        mock_plugin_interface.assert_not_called()
        self.assertEqual(len(bot.plugins), 0)

    # Test the Bot.reconnect routine to ensure it tries to reconnect a few times and
    # exits cleanly when connected.
    @patch("bot.asyncio.sleep", new_callable=AsyncMock)
    @patch("bot.settings")
    def test_reconnect_loop(self, mock_settings, mock_sleep):
        connection = MagicMock()
        # Fail the first reconnect, but succeed on the second.
        connection.is_connected.side_effect = [False, False, True]
        connection.server = "irc.example.com"
        connection.port = 6667
        connection.nickname = "botnick"
        connection.password = None
        connection.username = "botuser"
        connection.ircname = "Bot IRC"
        connection.connect_factory = None
        connection.connect = AsyncMock()

        bot = self.create_bot(mock_settings)
        self.loop.run_until_complete(bot.reconnect(connection))

        self.assertEqual(connection.connect.call_count, 2)

    @patch("bot.settings")
    @patch("os.path.isfile", return_value=True)  # make sure the mock plugin is loaded
    @patch("bot.PluginInterface")
    @patch("irc.client_aio.AioReactor")
    @patch("os.spawnvpe", return_value=1234)
    @patch("os.kill")  # temporary until we have graceful shutdowns of plugins
    @patch("bot.irc.connection.AioFactory")
    def test_run(
        self,
        mock_factory,
        mock_kill,
        mock_spawnvpe,
        mock_reactor,
        mock_plugin_interface,
        mock_isfile,
        mock_settings,
    ):
        reactor_instance = MagicMock()
        mock_reactor.return_value = reactor_instance

        server_mock = AsyncMock()
        reactor_instance.server.return_value = server_mock

        plugin_interface_instance = MagicMock()
        plugin_interface_instance.pid = 666
        mock_plugin_interface.return_value = plugin_interface_instance

        bot = self.create_bot(mock_settings)
        with patch("bot.asyncio.new_event_loop", return_value=self.loop):
            with self.assertRaises(SystemExit):
                bot.run()

        mock_plugin_interface.assert_called_once()  # Make sure we loaded one pluign
        mock_kill.assert_called_with(666, signal.SIGTERM)  # Make sure the plugin was destroyed
        reactor_instance.server.assert_called_once()  # Make sure we create the server
        server_mock.connect.assert_called_once()  # Make sure we try to connect to the server
        reactor_instance.process_forever.assert_called_once()  # Make sure the reactor runs forever


class TestPluginInterface(unittest.IsolatedAsyncioTestCase):
    # Test PluginInterface initialization and ensure that plugin_started() is called
    @patch("bot.zmq.asyncio.Context")
    @patch("bot.settings")
    def test_plugin_init(self, mock_settings, mock_context):
        bot = MagicMock()
        bot.plugin_started = MagicMock()

        mock_socket = MagicMock()
        mock_context.return_value.socket.return_value = mock_socket

        plugin = PluginInterface("testplugin", bot, 123)
        mock_socket.bind.assert_called()
        bot.plugin_started.assert_called_with(plugin)
