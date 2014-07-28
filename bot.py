from twisted.words.protocols import irc

from twisted.internet import endpoints

from twisted.internet import reactor, protocol
from twisted.python import log

from twisted.internet import reactor

class Bot(irc.IRCClient):

    def __init__(self):
        print "Bot.__init__"
        self.nickname = "platinumshrimp"
        self.realname = "Platinum Shrimp"
        self.username = "platinumshrimp"

    def connectionMade(self):
        print "Bot.connectionMade"
        irc.IRCClient.connectionMade(self)
        
    def connectionLost(self, reason):
        print "Bot.connectionLost"

    def signedOn(self):
        print "Bot.signedOn"
        self.join("#silvertrout")

    def joined(self, channel):
        print "Bot.joined", channel

class BotFactory(protocol.ClientFactory):

    def __init__(self):
        print "BotFactory.__init__"

    def buildProtocol(self, addr):
        print "BotFactory.buildProtocol"
        return Bot()

    def clientConnectionLost(self, connector, reason):
        print "BotFactory.clientConnectionLost"
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "BotFactory.clientConnectionFailed"
        reactor.stop()


if __name__ == '__main__':
    print "main"
    endpoint = endpoints.clientFromString(reactor, "tcp:host=irc.chalmers.it:port=6667")
    factory = BotFactory()
    conn = endpoint.connect(factory)
    reactor.run()

