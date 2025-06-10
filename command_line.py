import asyncio
import cmd
import os
import signal
from threading import Thread

import logging
from utils import settings

__author__ = "reggna"


# CLI to control the bots functionality.
#
# Once created, call command_line.start() in order to create the seprate thread to run the CLI in.
# On teardown, call command_line.wait_until_done() to join the thread back and make a clean exit.
class CommandLine(cmd.Cmd):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.intro = "Welcome to platimumshrimp CLI.  Type ? or help to list available commands."
        self.prompt = "PlatinumShrimp >> "

    def do_exit(self, _):
        """Exit the bot."""
        self.bot.loop.stop()
        return True

    def do_list_servers(self, _):
        """List connected servers with status."""
        for name, server in self.bot.servers.items():
            status = "Connected" if server.is_connected() else "Disconnected"
            print(f"{name}: {status} | Host: {server.server}:{server.port}")

    def do_list_channels(self, arg):
        """List channels on a given server. Usage: list_channels <server>"""
        name = arg.strip()
        if name not in self.bot.servers:
            print(f"Server '{name}' not found.")
            return
        server = self.bot.servers[name]
        channels = getattr(server, "channels", set())
        if not channels:
            print(f"No channels joined on server '{name}'.")
            return
        for channel in sorted(channels):
            print(f"- {channel}")

    def do_join_channel(self, arg):
        """Join a channel. Usage: join_channel <server> <channel>"""
        args = arg.split(" ")
        if len(args) != 2:
            print("Usage: join_channel <server> <channel>")
            return
        server_name, channel = args
        server = self.bot.servers.get(server_name)
        if server:
            server.join(channel)
        else:
            print(f"Server '{server_name}' not found.")

    def do_part_channel(self, arg):
        """Exit (part) a channel. Usage: part_channel <server> <channel>"""
        args = arg.split(" ")
        if len(args) != 2:
            print("Usage: part_channel <server> <channel>")
            return
        server_name, channel = args
        server = self.bot.servers.get(server_name)
        if server:
            server.part(channel)
        else:
            print(f"Server '{server_name}' not found.")

    def do_send_message(self, arg):
        """Send a message. Usage: send_message <server> <channel> <message>"""
        args = arg.split(" ")
        if len(args) < 3:
            print("Usage: send_message <server> <channel> <message>")
            return
        server_name, channel, message = args[0], args[1], " ".join(args[2:])
        server = self.bot.servers.get(server_name)
        if server:
            server.privmsg(channel, message)
        else:
            print(f"Server '{server_name}' not found.")

    def do_reload_settings(self, _):
        """Reload the settings file."""
        try:
            self.bot.settings = settings.load_settings()
            print("Settings reloaded.")
        except Exception as e:
            print(f"Failed to reload settings: {e}")

    def do_list_plugins(self, _):
        """List currently loaded plugins."""
        if not self.bot.plugins:
            print("No plugins loaded.")
            return
        for plugin in self.bot.plugins:
            print(f"{plugin.name} (PID: {plugin.pid})")

    def do_load_plugin(self, arg):
        """Load a plugin. Usage: load_plugin <plugin_name>"""
        name = arg.strip()
        if not name:
            print("Usage: load_plugin <plugin_name>")
            return

        plugin_settings = self.bot.settings.get("plugins", {}).get(name, {})

        async def _load():
            self.bot.load_plugin(name, plugin_settings)
            print(f"Plugin '{name}' loading initiated with settings {plugin_settings}.")

        # Schedule _load on the bot's main asyncio loop
        future = asyncio.run_coroutine_threadsafe(_load(), self.bot.loop)
        try:
            future.result()
        except Exception as e:
            print(f"Error loading plugin '{name}': {e}")

    def do_reload_plugin(self, arg):
        """Reload a plugin. Usage: reload_plugin <plugin_name>"""
        name = arg.strip()
        self.do_unload_plugin(name)
        self.do_reload_settings(arg)
        self.do_load_plugin(name)

    def do_unload_plugin(self, arg):
        """Unload a plugin. Usage: unload_plugin <plugin_name>"""
        name = arg.strip()
        plugin = next((p for p in self.bot.plugins if p.name == name), None)
        if not plugin:
            print(f"Plugin '{name}' not found.")
            return
        try:
            os.kill(plugin.pid, signal.SIGTERM)
            self.bot.plugins.remove(plugin)
            print(f"Plugin '{name}' unloaded.")
        except Exception as e:
            print(f"Error unloading plugin '{name}': {e}")

    def start(self):
        self.thread = Thread(target=self.cmdloop)
        self.thread.start()

    def wait_until_done(self):
        self.thread.join()
