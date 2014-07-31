
from twisted.internet import protocol, utils, reactor

from twisted.protocols.amp import Integer, String, Unicode, Command

from twisted.internet import stdio
from twisted.protocols import basic

from zope.interface import implements

from  twisted.protocols import amp

from  twisted.internet.interfaces import IProcessProtocol

class Started(Command):
    pass

class Update(Command):
    pass

class Privmsg(Command):
    arguments = [('user', String()),
                 ('channel', String()),
                 ('message', String()),]

class Join(Command):
    arguments = [('channel', String()),]

class Joined(Command):
    arguments = [('channel', String()),]

class Say(Command):
    arguments = [('channel', String()),
                 ('message', String()),]


class BidirectionalAMP(amp.AMP):
    
    def __init__(self):
        self.responses = []
        self.calls = []
    
    def locateResponder(self, class_name):
        cls = globals()[class_name]
        if cls not in self.responses:
            return None
        method = getattr(self, cls.__name__.lower())
        def responder_inner(box):
            params = cls.parseArguments(box, self)
            result = method(**params)
            return cls.makeResponse({}, self)
        return responder_inner
    
    def __getattr__(self, name):
        for cls in self.calls:
            if cls.__name__.lower() == name:
                def call(*args, **kwarg):
                    arguments = {}
                    for i, v in enumerate(cls.arguments):
                        arguments[v[0]] = args[i]
                    self.callRemote(cls, **arguments)
                return call
        else:
            raise AttributeError()


class PluginProtocol(protocol.ProcessProtocol):
    
    class InternalBidirectionalAMP(BidirectionalAMP):

        def __init__(self, bot):
            self.bot = bot
            self.responses = [Say, Join]
            self.calls = [Started, Update, Joined, Privmsg]

        def __getattr__(self, name):
            try:
                return BidirectionalAMP.__getattr__(self, name)
            except:
                return getattr(self.bot, name)


    def __init__(self, bot):
        self.bot = bot

        self.responses = [Say, Join]
        self.calls = [Started, Update, Joined]

        self.amp = PluginProtocol.InternalBidirectionalAMP(bot)

    def __getattr__(self, name):
        return getattr(self.amp, name)

    def makeConnection(self, process):
        print "PluginProtocol.makeConnection", process
        protocol.ProcessProtocol.makeConnection(self, process)
        self.amp.makeConnection(self)

    def write(self, data):
        self.transport.writeToChild(0, data)

    def getPeer(self):
        return ('subprocess',)

    def getHost(self):
        return ('no host',)

    def connectionLost(self, reason):
        print "PluginProtocol.connectionLost", reason

    def childDataReceived(self, childFD, data):
        print "PluginProtocol.childDataReceived", childFD, data
        return self.amp.dataReceived(data)

    def loseConnection(self):
        self.transport.closeChildFD(0)
        self.transport.closeChildFD(1)
        self.transport.loseConnection()

    def childConnectionLost(self, childFD):
        print "PluginProtocol.childConnectionLost", childFD

    def processExited(self, reason):
        print "PluginProtocol.processExited", reason

    def processEnded(self, reason):
        print "PluginProtocol.processEnded", reason


class Plugin(BidirectionalAMP):
    
    def __init__(self):
        self.responses = [Started, Update, Joined]
        self.calls = [Say, Join]

    @classmethod
    def run(cls):
        stdio.StandardIO(cls())
        reactor.run()

