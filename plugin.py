from twisted.internet import protocol, reactor, stdio
from twisted.protocols import amp
from twisted.protocols.policies import TimeoutMixin
from twisted.protocols.amp import String, Command, Unicode
from twisted.python import log


class Started(Command):
    arguments = [('settings', String())]


class Update(Command):
    pass


class Privmsg(Command):
    arguments = [('server_id', String()),
                 ('user', String()),
                 ('channel', String()),
                 ('message', Unicode())]


class Join(Command):
    arguments = [('server_id', String()),
                 ('channel', String())]


class Joined(Command):
    arguments = [('server_id', String()),
                 ('channel', String())]


class Say(Command):
    arguments = [('server_id', String()),
                 ('channel', String()),
                 ('message', Unicode())]


class Invited(Command):
    arguments = [('server_id', String()),
                 ('channel', String())]


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


class PluginProtocol(protocol.ProcessProtocol, TimeoutMixin):

    class InternalBidirectionalAMP(BidirectionalAMP):

        def __init__(self, bot):
            BidirectionalAMP.__init__(self)
            self.bot = bot
            self.responses = [Say, Join]
            self.calls = [Started, Update, Joined, Privmsg, Invited]

        def __getattr__(self, name):
            try:
                return BidirectionalAMP.__getattr__(self, name)
            except:
                log.msg("Calling outer function", name)
                return getattr(self.bot, name)

    def __init__(self, name, bot):
        log.msg("PluginProtocol.__init__", name, bot)
        self.name = name
        self.bot = bot

        self.responses = [Say, Join]
        self.calls = [Started, Update, Joined, Privmsg, Invited]

        self.setTimeout(60)

        self.amp = PluginProtocol.InternalBidirectionalAMP(bot)

    def __getattr__(self, name):
        return getattr(self.amp, name)

    def get_name(self):
        return self.name

    def makeConnection(self, process):
        log.msg("PluginProtocol.makeConnection", process)
        self.amp.makeConnection(self)
        protocol.ProcessProtocol.makeConnection(self, process)

    def write(self, data):
        try:
            self.transport.writeToChild(0, data)
        except:
            log.err()

    def getPeer(self):
        return ('subprocess',)

    def getHost(self):
        return ('no host',)

    def connectionLost(self, reason):
        log.msg("PluginProtocol.connectionLost", reason)

    def connectionMade(self):
        log.msg("PluginProtocol.connectionMade")
        self.amp.connectionMade()
        protocol.ProcessProtocol.connectionMade(self)
        self.bot.plugin_started(self)

    def childDataReceived(self, childFD, data):
        self.resetTimeout()
        return self.amp.dataReceived(data)

    def childConnectionLost(self, childFD):
        log.msg("PluginProtocol.childConnectionLost")
        self.loseConnection()

    def loseConnection(self):
        log.msg("PluginProtocol.loseConnection")
        self.transport.loseConnection()
        self.transport.signalProcess('KILL')

    def processExited(self, reason):
        log.msg("PluginProtocol.processExited", reason)

    def processEnded(self, reason):
        log.msg("PluginProtocol.processEnded", reason)
        self.bot.plugin_ended(self)


class Plugin(BidirectionalAMP):

    def __init__(self, name):
        BidirectionalAMP.__init__(self)
        self.responses = [Started, Update, Joined, Privmsg, Invited]
        self.calls = [Say, Join]
        self.name = name

    @classmethod
    def run(cls):
        try:
            instance = cls()
            log.startLogging(open(instance.name + '.log', 'a'))
            stdio.StandardIO(instance)
            reactor.run()
        except:
            log.err()

    # Methods to override:
    def started(self, settings):
        pass

    def joined(self, server_id, channel):
        pass

    def update(self):
        pass

    def privmsg(self, server_id, user, channel, message):
        pass

    def invited(self, server_id, channel):
        pass
