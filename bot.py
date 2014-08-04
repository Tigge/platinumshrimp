
from twisted.internet import endpoints, reactor, protocol
from twisted.python import log
from twisted.words.protocols import irc

import settings

from twisted.internet.task import LoopingCall

from twisted.internet.interfaces import IProcessProtocol

from plugin import PluginProtocol
import sys
import os
import json


class Server(irc.IRCClient):

    def __init__(self, server_id, settings, channels, plugins):
        print "Server.__init__"
        self.nickname = settings['nickname']
        self.realname = settings['realname']
        self.username = settings['username']
        self._id = server_id
        self._settings = settings
        self._channels = channels
        self._plugins = plugins

    def connectionMade(self):
        print "Server.connectionMade"
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        print "Server.connectionLost"

    def signedOn(self):
        print "Server.signedOn"
        for channel in self._channels:
            self.join(channel['name'])

    def joined(self, channel):
        print "Server.joined", channel
        for plugin in self._plugins.iterkeys():
            plugin.joined(self._id, channel)

    def privmsg(self, user, channel, message):
        print "Server.privmsg", user, channel, message
        for plugin in self._plugins.iterkeys():
            print "Sending to plugin: ", self._id, user, channel, message
            plugin.privmsg(self._id, user, channel, message)

class Bot(protocol.ClientFactory):

    def __init__(self, settings):
        print "Bot.__init__"
        self._settings = settings
        self._servers = []
        self._plugins = dict()
        for plugin in self._settings['plugins']:
            self._loadPlugin(plugin['name'], plugin['settings'])

    def _loadPlugin(self, name, settings):
        print "Bot.loadPlugin", name
        plugin = PluginProtocol(name, self)
        reactor.spawnProcess(plugin, sys.executable, args=[sys.executable, "plugins/" + name + "/" + name + ".py"], env={"PYTHONPATH": os.getcwd()})
        self._plugins[plugin] = settings
        plugin.started(json.dumps(settings))
        LoopingCall(plugin.update).start(1, now=False)

    def _setChannels(self, channels):
        self._channels = channels

    def say(self, server_id, channel, message):
        if (len(self._servers) > server_id):
            self._servers[server_id].say(channel, message)

    def join(self, server_id, channel):
        if (len(self._servers) > server_id):
            self._servers[server_id].join(channel)

    def buildProtocol(self, addr):
        print "Bot.buildProtocol"
        server = Server(len(self._servers), self._settings, self._channels, self._plugins)
        self._servers.append(server)
        return server

    def clientConnectionLost(self, connector, reason):
        print "Bot.clientConnectionLost"
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Bot.clientConnectionFailed"
        reactor.stop()


if __name__ == '__main__':
    print "main"
    settings = settings.get_settings()
    factory = Bot(settings)
    for server in settings['servers']:
        print "main: creating enpoint for host: {}, port: {}".format(
            server['host'],
            server['port'])
        #TODO: Find better way of sending default channels to bot:
        factory._setChannels(server['channels'])
        endpoint = endpoints.clientFromString(reactor,
            "tcp:host={}:port={}".format(server['host'], server['port']))
        conn = endpoint.connect(factory)
    reactor.run()

