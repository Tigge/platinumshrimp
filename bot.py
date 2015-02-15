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

        self._encoding = "utf-8"

    def connectionMade(self):
        log.msg("Server.connectionMade")
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        log.msg("Server.connectionLost")

    def signedOn(self):
        log.msg("Server.signedOn")
        for channel in self._channels:
            self.join(channel['name'])

    # region Encoding overrides

    def msg(self, user, message, length=None):
        log.msg("Server.msg", user, type(message), length)
        irc.IRCClient.msg(self, user, message.encode(self._encoding), length)

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
        log.msg("Server.joined", self._id, channel)
        for plugin in self._plugins.iterkeys():
            plugin.joined(self._id, channel)

    def privmsg(self, user, channel, message):
        log.msg("Server.privmsg", self._id, user, channel, message)
        for plugin in self._plugins.iterkeys():
            plugin.privmsg(self._id, user, channel, message.decode(self._encoding))

    def irc_unknown(self, prefix, command, params):
        if command == "INVITE":
            for plugin in self._plugins.iterkeys():
                plugin.invited(self._id, params[1])


class Bot(protocol.ClientFactory):

    def __init__(self, settings):
        log.msg("Bot.__init__", settings)
        self._settings = settings
        self._servers = dict()
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

        #Reload plugin
        self.plugin_load(name, settings)

    def _setChannels(self, channels):
        self._channels = channels

    def say(self, server_id, channel, message):
        log.msg("Bot.say", server_id, channel, message)
        if server_id in self._servers:
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
            self._servers[server_id].say(channel, message, max_length)

    def join(self, server_id, channel):
        if server_id in self._servers:
            self._servers[server_id].join(channel)

    def buildProtocol(self, addr):
        log.msg("Bot.buildProtocol")
        address = str(addr)
        if addr in self._servers:
            #TODO(reggna): What do we do when trying to join the same serverdo we do when trying to join the same server twice??
            log.msg("Trying to join already existing server?  : " + address)
        server = Server(address, self._settings, self._channels, self._plugins)
        self._servers[address] = server
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
