import threading
import zmq

from twisted.python import log

__author__ = 'tigge'


class Plugin:

    def __init__(self, name):
        context = zmq.Context()

        self._socket_bot = context.socket(zmq.PAIR)
        self._socket_bot.connect("ipc://ipc_plugin_" + name)

        self._socket_workers = context.socket(zmq.PULL)
        self._socket_workers.bind("ipc://ipc_plugin_" + name + "_workers")

        self._poller = zmq.Poller()
        self._poller.register(self._socket_bot, zmq.POLLIN)
        self._poller.register(self._socket_workers, zmq.POLLIN)

        self.name = name

        log.msg("Plugin.init", threading.current_thread().ident)

        self.threading_data = threading.local()
        self.threading_data.call_socket = self._socket_bot


    def _recieve(self, data):
        log.msg("Plugin.receive", threading.current_thread().ident)
        getattr(self, data["function"])(*data["params"])

    def _call(self, function, *args):
        log.msg("Plugin.call", self.threading_data.__dict__)
        socket = self.threading_data.call_socket
        socket.send_json({"function": function, "params": args})

    def _thread(self, function, *args, **kwargs):
        logging.info("Plugin._thread %r", function)

        def starter():
            context = zmq.Context()
            sock = context.socket(zmq.PUSH)
            sock.connect("ipc://ipc_plugin_" + self.name + "_workers")
            self.threading_data.call_socket = sock

            function(*args, **kwargs)

        thread = threading.Thread(target=starter)
        thread.start()

    def _run(self):
        while True:
            try:
                socks = dict(self._poller.poll())
            except KeyboardInterrupt:
                break

            if self._socket_bot in socks:
                self._recieve(self._socket_bot.recv_json())

            if self._socket_workers in socks:
                self._socket_bot.send(self._socket_workers.recv())

            log.msg("Plugin._run", socks)

    @classmethod
    def run(cls):
        log.startLogging(open('Reverser.log', 'a'))
        instance = cls()
        log.msg("Plugin.run", cls, instance)
        instance._run()

    def __getattr__(self, name):
        log.msg("Plugin.__getattr__", name)
        if name in ["say", "join"]:
            def call(*args, **kwarg):
                self._call(name, *args)
            return call
        else:
            def call(*args, **kwarg):
                pass
            return call

    # Methods to override:
    def started(self, settings):
        pass

    def onconnected(self, server):
        pass

    def ondisconnected(self, server):
        pass

    def joined(self, server, channel):
        pass

    def update(self):
        pass

    def privmsg(self, server, user, channel, message):
        pass

    def invited(self, server, channel):
        pass
