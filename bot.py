import sys
import os
import json

from twisted.internet import endpoints, reactor, protocol
from twisted.words.protocols import irc
from twisted.internet.task import LoopingCall
from twisted.python import log
import zmq

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
        log.msg("PluginInterface._recieve", data)
        getattr(self.bot, data["function"])(*data["params"])

    def _call(self, function, *args):
        log.msg("PluginInterface._call", function, args)
        self._socket_plugin.send_json({"function": function, "params": args})

    def update(self):
        try:
            socks = dict(self._poller.poll(timeout=0))
        except KeyboardInterrupt:
            return

        if self._socket_plugin in socks:
            log.msg("PluginInterface.update", self._socket_plugin)
            self._recieve(self._socket_plugin.recv_json())

    def __getattr__(self, name):
        log.msg("PluginInterface.__getattr__", name)
        if name in ["started", "onconnected", "joined", "privmsg"]:
            def call(*args, **kwarg):
                self._call(name, *args)
            return call
        else:
            raise AttributeError(self, name)


class Server(irc.IRCClient):

    def __init__(self, settings, plugins):
        log.msg("Server.__init__")
        self.nickname = settings['nickname']
        self.realname = settings['realname']
        self.username = settings['username']
        self._name = None
        self._settings = settings
        self._plugins = plugins

        self._encoding = "utf-8"

    def connectionMade(self):
        log.msg("Server.connectionMade")
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        for plugin in self._plugins.iterkeys():
            plugin.ondisconnected(self._name)
        log.msg("Server.connectionLost")

    def signedOn(self):
        log.msg("Server.signedOn " + self._name, self._plugins)

        for plugin in self._plugins.iterkeys():
            log.msg("ser " + str(plugin.onconnected))
            plugin.onconnected(self._name)

    # region Encoding overrides

    def msg(self, user, message, length=None):
        log.msg("Server.msg", user, type(message), length)
        irc.IRCClient.msg(self, str(user), message.encode(self._encoding), length)

    def topic(self, channel, topic=None):
        log.msg("Server.topic", channel, type(topic))
        irc.IRCClient.topic(self, channel, topic.encode(self._encoding))

    def notice(self, user, message):
        irc.IRCClient.notice(self, user, message.encode(self._encoding))

    def away(self, message=''):
        irc.IRCClient.away(self, message.encode(self._encoding))

    def quit(self, message=''):
        irc.IRCClient.quit(self, message.encode(self._encoding))

    # endregion

    def joined(self, channel):
        log.msg("Server.joined", self._name, channel)
        for plugin in self._plugins.iterkeys():
            plugin.joined(self._name, channel)

    def privmsg(self, user, channel, message):
        log.msg("Server.privmsg", self._name, user, channel, message)
        for plugin in self._plugins.iterkeys():
            plugin.privmsg(self._name, user, channel, message.decode(self._encoding))

    def irc_unknown(self, prefix, command, params):
        if command == "INVITE":
            for plugin in self._plugins.iterkeys():
                plugin.invited(self._name, params[1])


class Bot(protocol.ClientFactory):

    def __init__(self, settings):
        log.msg("Bot.__init__", settings)
        self._settings = settings
        self._servers = dict()
        self._plugins = dict()
        if 'plugins' in settings:
            for plugin in self._settings['plugins']:
                self.plugin_load(plugin['name'], plugin['settings'])

    def plugin_load(self, name, settings):
        log.msg("Bot.plugin_load", name, settings)
        plugin = PluginInterface(name, self)
        file_name = "plugins/" + name + "/" + name + ".py"
        if not os.path.isfile(file_name):
            log.err("Unable to load plugin", name)
        else:
            log.msg("Bot.plugin_load plugin", plugin, name, self, sys.executable, [sys.executable, file_name])
            #reactor.spawnProcess(plugin, sys.executable, args=[sys.executable, file_name], env={"PYTHONPATH": os.getcwd()})
            os.spawnvpe(os.P_NOWAIT, sys.executable, args=[sys.executable, file_name], env={"PYTHONPATH": os.getcwd()})
            update_loop = LoopingCall(plugin.update)
            update_loop.start(0.1, now=True)
            plugin._call("privmsg", "a", "b", "c", ".reverse reverse")

    def plugin_started(self, plugin):
        log.msg("Bot.plugin_started", plugin, self._settings)

        for p in self._settings['plugins']:
            if p["name"] == plugin.name:
                self._plugins[plugin] = p["settings"]

        log.msg("Bot.plugin_started settings", self._plugins[plugin])

        plugin.update_loop_call = LoopingCall(plugin.update)
        plugin.started(json.dumps(self._plugins[plugin]))
        plugin.update_loop_call.start(1, now=False)

    def plugin_ended(self, plugin):
        log.msg("Bot.plugin_ended", plugin)

        if plugin not in self._plugins:
            log.msg("Bot.plugin_ended already deleted")
            return

        name = plugin.name
        settings = self._plugins[plugin]

        # Delete plugin
        plugin.update_loop_call.stop()
        del self._plugins[plugin]

        # Reload plugin
        self.plugin_load(name, settings)

    def say(self, server, channel, message):
        log.msg("Bot.say", server, channel, message)
        if server in self._servers:
            # From https://tools.ietf.org/html/rfc1459 :
            # IRC messages are always lines of characters terminated with a CR-LF
            # (Carriage Return - Line Feed) pair, and these messages shall not
            # exceed 512 characters in length, counting all characters including
            # the trailing CR-LF. Thus, there are 510 characters maximum allowed
            # for the command and its parameters.
            max_length = 510 - 8 - len(channel) - 1 # 8 here is the length of
                                                    # "PRIVMSG " and 1 is for
                                                    # the space between the
                                                    # target (channel) and the
                                                    # actual message
            self._servers[server].say(channel, message, max_length)

    def join(self, server, channel):
        log.msg("Bot.join " + server + ", " + channel)
        if server in self._servers:
            self._servers[server].join(str(channel))

    def buildProtocol(self, addr):
        log.msg("Bot.buildProtocol")
        return Server(self._settings, self._plugins)

    def connected(self, name, server):
        log.msg("Bot.connected")
        server._name = name
        self._servers[name] = server

    def clientConnectionLost(self, connector, reason):
        log.msg("Bot.clientConnectionLost")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.msg("Bot.clientConnectionFailed")
        reactor.stop()

if __name__ == '__main__':
    log.startLogging(open('Bot.log', 'a'))
    log.msg("main")
    config = settings.get_settings()
    if not settings.validate_settings(config):
        print("Error parsing settings")
        sys.exit(1)
    factory = Bot(config)
    for server in config['servers']:
        log.msg("main: creating endpoint for host:", server['host'], "port:", server['port'], "ssl:", server['ssl'])
        con_type = "ssl" if server['ssl'] else "tcp"
        con_desc = "{}:host={}:port={}".format(con_type, server['host'], server['port'])
        endpoint = endpoints.clientFromString(reactor, con_desc)
        conn = endpoint.connect(factory).addCallback(lambda s: factory.connected(server['name'], s))
    reactor.run()
