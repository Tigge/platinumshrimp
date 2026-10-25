import json
import logging
import math
from os import path

DEFAULT_SETTINGS_FILE = "settings.json"
DEFAULT_PLUGIN_WATCHDOG = {"timeout_seconds": 30, "max_restarts": 3}
DEFAULT_SETTINGS = {
    "nickname": "platinumshrimp",
    "realname": "Platinumshrimp",
    "username": "banned",
    "servers": {"chalmersit": {"host": "irc.chalmers.it", "port": 9999, "ssl": True}},
    "plugins": {"titlegiver": {}, "autojoiner": {"chalmersit": ["#platinumshrimp"]}},
    "plugin_watchdog": DEFAULT_PLUGIN_WATCHDOG.copy(),
}


def validate_settings(settings):
    if not settings:
        logging.error("No settings at all?")
        return False
    if not settings["nickname"] or not isinstance(settings["nickname"], str):
        logging.error("Settings is missing nickname field")
        return False
    if not settings["realname"] or not isinstance(settings["realname"], str):
        logging.error("Settings is missing realname field")
        return False
    if not settings["username"] or not isinstance(settings["username"], str):
        logging.error("Settings is missing username field")
        return False
    if not settings["servers"]:
        logging.error("Settings is missing servers?")
        return False
    for server, server_settings in settings["servers"].items():
        if not server:
            logging.error("Got empty server in server settings")
            return False
        if not isinstance(server, str):
            logging.error("Missing name for server")
            return False
        if not server_settings["host"] or not isinstance(server_settings["host"], str):
            logging.error("Got misconfigured host setting")
            return False
        if not server_settings["port"] or not isinstance(server_settings["port"], int):
            logging.error("Got misconfigured ip setting")
            return False
    if not settings["plugins"]:
        logging.error("Got no plugin, bot will be useless?")
        return False
    for plugin, plugin_settings in settings["plugins"].items():
        if not plugin:
            logging.error("Settings found empty plugin")
            return False
        if not isinstance(plugin, str):
            logging.error("Settings got plugin with no name")
            return False
    watchdog_settings = settings.get("plugin_watchdog", {})
    if not isinstance(watchdog_settings, dict):
        logging.error("Plugin watchdog settings must be an object")
        return False
    timeout = watchdog_settings.get("timeout_seconds", DEFAULT_PLUGIN_WATCHDOG["timeout_seconds"])
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or (isinstance(timeout, float) and not math.isfinite(timeout))
        or timeout <= 1
    ):
        logging.error("Plugin watchdog timeout_seconds must be a number greater than 1")
        return False
    max_restarts = watchdog_settings.get("max_restarts", DEFAULT_PLUGIN_WATCHDOG["max_restarts"])
    if isinstance(max_restarts, bool) or not isinstance(max_restarts, int) or max_restarts < 0:
        logging.error("Plugin watchdog max_restarts must be a non-negative integer")
        return False
    return True


def create_default_settings(settings_file):
    with open(settings_file, "w") as file:
        file.write(json.dumps(DEFAULT_SETTINGS, indent=2))


def load_settings(settings_file=DEFAULT_SETTINGS_FILE):
    if not path.isfile(settings_file):
        create_default_settings(settings_file)

    with open(settings_file, "r") as file:
        return json.load(file)


def save_settings(data, settings_file=DEFAULT_SETTINGS_FILE):
    with open(settings_file, "w") as file:
        return json.dump(data, file, indent=2)
