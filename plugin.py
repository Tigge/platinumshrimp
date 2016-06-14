import logging
import threading
import zmq
import os
import tempfile
import argparse

__author__ = 'tigge'

plugin_argparser = argparse.ArgumentParser(description='Start a platinumshrimp plugin')
plugin_argparser.add_argument("--socket_path", type=str, default=tempfile.gettempdir(),
                              help="The path to the location where platinumshrimp stores the IPC socket",
                             dest="socket_path")

class Plugin:

    def __init__(self, name):
        logging.basicConfig(filename=name + ".log", level=logging.DEBUG)

        context = zmq.Context()

        args, _ = plugin_argparser.parse_known_args()
        self.socket_base_path = args.socket_path

        self._socket_bot = context.socket(zmq.PAIR)
        self._socket_bot.connect("ipc://" + self.socket_base_path + "/ipc_plugin_" + name)

        self._socket_workers = context.socket(zmq.PULL)
        self._socket_workers.bind("ipc://" + self.socket_base_path + "/ipc_plugin_" + name + "_workers")

        self._poller = zmq.Poller()
        self._poller.register(self._socket_bot, zmq.POLLIN)
        self._poller.register(self._socket_workers, zmq.POLLIN)

        self.name = name

        logging.info("Plugin.init %s, %s", threading.current_thread().ident, "ipc://ipc_plugin_" + name)

        self.threading_data = threading.local()
        self.threading_data.call_socket = self._socket_bot

    def _recieve(self, data):
        getattr(self, data["function"])(*data["params"])

    def _call(self, function, *args):
        logging.info("Plugin.call %s", self.threading_data.__dict__)
        socket = self.threading_data.call_socket
        socket.send_json({"function": function, "params": args})

    def _thread(self, function, *args, **kwargs):
        logging.info("Plugin._thread %r", function)

        def starter():
            context = zmq.Context()
            sock = context.socket(zmq.PUSH)
            sock.connect("ipc://" + self.socket_base_path + "/ipc_plugin_" + self.name + "_workers")
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

    @classmethod
    def run(cls):
        instance = cls()
        logging.info("Plugin.run %s, %s", cls, instance)
        instance._run()

    def __getattr__(self, name):
        if name in ["action", "admin", "cap", "ctcp", "ctcp_reply", "globops", "info", "invite", "ison",
                    "join", "kick", "links", "list", "lusers", "mode", "motd", "names", "nick", "notice",
                    "oper", "part", "pass_", "ping", "pong", "privmsg", "quit", "squit", "stats", "time",
                    "topic", "trace", "user", "userhost", "users", "version", "wallops", "who", "whois",
                    "whowas"]:
            def call(*args, **kwarg):
                self._call(name, *args)
            return call
        else:
            raise AttributeError(name + ' not found.')

