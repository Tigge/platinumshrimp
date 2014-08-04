from twisted.internet import protocol, reactor, stdio
from twisted.protocols import amp
from twisted.protocols.amp import String, Integer, Command
from twisted.python import log

class Started(Command):
    arguments = [('settings', String()),]

class Update(Command):
    pass

class Privmsg(Command):
    arguments = [('server_id', Integer()),
                 ('user', String()),
                 ('channel', String()),
                 ('message', String()),]

class Join(Command):
    arguments = [('server_id', Integer()),
                 ('channel', String()),]

class Joined(Command):
    arguments = [('server_id', Integer()),
                 ('channel', String()),]

class Say(Command):
    arguments = [('server_id', Integer()),
                 ('channel', String()),
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
            raise AttributeError(self, name)


class PluginProtocol(protocol.ProcessProtocol):

    class InternalBidirectionalAMP(BidirectionalAMP):

        def __init__(self, bot):
            BidirectionalAMP.__init__(self)
            self.bot = bot
            self.responses = [Say, Join]
            self.calls = [Started, Update, Joined, Privmsg]

        def __getattr__(self, name):
            try:
                return BidirectionalAMP.__getattr__(self, name)
            except:
                return getattr(self.bot, name)


    def __init__(self, name, bot):
        self.name = name
        self.bot = bot

        self.responses = [Say, Join]
        self.calls = [Started, Update, Joined, Privmsg]

        self.amp = PluginProtocol.InternalBidirectionalAMP(bot)

    def __getattr__(self, name):
        return getattr(self.amp, name)

    def get_name(self):
        return self.name

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

    def __init__(self, name):
        BidirectionalAMP.__init__(self)
        self.responses = [Started, Update, Joined, Privmsg]
        self.calls = [Say, Join]
        self.name = name

    @classmethod
    def run(cls):
        try:
            instance = cls()
            log.startLogging(open(instance.name + '.log', 'w'))
            stdio.StandardIO(instance)
            reactor.run()
        except:
            log.err()

    # Methods to override:
    def started(self, settings):
        log.msg("Plugin.started")

    def joined(self, server_id, channel):
        log.msg("Plugin.joined", channel)

    def update(self):
        log.msg("Plugin.update")

    def privmsg(self, server_id, user, channel, message):
        log.msg("Plugin.privmsg", user, channel, message)

