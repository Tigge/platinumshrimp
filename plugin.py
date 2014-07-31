
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
                 ('msg', String()),]

class Join(Command):
    arguments = [('channel', String()),]

class Joined(Command):
    arguments = [('channel', String()),]

class Say(Command):
    arguments = [('channel', String()),
                 ('msg', String()),]

class PluginProtocol(protocol.ProcessProtocol):
    
    class Test(amp.AMP):

        def __init__(self, bot):
            self.bot = bot

        @Say.responder
        def say(self, channel, msg):
            print "PluginProtocol.say", channel, msg
            self.bot.say(channel, msg)
            return {}

        @Join.responder
        def join(self, channel):
            print "PluginProtocol.join", channel
            self.bot.join(channel)
            return {}


    def __init__(self, bot):
        self.bot = bot
        self.amp = PluginProtocol.Test(bot)

    def privmsg(self, user, channel, msg):
        print "PluginProtocol.privmsg", user, channel, msg
        self.amp.callRemote(Privmsg, user=user, channel=channel, msg=msg)

    def started(self):
        print "PluginProtocol.started"
        self.amp.callRemote(Started)

    def joined(self, channel):
        print "PluginProtocol.joined", channel
        self.amp.callRemote(Joined, channel=channel)

    def update(self):
        print "PluginProtocol.update"
        self.amp.callRemote(Update)

    def makeConnection(self, process):
        print "PluginProtocol.makeConnection", process
        protocol.ProcessProtocol.makeConnection(self, process)
        self.amp.makeConnection(self)

    def write(self, data):
        #print self.transport
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


class Plugin(amp.AMP):
    
    def __init__(self):
        self.f = open("Plugin.__init__", "w")
        self.f.write("ok\n")
    
    def say(self, channel, msg):
        self.callRemote(Say, channel=channel, msg=msg)

    def join(self, channel):
        self.callRemote(Join, channel=channel)

    def started(self):
        pass
        
    @Started.responder
    def started_resp(self):
        self.started()
        return {}

    def update(self):
        pass
        
    @Update.responder
    def update_resp(self):
        self.update()
        return {}

    def joined(self, channel):
        pass
        
    @Joined.responder
    def joined_resp(self, channel):
        self.joined(channel)
        return {}

    @classmethod
    def run(cls):
        stdio.StandardIO(cls())
        reactor.run()

