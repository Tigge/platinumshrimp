
from twisted.internet import endpoints, reactor, protocol
from twisted.python import log
from twisted.words.protocols import irc

from settings import GetSettings

from twisted.internet.task import LoopingCall

from twisted.internet.interfaces import IProcessProtocol

import plugin
import sys
import os
import json

class Bot(irc.IRCClient):

    def __init__(self, settings, channels):
        print "Bot.__init__"
        self.nickname = settings['nickname']
        self.realname = settings['realname']
        self.username = settings['username']
        self._channels = channels
        self.settings = settings

        self.plugins = []

    def loadPlugin(self, name):
        print "Bot.loadPlugin"
        p = plugin.PluginProtocol(name, self)
        reactor.spawnProcess(p, sys.executable, args=[sys.executable, name + ".py"], env=os.environ)
        self.plugins.append(p)

    def connectionMade(self):
        print "Bot.connectionMade"
        irc.IRCClient.connectionMade(self)

        self.loadPlugin("trakt")

    def connectionLost(self, reason):
        print "Bot.connectionLost"

    def signedOn(self):
        print "Bot.signedOn"

        for plugin in self.plugins:
            settings = self.settings["plugins"].get(plugin.get_name(), {})
            plugin.started(json.dumps(settings))
            LoopingCall(plugin.update).start(1, now=False)

        for channel in self._channels:
            self.join(channel['name'])

    def joined(self, channel):
        print "Bot.joined", channel
        for plugin in self.plugins:
            plugin.joined(channel)

    def privmsg(self, user, channel, message):
        print "Bot.privmsg", user, channel, message
        for plugin in self.plugins:
            plugin.privmsg(user, channel, message)


class BotFactory(protocol.ClientFactory):

    def __init__(self, settings):
        print "BotFactory.__init__"
        self._settings = settings

    def _setChannels(self, channels):
        self._channels = channels

    def buildProtocol(self, addr):
        print "BotFactory.buildProtocol"
        return Bot(self._settings, self._channels)

    def clientConnectionLost(self, connector, reason):
        print "BotFactory.clientConnectionLost"
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "BotFactory.clientConnectionFailed"
        reactor.stop()


if __name__ == '__main__':
    print "main"
    settings = GetSettings()
    factory = BotFactory(settings)
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

