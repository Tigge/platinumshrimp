import asyncio
import ssl
import sys
import signal
import os
import json
import time
import logging
import tempfile
from utils import settings

import zmq
import zmq.asyncio
import irc.client_aio
import jaraco.stream

from command_line import CommandLine


class PluginInterface:
    """
    Interface for a plugin. This class runs in the main bot process and
    communicates with the plugin process over IPC.
    """

    def __init__(self, name, bot, pid):

        logging.info("PluginInterface.__init__ %s", "ipc://ipc_plugin_" + name)
        self.name = name
        self.bot = bot
        self.pid = pid
        self.started_at = time.monotonic()
        self.last_heartbeat = self.started_at
        self.state = "starting"
        self.failure_reason = None
        self.process_exited = False
        self.exit_status = None
        self.run_task = None
        self.update_task = None
        self._shutdown_requested = False
        socket_path = os.path.join(self.bot.temp_folder, "ipc_plugin_" + name)

        self._context = zmq.asyncio.Context.instance()

        self._socket_plugin = self._context.socket(zmq.PAIR)
        self._socket_plugin.bind("ipc://" + os.path.abspath(socket_path))

        self._poller = zmq.asyncio.Poller()
        self._poller.register(self._socket_plugin, zmq.POLLIN)

        self.bot.plugin_started(self)

    def __del__(self):
        if hasattr(self, "_socket_plugin"):
            self._socket_plugin.close()

    def _recieve(self, data):
        logging.info("PluginInterface._recieve %s", data)
        if data["function"] == "_heartbeat":
            self.last_heartbeat = time.monotonic()
            self.state = "running"
            return

        if data["function"] == "_save_settings":
            new_plugin_settings = json.loads(data["params"][0])
            self.bot.settings["plugins"][self.name] = new_plugin_settings
            self.bot.plugin_configs[self.name] = new_plugin_settings
            settings.save_settings(self.bot.settings)
            return

        server = data["params"][0]
        if server not in self.bot.servers:
            logging.error("PluginInterface._recieve %s not found", server)
            return

        if data["function"] in [
            "action",
            "admin",
            "cap",
            "ctcp",
            "ctcp_reply",
            "globops",
            "info",
            "invite",
            "ison",
            "join",
            "kick",
            "links",
            "list",
            "lusers",
            "mode",
            "motd",
            "names",
            "nick",
            "notice",
            "oper",
            "part",
            "pass_",
            "ping",
            "pong",
            "privmsg",
            "quit",
            "squit",
            "stats",
            "time",
            "topic",
            "trace",
            "user",
            "userhost",
            "users",
            "version",
            "wallops",
            "who",
            "whois",
            "whowas",
        ]:
            try:
                getattr(self.bot.servers[server], data["function"])(*data["params"][1:])
            except (irc.client.InvalidCharacters, irc.client.MessageTooLong):
                logging.exception("Failed to call function from plugin %r", data)
        else:
            logging.error("Undefined function %s called with %r", data["function"], data["params"])

    def _call(self, function, *args):
        self._socket_plugin.send_json({"function": function, "params": args})

    async def run(self):
        while True:
            socks = dict(await self._poller.poll())

            if self._socket_plugin in socks:
                logging.info("PluginInterface.update %s", self._socket_plugin)
                self._recieve(await self._socket_plugin.recv_json())

    def __getattr__(self, name):
        if name in ["started", "update", "shutdown", "_heartbeat"]:

            def call(*args, **kwarg):
                self._call(name, *args)

            return call
        else:
            raise AttributeError(self, name)

    def poll_process(self):
        if self.process_exited:
            return self.exit_status

        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            self.process_exited = True
            return self.exit_status

        if pid:
            self.process_exited = True
            self.exit_status = status
            return status
        return None

    async def _wait_for_exit(self):
        for _ in range(5):
            await asyncio.sleep(0.1)
            self.poll_process()
            if self.process_exited:
                return True
        return False

    async def shutdown_plugin(self):
        self._shutdown_requested = True
        if not self.process_exited:
            self.poll_process()
        if not self.process_exited:
            try:
                self.shutdown()
            except zmq.ZMQError:
                logging.exception("Unable to request shutdown from plugin %s", self.name)
            if not await self._wait_for_exit():
                logging.error("Plugin %s did not shut down cleanly, sending SIGTERM", self.name)
                print(
                    f"Error: Plugin {self.name} did not shut down cleanly, sending SIGTERM",
                    file=sys.stderr,
                )
                try:
                    os.kill(self.pid, signal.SIGTERM)
                except ProcessLookupError:
                    self.process_exited = True

                if not self.process_exited and not await self._wait_for_exit():
                    logging.error("Plugin %s ignored SIGTERM, sending SIGKILL", self.name)
                    try:
                        os.kill(self.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        self.process_exited = True
                    if not self.process_exited:
                        await self._wait_for_exit()

        tasks = [task for task in (self.run_task, self.update_task) if task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._socket_plugin.close(linger=0)


class Bot:
    def __init__(self, temp_folder):
        logging.basicConfig(
            filename="Bot.log",
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        self.settings = settings.load_settings()
        if not settings.validate_settings(self.settings):
            logging.error("Error parsing settings")
            sys.exit(1)
        self.plugins = list()
        self.servers = dict()
        self.temp_folder = temp_folder
        watchdog_settings = self.settings.get("plugin_watchdog", {})
        self.plugin_heartbeat_timeout = watchdog_settings.get(
            "timeout_seconds", settings.DEFAULT_PLUGIN_WATCHDOG["timeout_seconds"]
        )
        self.plugin_max_restarts = watchdog_settings.get(
            "max_restarts", settings.DEFAULT_PLUGIN_WATCHDOG["max_restarts"]
        )
        self.plugin_restart_counts = {}
        self.unhealthy_plugins = {}
        self.plugin_configs = dict(self.settings.get("plugins", {}))
        self.watchdog_task = None
        self.shutting_down = False

    async def unload_plugin(self, name):
        plugin = next((p for p in self.plugins if p.name == name), None)
        if plugin:
            await plugin.shutdown_plugin()
            self.plugins.remove(plugin)
            return True
        return self.unhealthy_plugins.pop(name, None) is not None

    async def reconnect(self, connection):
        while not connection.is_connected():
            logging.error("Waiting 30 seconds to reconnect")
            await asyncio.sleep(30)
            await connection.connect(
                connection.server,
                connection.port,
                connection.nickname,
                password=connection.password,
                username=connection.username,
                ircname=connection.ircname,
                connect_factory=connection.connect_factory,
            )

    def _dispatcher(self, connection, event):
        if event.type == "all_raw_messages":
            return

        if event.type == "disconnect":
            asyncio.create_task(self.reconnect(connection))

        # Track currently active channels
        if event.type == "join" and event.source.nick == connection.nickname:
            connection.channels.add(event.target)
        elif event.type == "part" and event.source.nick == connection.nickname:
            connection.channels.discard(event.target)
        elif event.type == "kick" and event.arguments[0] == connection.nickname:
            connection.channels.discard(event.target)
        elif event.type == "quit":
            # Technically not needed but on quit, clear all channels
            connection.channels.clear()

        for plugin in self.plugins:
            plugin._call(
                "on_" + event.type, connection.name, event.source, event.target, *event.arguments
            )

    def _dispatch_sent(self, connection_name, type, target, message):
        source = self.settings["nickname"]
        event_type = type
        if type == "privmsg" and target and target[0] in "&#+!":
            event_type = "pubmsg"

        for plugin in self.plugins:
            plugin._call("on_me_" + event_type, connection_name, source, target, message)

    def load_plugin(self, name, settings):
        self.plugin_configs[name] = settings
        self.plugin_restart_counts.pop(name, None)
        self.unhealthy_plugins.pop(name, None)
        if not self._start_plugin(name):
            self.unhealthy_plugins[name] = "failed to start plugin process"

    def _start_plugin(self, name):
        logging.info("Bot.plugin_load %s, %s", name, self.plugin_configs.get(name, {}))
        file_name = "plugins/" + name + "/" + name + ".py"
        if not os.path.isfile(file_name):
            logging.error("Unable to load plugin %s", name)
            return False

        logging.info(
            "Bot.plugin_load plugin %s, %s, %s, %s",
            name,
            self,
            sys.executable,
            [sys.executable, file_name],
        )
        environment = os.environ.copy()
        environment.update(PYTHONPATH=os.getcwd())
        try:
            pid = os.spawnvpe(
                os.P_NOWAIT,
                sys.executable,
                args=[sys.executable, file_name, "--socket_path", self.temp_folder],
                env=environment,
            )
        except OSError:
            logging.exception("Unable to start plugin %s", name)
            return False
        self.plugins.append(PluginInterface(name, self, pid))
        return True

    def plugin_started(self, plugin):
        logging.info("Bot.plugin_started %s, %s", plugin, self.settings)

        for plugin_name, plugin_settings in self.settings["plugins"].items():
            if plugin_name == plugin.name:
                plugin.started(json.dumps(plugin_settings))
                plugin.update_task = self.loop.create_task(self.plugin_update(plugin))
                plugin.run_task = self.loop.create_task(plugin.run())
                # self.reactor.scheduler.execute_every(1.0, plugin.update)
                logging.debug("Bot.plugin_started, settings %r", plugin_settings)
                break

    async def plugin_update(self, plugin):
        while True:
            plugin.update()
            await asyncio.sleep(1)

    async def check_plugin_health(self):
        for plugin in list(self.plugins):
            if plugin._shutdown_requested:
                continue

            exit_status = plugin.poll_process()
            if plugin.process_exited:
                exit_code = (
                    os.waitstatus_to_exitcode(exit_status) if exit_status is not None else "unknown"
                )
                await self._restart_plugin(plugin, f"process exited with status {exit_code}")
            elif time.monotonic() - plugin.last_heartbeat > self.plugin_heartbeat_timeout:
                await self._restart_plugin(plugin, "heartbeat timeout")

    async def plugin_watchdog(self):
        while not self.shutting_down:
            await asyncio.sleep(1)
            await self.check_plugin_health()

    async def _restart_plugin(self, plugin, reason):
        if plugin not in self.plugins or plugin._shutdown_requested:
            return

        restart_count = self.plugin_restart_counts.get(plugin.name, 0)
        if restart_count >= self.plugin_max_restarts:
            logging.error(
                "Plugin %s is unhealthy after %s automatic restart attempts: %s",
                plugin.name,
                restart_count,
                reason,
            )
            await plugin.shutdown_plugin()
            self.plugins.remove(plugin)
            plugin.state = "unhealthy"
            plugin.failure_reason = reason
            self.unhealthy_plugins[plugin.name] = reason
            return

        restart_count += 1
        self.plugin_restart_counts[plugin.name] = restart_count
        logging.warning(
            "Restarting plugin %s (attempt %s/%s): %s",
            plugin.name,
            restart_count,
            self.plugin_max_restarts,
            reason,
        )
        plugin_name = plugin.name
        plugin.state = "restarting"
        await plugin.shutdown_plugin()
        self.plugins.remove(plugin)
        if not plugin.process_exited:
            reason = "unable to stop plugin process"
            logging.error("Plugin %s is unhealthy: %s", plugin_name, reason)
            plugin.state = "unhealthy"
            plugin.failure_reason = reason
            self.unhealthy_plugins[plugin_name] = reason
            return
        if not self._start_plugin(plugin_name):
            reason = "failed to spawn plugin process"
            self.unhealthy_plugins[plugin_name] = reason

    def run(self):

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.reactor = irc.client_aio.AioReactor(loop=self.loop)
        self.reactor.add_global_handler("all_events", self._dispatcher, -10)

        # Load plugins
        async def load_plugins():
            if "plugins" in self.settings:
                for plugin_name, plugin_settings in self.settings["plugins"].items():
                    self.load_plugin(plugin_name, plugin_settings)

        self.loop.run_until_complete(load_plugins())
        self.watchdog_task = self.loop.create_task(self.plugin_watchdog())

        # Connect to servers
        servers = self.settings["servers"]
        for server_name, server_settings in servers.items():
            logging.info("Connecting to %r %r", server_name, server_settings)
            server = self.reactor.server()
            self.servers[server_name] = server
            server.channels = set()
            server.name = server_name

            # Monkey-patch to track outgoing messages
            def patch(obj, func_name, event_type):
                orig = getattr(obj, func_name)

                def wrapped(target, message):
                    orig(target, message)
                    self._dispatch_sent(server_name, event_type, target, message)

                setattr(obj, func_name, wrapped)

            patch(server, "privmsg", "privmsg")
            patch(server, "notice", "notice")
            if hasattr(server, "action"):
                patch(server, "action", "action")

            server.buffer_class = jaraco.stream.buffer.LenientDecodingLineBuffer
            use_ssl = "ssl" in server_settings and server_settings["ssl"]
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            factory = irc.connection.AioFactory(ssl=ssl_context if use_ssl else None)
            self.loop.run_until_complete(
                server.connect(
                    server_settings["host"],
                    server_settings["port"],
                    nickname=self.settings["nickname"],
                    ircname=self.settings["realname"],
                    username=self.settings["username"],
                    connect_factory=factory,
                )
            )

        command_line = CommandLine(self)
        command_line.start()

        try:
            self.reactor.process_forever()
        except:
            logging.exception("Bot.run aborted")

        # Request termination of plugins
        self.shutting_down = True
        if self.watchdog_task is not None:
            self.watchdog_task.cancel()
            self.loop.run_until_complete(asyncio.gather(self.watchdog_task, return_exceptions=True))

        async def unload_all_plugins():
            tasks = [self.unload_plugin(plugin.name) for plugin in list(self.plugins)]
            await asyncio.gather(*tasks, return_exceptions=True)

        self.loop.run_until_complete(unload_all_plugins())

        self.loop.close()
        command_line.wait_until_done()
        sys.exit(1)


def main():
    with tempfile.TemporaryDirectory(prefix="platinumshrimp_") as temp_folder:
        bot = Bot(temp_folder)
        bot.run()


if __name__ == "__main__":
    main()
