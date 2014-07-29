
from twisted.internet import endpoints, reactor, protocol
from twisted.python import log
from twisted.words.protocols import irc

from settings import GetSettings

class Bot(irc.IRCClient):

    def __init__(self, settings, channels):
        print "Bot.__init__"
        self.nickname = settings['nickname']
        self.realname = settings['realname']
        self.username = settings['username']
        self._channels = channels

    def connectionMade(self):
        print "Bot.connectionMade"
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        print "Bot.connectionLost"

    def signedOn(self):
        print "Bot.signedOn"
        for channel in self._channels:
            self.join(channel['name'])

    def joined(self, channel):
        print "Bot.joined", channel

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

