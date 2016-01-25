import ssl
import sys
import os
import json
import time
import logging

import zmq
import irc.client

from utils import settings


class PluginInterface:
    def __init__(self, name, bot):

        logging.info("PluginInterface.__init__ %s", "ipc://ipc_plugin_" + name)
        self.name = name
        self.bot = bot

        context = zmq.Context()

        self._socket_plugin = context.socket(zmq.PAIR)
        self._socket_plugin.bind("ipc://ipc_plugin_" + name)

        self._poller = zmq.Poller()
        self._poller.register(self._socket_plugin, zmq.POLLIN)

        self.bot.plugin_started(self)

    def _recieve(self, data):
        logging.info("PluginInterface._recieve %s", data)
        server = data["params"][0]
        if server not in self.bot.servers:
            logging.error("PluginInterface._recieve %s not found", server)
            return

        if data["function"] in ["action", "admin", "cap", "ctcp", "ctcp_reply", "globops", "info", "invite", "ison",
                                "join", "kick", "links", "list", "lusers", "mode", "motd", "names", "nick", "notice",
                                "oper", "part", "pass_", "ping", "pong", "privmsg", "quit", "squit", "stats", "time",
                                "topic", "trace", "user", "userhost", "users", "version", "wallops", "who", "whois",
                                "whowas"]:
            getattr(self.bot.servers[server], data["function"])(*data["params"][1:])
        else:
            logging.error("Undefined function %s called with %r", data["function"], data["params"])

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
    def __init__(self):
        logging.basicConfig(filename="Bot.log", level=logging.DEBUG)

        self.settings = settings.get_settings()
        if not settings.validate_settings(self.settings):
            logging.error("Error parsing settings")
            sys.exit(1)
        self.plugins = list()
        self.servers = dict()

        self.reactor = irc.client.Reactor()
        self.reactor.add_global_handler("all_events", self._dispatcher, -10)

        # Load plugins
        if 'plugins' in self.settings:
            for plugin in self.settings['plugins']:
                self.load_plugin(plugin['name'], plugin['settings'])

        # Connect to servers
        for server in self.settings['servers']:
            logging.info("Connecting to '%s'", server)
            s = self.reactor.server()
            self.servers[server['name']] = s
            s.name = server['name']
            factory = irc.connection.Factory(wrapper=ssl.wrap_socket) if "ssl" in server and server["ssl"] else irc.connection.Factory()
            s.connect(server['host'], server['port'], nickname=self.settings['nickname'],
                      ircname=self.settings['realname'], username=self.settings['username'],
                      connect_factory=factory)

    def reconnect(self, connection):
        if not connection.is_connected():
            connection.reconnect()

    def _dispatcher(self, connection, event):
        if event.type == "all_raw_messages":
            return

        if event.type == "disconnect":
            connection.execute_delayed(30, self.reconnect, (connection,))

        for plugin in self.plugins:
            plugin._call("on_" + event.type, connection.name, event.source, event.target, *event.arguments)

    def load_plugin(self, name, settings):
        logging.info("Bot.plugin_load %s, %s", name, settings)
        file_name = "plugins/" + name + "/" + name + ".py"
        if not os.path.isfile(file_name):
            logging.error("Unable to load plugin %s", name)
        else:
            logging.info("Bot.plugin_load plugin %s, %s, %s, %s", name, self, sys.executable,
                         [sys.executable, file_name])
            os.spawnvpe(os.P_NOWAIT, sys.executable, args=[sys.executable, file_name], env={"PYTHONPATH": os.getcwd()})
            self.plugins.append(PluginInterface(name, self))

    def plugin_started(self, plugin):
        logging.info("Bot.plugin_started %s, %s", plugin, self.settings)

        for p in self.settings['plugins']:
            if p["name"] == plugin.name:
                plugin.started(json.dumps(p["settings"]))
                self.reactor.execute_every(1.0, plugin.update)
                logging.debug("Bot.plugin_started, settings '%s'", p["settings"])
                break

    def run(self):
        while True:
            self.reactor.process_once(timeout=0)

            for plugin in self.plugins:
                plugin.process_once(timeout=0)

            time.sleep(0)  # yield


if __name__ == '__main__':
    bot = Bot()
    bot.run()
