import asyncio
import irc.client
import irc.client_aio
import signal
import os
import socket
import time

import unittest
import tempfile
from threading import Thread
from unittest.mock import MagicMock, patch, AsyncMock, call
from bot import Bot, PluginInterface
from command_line import CommandLine


class TestBot(unittest.TestCase):
    @staticmethod
    def create_bot(mock_settings, valid=True):
        mock_settings.load_settings.return_value = {
            "nickname": "testbot",
            "realname": "Test Bot",
            "username": "testuser",
            "servers": {"test_server": {"host": "irc.test.net", "port": 6667, "ssl": False}},
            "plugins": {"test_plugin": {}},
            "plugin_watchdog": {"timeout_seconds": 30, "max_restarts": 3},
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
        with self.assertLogs("root"):
            with self.assertRaises(SystemExit):
                bot = self.create_bot(mock_settings, False)

    @patch("bot.settings")
    def test_dispatch_sent_from_cli_thread_propagates_channel_message(self, mock_settings):
        bot = self.create_bot(mock_settings)
        bot.loop = self.loop
        plugin = MagicMock()
        bot.plugins.append(plugin)

        thread = Thread(
            target=bot._dispatch_sent, args=("test_server", "privmsg", "#spam", "Test!")
        )
        thread.start()
        thread.join()
        self.loop.run_until_complete(asyncio.sleep(0))

        plugin._call.assert_called_once_with(
            "on_me_pubmsg", "test_server", "testbot", "#spam", "Test!"
        )

    @patch("bot.settings")
    def test_command_line_send_message_sends_to_server(self, mock_settings):
        bot = self.create_bot(mock_settings)
        server = MagicMock()
        bot.servers["test_server"] = server

        CommandLine(bot).do_send_message("test_server #spam Test!")

        server.privmsg.assert_called_once_with("#spam", "Test!")

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
        with self.assertLogs("root"):
            bot.load_plugin("test", {})
        mock_plugin_interface.assert_not_called()
        self.assertEqual(len(bot.plugins), 0)

    @patch("bot.settings")
    def test_check_plugin_health_keeps_healthy_plugin(self, mock_settings):
        bot = self.create_bot(mock_settings)
        plugin = MagicMock()
        plugin._shutdown_requested = False
        plugin.process_exited = False
        plugin.last_heartbeat = time.monotonic()
        plugin.poll_process.return_value = None
        bot.plugins.append(plugin)
        bot._restart_plugin = AsyncMock()

        self.loop.run_until_complete(bot.check_plugin_health())

        bot._restart_plugin.assert_not_awaited()

    @patch("bot.settings")
    def test_check_plugin_health_restarts_plugin_after_heartbeat_timeout(self, mock_settings):
        bot = self.create_bot(mock_settings)
        bot.plugin_heartbeat_timeout = 5
        plugin = MagicMock()
        plugin.name = "test_plugin"
        plugin._shutdown_requested = False
        plugin.process_exited = False
        plugin.last_heartbeat = 10
        plugin.poll_process.return_value = None
        bot.plugins.append(plugin)
        bot._restart_plugin = AsyncMock()

        with patch("bot.time.monotonic", return_value=20):
            self.loop.run_until_complete(bot.check_plugin_health())

        bot._restart_plugin.assert_awaited_once_with(plugin, "heartbeat timeout")

    @patch("bot.settings")
    def test_check_plugin_health_restarts_exited_process(self, mock_settings):
        bot = self.create_bot(mock_settings)
        plugin = MagicMock()
        plugin.name = "test_plugin"
        plugin._shutdown_requested = False
        plugin.process_exited = True
        plugin.poll_process.return_value = 256
        bot.plugins.append(plugin)
        bot._restart_plugin = AsyncMock()

        self.loop.run_until_complete(bot.check_plugin_health())

        bot._restart_plugin.assert_awaited_once_with(plugin, "process exited with status 1")

    @patch("bot.settings")
    def test_restart_plugin_stops_after_configured_restart_limit(self, mock_settings):
        bot = self.create_bot(mock_settings)
        plugin = MagicMock()
        plugin.name = "test_plugin"
        plugin._shutdown_requested = False
        plugin.process_exited = True
        plugin.shutdown_plugin = AsyncMock()
        bot.plugins.append(plugin)
        bot.plugin_restart_counts[plugin.name] = bot.plugin_max_restarts
        bot._start_plugin = MagicMock()

        with self.assertLogs("root", level="ERROR"):
            self.loop.run_until_complete(bot._restart_plugin(plugin, "heartbeat timeout"))

        plugin.shutdown_plugin.assert_awaited_once()
        bot._start_plugin.assert_not_called()
        self.assertNotIn(plugin, bot.plugins)
        self.assertEqual(bot.unhealthy_plugins[plugin.name], "heartbeat timeout")

    @patch("bot.settings")
    def test_restart_plugin_restarts_and_tracks_attempt(self, mock_settings):
        bot = self.create_bot(mock_settings)
        plugin = MagicMock()
        plugin.name = "test_plugin"
        plugin._shutdown_requested = False
        plugin.process_exited = True
        plugin.shutdown_plugin = AsyncMock()
        bot.plugins.append(plugin)
        bot._start_plugin = MagicMock(return_value=True)

        with self.assertLogs("root", level="WARNING"):
            self.loop.run_until_complete(bot._restart_plugin(plugin, "process exited"))

        plugin.shutdown_plugin.assert_awaited_once()
        self.assertEqual(bot.plugin_restart_counts[plugin.name], 1)
        bot._start_plugin.assert_called_once_with(plugin.name)

    @patch("bot.asyncio.sleep", new_callable=AsyncMock)
    @patch("bot.settings")
    def test_reconnect_retries_with_backoff_and_restores_channels(self, mock_settings, mock_sleep):
        connection = MagicMock()
        connection.is_connected.return_value = False
        connection.server = "irc.example.com"
        connection.port = 6667
        connection.nickname = "botnick"
        connection.password = None
        connection.username = "botuser"
        connection.ircname = "Bot IRC"
        connection.connect_factory = None
        connection.name = "test_server"
        connection.channels = {"#one", "#two"}

        async def connect(*args, **kwargs):
            if connection.connect.await_count == 3:
                connection.is_connected.return_value = True
            else:
                raise OSError("network unavailable")

        connection.connect = AsyncMock(side_effect=connect)

        bot = self.create_bot(mock_settings)
        with self.assertLogs("root", level="WARNING"):
            self.loop.run_until_complete(bot.reconnect(connection))

        self.assertEqual(connection.connect.await_count, 3)
        self.assertEqual(mock_sleep.await_args_list, [call(5), call(10)])
        self.assertEqual(connection.join.call_args_list, [call("#one"), call("#two")])

    @patch("bot.asyncio.sleep", new_callable=AsyncMock)
    @patch("bot.settings")
    def test_reconnect_stops_after_configured_retry_limit(self, mock_settings, mock_sleep):
        connection = MagicMock()
        connection.is_connected.return_value = False
        connection.server = "irc.example.com"
        connection.name = "test_server"
        connection.channels = set()
        connection.connect = AsyncMock(side_effect=OSError("network unavailable"))

        bot = self.create_bot(mock_settings)
        bot.reconnect_max_retries = 2
        with self.assertLogs("root", level="ERROR") as logs:
            self.loop.run_until_complete(bot.reconnect(connection))

        self.assertEqual(connection.connect.await_count, 3)
        self.assertEqual(mock_sleep.await_args_list, [call(5), call(10)])
        self.assertIn("after 3 attempts (2 retries)", logs.output[-1])

    @patch("bot.settings")
    def test_enable_tcp_keepalive_configures_socket_probes(self, mock_settings):
        bot = self.create_bot(mock_settings)
        connection = MagicMock()
        transport_socket = MagicMock()
        connection.transport.get_extra_info.return_value = transport_socket

        bot._enable_tcp_keepalive(connection)

        expected_options = [
            call(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
            call(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60),
            call(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10),
            call(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3),
        ]
        transport_socket.setsockopt.assert_has_calls(expected_options)

    @patch("bot.settings")
    def test_quit_event_does_not_clear_channel_state(self, mock_settings):
        bot = self.create_bot(mock_settings)
        connection = MagicMock()
        connection.nickname = "testbot"
        connection.channels = {"#one"}
        event = MagicMock()
        event.type = "quit"

        bot._dispatcher(connection, event)

        self.assertEqual(connection.channels, {"#one"})

    @patch("bot.settings")
    @patch("os.path.isfile", return_value=True)  # make sure the mock plugin is loaded
    @patch("bot.PluginInterface")
    @patch("irc.client_aio.AioReactor")
    @patch("os.spawnvpe", return_value=1234)
    @patch("bot.irc.connection.AioFactory")
    @patch("bot.CommandLine")
    def test_run(
        self,
        mock_command_line,
        mock_factory,
        mock_spawnvpe,
        mock_reactor,
        mock_plugin_interface,
        mock_isfile,
        mock_settings,
    ):
        reactor_instance = MagicMock()
        mock_reactor.return_value = reactor_instance

        server_mock = AsyncMock()
        server_mock.transport = MagicMock()
        server_mock.transport.get_extra_info.return_value = MagicMock()
        reactor_instance.server.return_value = server_mock

        plugin_interface_instance = MagicMock()
        plugin_interface_instance.pid = 666
        plugin_interface_instance.name = "test_plugin"
        plugin_interface_instance.shutdown_plugin = AsyncMock()
        mock_plugin_interface.return_value = plugin_interface_instance

        bot = self.create_bot(mock_settings)
        with patch("bot.asyncio.new_event_loop", return_value=self.loop):
            with self.assertRaises(SystemExit):
                bot.run()

        mock_plugin_interface.assert_called_once()  # Make sure we loaded one pluign
        plugin_interface_instance.shutdown_plugin.assert_called_once()  # Make sure the plugin was gracefully shut down
        reactor_instance.server.assert_called_once()  # Make sure we create the server
        server_mock.connect.assert_called_once()  # Make sure we try to connect to the server
        reactor_instance.process_forever.assert_called_once()  # Make sure the reactor runs forever


class TestPluginInterface(unittest.IsolatedAsyncioTestCase):
    def test_disconnected_server_does_not_stop_plugin_message_handling(self):
        interface = PluginInterface.__new__(PluginInterface)
        server = MagicMock()
        server.privmsg.side_effect = irc.client.ServerNotConnectedError("Not connected.")
        interface.bot = MagicMock()
        interface.bot.servers = {"test_server": server}

        with self.assertLogs("root", level="ERROR"):
            interface._recieve(
                {
                    "function": "privmsg",
                    "params": ("test_server", "#channel", "message"),
                }
            )

        server.privmsg.assert_called_once_with("#channel", "message")

    # Test PluginInterface initialization and ensure that plugin_started() is called
    @patch("bot.zmq.asyncio.Context.instance")
    @patch("bot.settings")
    def test_plugin_init(self, mock_settings, mock_instance):
        bot = MagicMock()
        bot.plugin_started = MagicMock()

        mock_socket = MagicMock()
        mock_instance.return_value.socket.return_value = mock_socket

        plugin = PluginInterface("testplugin", bot, 123)
        mock_socket.bind.assert_called()
        bot.plugin_started.assert_called_with(plugin)

    @patch("bot.zmq.asyncio.Context")
    @patch("bot.settings")
    @patch("bot.os.waitpid")
    @patch("bot.os.kill")
    @patch("bot.asyncio.sleep", new_callable=AsyncMock)
    async def test_shutdown_plugin_clean(
        self, mock_sleep, mock_kill, mock_waitpid, mock_settings, mock_context
    ):
        bot = MagicMock()
        mock_socket = MagicMock()
        mock_context.return_value.socket.return_value = mock_socket

        plugin = PluginInterface("testplugin", bot, 123)
        # Mocking the _call method to avoid sending real zmq messages
        plugin._call = MagicMock()

        # Simulate process exiting cleanly
        mock_waitpid.side_effect = [(0, 0), (123, 0)]

        await plugin.shutdown_plugin()

        plugin._call.assert_called_with("shutdown")
        mock_waitpid.assert_called_with(123, os.WNOHANG)
        mock_kill.assert_not_called()

    @patch("bot.zmq.asyncio.Context")
    @patch("bot.settings")
    @patch("bot.os.waitpid")
    @patch("bot.os.kill")
    @patch("bot.asyncio.sleep", new_callable=AsyncMock)
    async def test_shutdown_plugin_timeout(
        self, mock_sleep, mock_kill, mock_waitpid, mock_settings, mock_context
    ):
        bot = MagicMock()
        mock_socket = MagicMock()
        mock_context.return_value.socket.return_value = mock_socket

        plugin = PluginInterface("testplugin", bot, 123)
        plugin._call = MagicMock()

        # Simulate process not exiting
        mock_waitpid.return_value = (0, 0)

        with self.assertLogs("root", level="ERROR"), patch("sys.stderr"):
            await plugin.shutdown_plugin()

        plugin._call.assert_called_with("shutdown")
        self.assertEqual(mock_waitpid.call_count, 16)
        mock_kill.assert_has_calls([call(123, signal.SIGTERM), call(123, signal.SIGKILL)])

    @patch("bot.zmq.asyncio.Context.instance")
    @patch("bot.settings")
    def test_heartbeat_updates_plugin_health(self, mock_settings, mock_instance):
        bot = MagicMock()
        bot.plugin_started = MagicMock()
        mock_instance.return_value.socket.return_value = MagicMock()
        plugin = PluginInterface("testplugin", bot, 123)

        with patch("bot.time.monotonic", return_value=42):
            plugin._recieve({"function": "_heartbeat", "params": []})

        self.assertEqual(plugin.last_heartbeat, 42)
        self.assertEqual(plugin.state, "running")

    @patch("bot.os.waitpid", return_value=(123, 256))
    @patch("bot.zmq.asyncio.Context.instance")
    @patch("bot.settings")
    def test_poll_process_records_child_exit(self, mock_settings, mock_instance, mock_waitpid):
        bot = MagicMock()
        bot.plugin_started = MagicMock()
        mock_instance.return_value.socket.return_value = MagicMock()
        plugin = PluginInterface("testplugin", bot, 123)

        self.assertEqual(plugin.poll_process(), 256)
        self.assertTrue(plugin.process_exited)
        self.assertEqual(plugin.exit_status, 256)
        mock_waitpid.assert_called_once_with(123, os.WNOHANG)
