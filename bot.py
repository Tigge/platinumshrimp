import sys
import os
import json

from twisted.internet import endpoints, reactor, protocol
from twisted.words.protocols import irc
from twisted.internet.task import LoopingCall
from twisted.python import log

import settings
from plugin import PluginProtocol


class Server(irc.IRCClient):

    def __init__(self, server_id, settings, channels, plugins):
        log.msg("Server.__init__")
        self.nickname = settings['nickname']
        self.realname = settings['realname']
        self.username = settings['username']
        self._id = server_id
        self._settings = settings
        self._channels = channels
        self._plugins = plugins

    def connectionMade(self):
        log.msg("Server.connectionMade")
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        log.msg("Server.connectionLost")

    def signedOn(self):
        log.msg("Server.signedOn")
        for channel in self._channels:
            self.join(channel['name'])

    def joined(self, channel):
        log.msg("Server.joined", channel)
        for plugin in self._plugins.iterkeys():
            plugin.joined(self._id, channel)

    def privmsg(self, user, channel, message):
        log.msg("Server.privmsg", user, channel, message)
        for plugin in self._plugins.iterkeys():
            plugin.privmsg(self._id, user, channel, message)

    def irc_unknown(self, prefix, command, params):
        if command == "INVITE":
          for plugin in self._plugins.iterkeys():
            plugin.invited(self._id, params[1])


class Bot(protocol.ClientFactory):

    def __init__(self, settings):
        log.msg("Bot.__init__", settings)
        self._settings = settings
        self._servers = []
        self._plugins = dict()
        for plugin in self._settings['plugins']:
            self.plugin_load(plugin['name'], plugin['settings'])

    def plugin_load(self, name, settings):
        log.msg("Bot.plugin_load", name, settings)
        plugin = PluginProtocol(name, self)
        log.msg("Bot.plugin_load plugin", plugin, name, self, sys.executable, [sys.executable, "plugins/" + name + "/" + name + ".py"])
        reactor.spawnProcess(plugin, sys.executable, args=[sys.executable, "plugins/" + name + "/" + name + ".py"], env={"PYTHONPATH": os.getcwd()})

    def plugin_started(self, plugin):
        log.msg("Bot.plugin_started", plugin, self._settings)

        for p in self._settings['plugins']:
            if p["name"] == plugin.name:
                self._plugins[plugin] = p["settings"]

        log.msg("Bot.plugin_started settings", self._plugins[plugin])

        plugin.started(json.dumps(self._plugins[plugin]))
        plugin.update_loop_call = LoopingCall(plugin.update)
        plugin.update_loop_call.start(1, now=False)

    def plugin_ended(self, plugin):
        log.msg("Bot.plugin_ended", plugin)
        name = plugin.name
        settings = self._plugins[plugin]

        # Delete plugin
        plugin.update_loop_call.stop()
        del self._plugins[plugin]

        #Reload plugin
        self.plugin_load(name, settings)

    def _setChannels(self, channels):
        self._channels = channels

    def say(self, server_id, channel, message):
        if (len(self._servers) > server_id):
            self._servers[server_id].say(channel, message)

    def join(self, server_id, channel):
        if (len(self._servers) > server_id):
            self._servers[server_id].join(channel)

    def buildProtocol(self, addr):
        log.msg("Bot.buildProtocol")
        server = Server(len(self._servers), self._settings, self._channels, self._plugins)
        self._servers.append(server)
        return server

    def clientConnectionLost(self, connector, reason):
        log.msg("Bot.clientConnectionLost")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.msg("Bot.clientConnectionFailed")
        reactor.stop()


if __name__ == '__main__':
    log.startLogging(open('Bot.log', 'a'))
    log.msg("main")
    settings = settings.get_settings()
    factory = Bot(settings)
    for server in settings['servers']:
        log.msg("main: creating enpoint for host:", server['host'], "port:", server['port'])
        #TODO: Find better way of sending default channels to bot:
        factory._setChannels(server['channels'])
        endpoint = endpoints.clientFromString(reactor,
            "tcp:host={}:port={}".format(server['host'], server['port']))
        conn = endpoint.connect(factory)
    reactor.run()
