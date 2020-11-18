import ssl
import sys
import os
import json
import time
import logging
import tempfile
from utils import settings

import zmq
import irc.client
import jaraco.stream


class PluginInterface:
    def __init__(self, name, bot):

        logging.info("PluginInterface.__init__ %s", "ipc://ipc_plugin_" + name)
        self.name = name
        self.bot = bot
        socket_path = os.path.join(self.bot.temp_folder, "ipc_plugin_" + name)

        context = zmq.Context()

        self._socket_plugin = context.socket(zmq.PAIR)
        self._socket_plugin.bind("ipc://" + os.path.abspath(socket_path))

        self._poller = zmq.Poller()
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

    def process_once(self, timeout=0):
        try:
            socks = dict(self._poller.poll(timeout=timeout))
        except KeyboardInterrupt:
            return

        if self._socket_plugin in socks:
            logging.info("PluginInterface.update %s", self._socket_plugin)
            self._recieve(self._socket_plugin.recv_json())

    def __getattr__(self, name):
        logging.info("PluginInterface.__getattr__ %s", name)
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

        self.reactor = irc.client.Reactor()
        self.reactor.add_global_handler("all_events", self._dispatcher, -10)

        # Load plugins
        if "plugins" in self.settings:
            for plugin_name, plugin_settings in self.settings["plugins"].items():
                self.load_plugin(plugin_name, plugin_settings)

        # Connect to servers
        servers = self.settings["servers"]
        for server_name, server_settings in servers.items():
            logging.info("Connecting to %r %r", server_name, server_settings)
            s = self.reactor.server()
            self.servers[server_name] = s
            s.name = server_name
            s.buffer_class = jaraco.stream.buffer.LenientDecodingLineBuffer
            use_ssl = "ssl" in server_settings and server_settings["ssl"]
            factory = (
                irc.connection.Factory(wrapper=ssl.wrap_socket)
                if use_ssl
                else irc.connection.Factory()
            )
            s.connect(
                server_settings["host"],
                server_settings["port"],
                nickname=self.settings["nickname"],
                ircname=self.settings["realname"],
                username=self.settings["username"],
                connect_factory=factory,
            )

    def reconnect(self, connection):
        if not connection.is_connected():
            connection.reconnect()

    def _dispatcher(self, connection, event):
        if event.type == "all_raw_messages":
            return

        if event.type == "disconnect":
            self.reactor.scheduler.execute_after(30, lambda: self.reconnect(connection))

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
            os.spawnvpe(
                os.P_NOWAIT,
                sys.executable,
                args=[sys.executable, file_name, "--socket_path", self.temp_folder],
                env=environment,
            )
            self.plugins.append(PluginInterface(name, self))

    def plugin_started(self, plugin):
        logging.info("Bot.plugin_started %s, %s", plugin, self.settings)

        for plugin_name, plugin_settings in self.settings["plugins"].items():
            if plugin_name == plugin.name:
                plugin.started(json.dumps(plugin_settings))
                self.reactor.scheduler.execute_every(1.0, plugin.update)
                logging.debug("Bot.plugin_started, settings %r", plugin_settings)
                break

    def run(self):
        while True:
            self.reactor.process_once(timeout=0.1)

            for plugin in self.plugins:
                plugin.process_once(timeout=0)

            time.sleep(0)  # yield


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="platinumshrimp_") as temp_folder:
        bot = Bot(temp_folder)
        bot.run()
