import asyncio
import logging
import locale
import threading
import zmq
import zmq.asyncio
import tempfile
import argparse
import sys
import textwrap

from utils import str_utils

__author__ = "tigge"

plugin_argparser = argparse.ArgumentParser(description="Start a platinumshrimp plugin")
plugin_argparser.add_argument(
    "--socket_path",
    type=str,
    default=tempfile.gettempdir(),
    help="The path to the location where platinumshrimp stores the IPC socket",
    dest="socket_path",
)


class Plugin:
    def __init__(self, name):

        locale.setlocale(locale.LC_ALL, "")
        logging.basicConfig(filename=name + ".log", level=logging.DEBUG)

        context = zmq.asyncio.Context()

        args, _ = plugin_argparser.parse_known_args()
        self.socket_base_path = args.socket_path

        self._socket_bot = context.socket(zmq.PAIR)
        self._socket_bot.connect("ipc://" + self.socket_base_path + "/ipc_plugin_" + name)

        self._socket_workers = context.socket(zmq.PULL)
        self._socket_workers.bind(
            "ipc://" + self.socket_base_path + "/ipc_plugin_" + name + "_workers"
        )

        self._poller = zmq.asyncio.Poller()
        self._poller.register(self._socket_bot, zmq.POLLIN)
        self._poller.register(self._socket_workers, zmq.POLLIN)

        self.name = name

        self.main_thread_ident = threading.current_thread().ident
        logging.info(f"Plugin.init {self.main_thread_ident}, ipc://ipc_plugin_{name}")
        self.threading_data = threading.local()
        self.threading_data.call_socket = self._socket_bot

    def _recieve(self, data):
        func_name = data["function"]
        if func_name.startswith("on_") or func_name in ["started", "update"]:
            try:
                func = getattr(self, func_name)
            except AttributeError as e:
                pass  # Not all plugins implements all functions, therefore silencing if not found.
            else:
                func(*data["params"])

        else:
            logging.warning("Unsupported call to plugin function with name " + func_name)

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

    async def _run(self):
        while True:
            socks = dict(await self._poller.poll())

            if self._socket_bot in socks:
                self._recieve(await self._socket_bot.recv_json())

            if self._socket_workers in socks:
                self._socket_bot.send(await self._socket_workers.recv())

    @classmethod
    def run(cls):

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        instance = cls()
        logging.info("Plugin.run %s, %s", cls, instance)

        loop.create_task(instance._run())
        try:
            loop.run_forever()
        except:
            logging.exception("Plugin.run aborted")

        loop.close()
        sys.exit(1)

    def __getattr__(self, name):
        # List covers available commands to be sent to the IRC server
        if name in [
            "action",
            "admin",
            "cap",
            "ctcp",
            "ctcp_reply",
            "globops",
            "info",
            "invite",
            "ison",
            "join",
            "kick",
            "links",
            "list",
            "lusers",
            "mode",
            "motd",
            "names",
            "nick",
            "notice",
            "oper",
            "part",
            "pass_",
            "ping",
            "pong",
            "privmsg",
            "quit",
            "squit",
            "stats",
            "time",
            "topic",
            "trace",
            "user",
            "userhost",
            "users",
            "version",
            "wallops",
            "who",
            "whois",
            "whowas",
            "_save_settings",
        ]:

            def call(*args, **kwarg):
                self._call(name, *args)

            return call
        else:
            raise AttributeError("Unsupported internal function call to function: " + name)

    def safe_privmsg(self, server, target, message):
        if threading.current_thread().ident == self.main_thread_ident:
            logging.info("Plugin.safe_privmsg on main thread, pushing to new thread")
            self._thread(self.safe_privmsg, server, target, message)
            return
        # Even though the standard should be "up to 512" characters, various clients and servers
        # impose a much stricter limit.  Let's use 400 as a "safe" upper bound.
        max_length = 400 - len(f"PRIVMSG {target} ")
        for unescaped_line in str_utils.unescape_entities(message).splitlines():
            wrapped = textwrap.wrap(unescaped_line, width=max_length, fix_sentence_endings=True)
            for safe_line in wrapped:
                self.privmsg(server, target, safe_line)
