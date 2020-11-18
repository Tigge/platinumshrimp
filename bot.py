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


class PluginInterface:
    def __init__(self, name, bot, pid):

        logging.info("PluginInterface.__init__ %s", "ipc://ipc_plugin_" + name)
        self.name = name
        self.bot = bot
        self.pid = pid
        socket_path = os.path.join(self.bot.temp_folder, "ipc_plugin_" + name)

        context = zmq.asyncio.Context()

        self._socket_plugin = context.socket(zmq.PAIR)
        self._socket_plugin.bind("ipc://" + os.path.abspath(socket_path))

        self._poller = zmq.asyncio.Poller()
        self._poller.register(self._socket_plugin, zmq.POLLIN)

        self.bot.plugin_started(self)

    def _recieve(self, data):
        logging.info("PluginInterface._recieve %s", data)
        if data["function"] == "_save_settings":
            new_plugin_settings = json.loads(data["params"][0])
            self.bot.settings["plugins"][self.name] = new_plugin_settings
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
            logging.error(
                "Undefined function %s called with %r", data["function"], data["params"]
            )

    def _call(self, function, *args):
        self._socket_plugin.send_json({"function": function, "params": args})

    async def run(self):
        while True:
            socks = dict(await self._poller.poll())

            if self._socket_plugin in socks:
                logging.info("PluginInterface.update %s", self._socket_plugin)
                self._recieve(await self._socket_plugin.recv_json())

    def __getattr__(self, name):
        if name in ["started", "update"]:

            def call(*args, **kwarg):
                self._call(name, *args)

            return call
        else:
            raise AttributeError(self, name)


class Bot:
    def __init__(self, temp_folder):
        logging.basicConfig(filename="Bot.log", level=logging.DEBUG)

        self.settings = settings.load_settings()
        if not settings.validate_settings(self.settings):
            logging.error("Error parsing settings")
            sys.exit(1)
        self.plugins = list()
        self.servers = dict()
        self.temp_folder = temp_folder

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

        for plugin in self.plugins:
            plugin._call(
                "on_" + event.type,
                connection.name,
                event.source,
                event.target,
                *event.arguments
            )

    def load_plugin(self, name, settings):
        logging.info("Bot.plugin_load %s, %s", name, settings)
        file_name = "plugins/" + name + "/" + name + ".py"
        if not os.path.isfile(file_name):
            logging.error("Unable to load plugin %s", name)
        else:
            logging.info(
                "Bot.plugin_load plugin %s, %s, %s, %s",
                name,
                self,
                sys.executable,
                [sys.executable, file_name],
            )
            environment = os.environ
            environment.update(PYTHONPATH=os.getcwd())
            pid = os.spawnvpe(
                os.P_NOWAIT,
                sys.executable,
                args=[sys.executable, file_name, "--socket_path", self.temp_folder],
                env=environment,
            )
            self.plugins.append(PluginInterface(name, self, pid))

    def plugin_started(self, plugin):
        logging.info("Bot.plugin_started %s, %s", plugin, self.settings)

        for plugin_name, plugin_settings in self.settings["plugins"].items():
            if plugin_name == plugin.name:
                plugin.started(json.dumps(plugin_settings))
                self.loop.create_task(self.plugin_update(plugin))
                self.loop.create_task(plugin.run())
                # self.reactor.scheduler.execute_every(1.0, plugin.update)
                logging.debug("Bot.plugin_started, settings %r", plugin_settings)
                break

    async def plugin_update(self, plugin):
        while True:
            plugin.update()
            await asyncio.sleep(1)

    def run(self):

        self.loop = asyncio.get_event_loop()
        self.reactor = irc.client_aio.AioReactor(loop=self.loop)
        self.reactor.add_global_handler("all_events", self._dispatcher, -10)

        # Load plugins
        if "plugins" in self.settings:
            for plugin_name, plugin_settings in self.settings["plugins"].items():
                self.load_plugin(plugin_name, plugin_settings)

        # Connect to servers
        servers = self.settings["servers"]
        for server_name, server_settings in servers.items():
            logging.info("Connecting to %r %r", server_name, server_settings)
            server = self.reactor.server()
            self.servers[server_name] = server
            server.name = server_name
            server.buffer_class = jaraco.stream.buffer.LenientDecodingLineBuffer
            use_ssl = "ssl" in server_settings and server_settings["ssl"]
            factory = irc.connection.AioFactory(ssl=use_ssl)
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

        try:
            self.reactor.process_forever()
        except:
            logging.exception("Bot.run aborted")

        # Request termination of plugins
        for plugin in self.plugins:
            os.kill(plugin.pid, signal.SIGTERM)

        self.loop.close()
        sys.exit(1)


def main():
    with tempfile.TemporaryDirectory(prefix="platinumshrimp_") as temp_folder:
        bot = Bot(temp_folder)
        bot.run()


if __name__ == "__main__":
    main()
