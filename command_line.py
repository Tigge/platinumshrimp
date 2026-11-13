import asyncio
import cmd
import math
import os
import signal
import time
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
        if not self.bot.plugins and not self.bot.unhealthy_plugins:
            print("No plugins loaded.")
            return
        for plugin in self.bot.plugins:
            restart_count = self.bot.plugin_restart_counts.get(plugin.name, 0)
            print(
                f"{plugin.name} (PID: {plugin.pid}, status: {plugin.state}, "
                f"automatic restarts: {restart_count}/{self.bot.plugin_max_restarts})"
            )
        for name, reason in self.bot.unhealthy_plugins.items():
            print(f"{name} (unhealthy: {reason})")

    def _snapshot_for_cli(self):
        loop = getattr(self.bot, "loop", None)
        if loop is not None and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.bot.get_status_snapshot(), loop)
            return future.result(timeout=1)
        return self.bot._build_snapshot()

    @staticmethod
    def _format_memory(value):
        if value is None:
            return "n/a"
        return f"{value:.1f} MiB"

    @staticmethod
    def _format_seconds(value):
        if value is None:
            return "n/a"
        if value < 60:
            return f"{value:.0f}s"
        if value < 3600:
            minutes, seconds = divmod(value, 60)
            return f"{minutes:.0f}m {seconds:.0f}s"
        hours, remainder = divmod(value, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:.0f}h {minutes:.0f}m"

    def _render_overview(self, snapshot):
        bot = snapshot["bot"]
        plugins = snapshot["plugins"] or []
        servers = snapshot["servers"] or []

        print(
            f"Bot: pid={bot['pid']} uptime={self._format_seconds(bot['uptime_seconds'])} "
            f"mem={self._format_memory(bot['memory_mb'])}"
        )
        print(
            f"{'Plugin':<18} {'State':<11} {'HB Age':>8} {'Restarts':>8} "
            f"{'Memory':>10} {'Reason':<20}"
        )
        if not plugins:
            print("(no plugins loaded)")
        for plugin in plugins:
            reason = plugin.get("failure_reason") or "-"
            print(
                f"{plugin['name']:<18} {plugin['state']:<11} "
                f"{self._format_seconds(plugin['heartbeat_age']):>8} "
                f"{plugin['restart_count']:>8} {self._format_memory(plugin['memory_mb']):>10} "
                f"{reason:<20}"
            )

        print()
        print(f"{'Server':<18} {'State':<10} {'Host':<20} {'Channels'}")
        if not servers:
            print("(no servers configured)")
        for server in servers:
            host = server.get("host") or "-"
            status = "connected" if server.get("connected") else "disconnected"
            channels = ", ".join(server.get("channels", [])) if server.get("channels") else "-"
            print(f"{server['name']:<18} {status:<10} {host:<20} {channels}")

    def do_overview(self, arg):
        """Show a compact health overview for the bot and plugins."""
        refresh_seconds = arg.strip()
        if refresh_seconds:
            try:
                refresh_seconds = float(refresh_seconds)
            except ValueError:
                print("Usage: overview [seconds]")
                return
            if not math.isfinite(refresh_seconds) or refresh_seconds < 0:
                print("Usage: overview [seconds]")
                return
        else:
            refresh_seconds = None

        while True:
            snapshot = self._snapshot_for_cli()
            self._render_overview(snapshot)
            if refresh_seconds is None:
                return
            if refresh_seconds == 0:
                return
            try:
                time.sleep(refresh_seconds)
            except KeyboardInterrupt:
                print()
                return

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

        async def _unload():
            if await self.bot.unload_plugin(name):
                print(f"Plugin '{name}' unloaded.")
            else:
                print(f"Plugin '{name}' not found.")

        # Schedule _unload on the bot's main asyncio loop
        future = asyncio.run_coroutine_threadsafe(_unload(), self.bot.loop)
        try:
            future.result()
        except Exception as e:
            print(f"Error unloading plugin '{name}': {e}")

    # A lot of commands share auto complete so let's override the default instead of individuals
    def completedefault(self, text, line, start_index, end_index):
        args = line.split(" ")

        if args[0] in ["unload_plugin", "reload_plugin"] and self.bot.plugins:
            return [plugin.name for plugin in self.bot.plugins if plugin.name.startswith(text)]

        # Exit early for commands with no auto-complete
        if not args[0] in ["send_message", "list_channels", "part_channel", "join_channel"]:
            return

        if len(args) < 3:  # Complete server names
            return [s + " " for s in self.bot.servers if s.startswith(text)]
        elif len(args) == 3:  # Complete channel names
            if args[1] not in self.bot.servers:
                return
            server = self.bot.servers[args[1]]
            return [c + " " for c in getattr(server, "channels", set()) if c.startswith(args[2])]

    # Override the emptyline function to avoid the default of repeating the last command
    def emptyline(self):
        pass

    # Let's exit the bot on EOF (aka ctrl+d)
    def do_EOF(self, _):
        print("")  # Just to make a new line
        return self.do_exit(_)

    def start(self):
        self.thread = Thread(target=self.cmdloop)
        self.thread.start()

    def wait_until_done(self):
        self.thread.join()
