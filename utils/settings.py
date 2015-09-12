import json
import logging
from os import path


DEFAULT_SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
        'nickname': 'platinumshrimp',
        'realname': 'Platinumshrimp',
        'username': 'banned',
        'servers': [{
            'name': 'chalmersit',
            'host': 'irc.chalmers.it',
            'port': 9999,
            'ssl': True
        }],
        'plugins': [
            {
                'name': 'titlegiver',
                'settings': ''
            },
            {
                'name': 'invitejoiner',
                'settings': ''
            },
            {
                'name': 'autojoiner',
                'settings': { 'chalmersit': ['#platinumshrimp'] }
            }
        ]
    }


def validate_settings(settings):
    if not settings:
        logging.error("No settings at all?")
        return False
    if not settings['nickname'] or not isinstance(settings['nickname'], str):
        logging.error("Settings is missing nickname field")
        return False
    if not settings['realname'] or not isinstance(settings['realname'], str):
        logging.error("Settings is missing realname field")
        return False
    if not settings['username'] or not isinstance(settings['username'], str):
        logging.error("Settings is missing username field")
        return False
    if not settings['servers']:
        logging.error("Settings is missing servers?")
        return False
    for server in settings['servers']:
        if not server:
            logging.error("Got empty server in server settings")
            return False
        if not server['name'] or not isinstance(server['name'], str):
            logging.error("Missing name for server")
            return False
        if not server['host'] or not isinstance(server['host'], str):
            logging.error("Got misconfigured host setting")
            return False
        if not server['port'] or not isinstance(server['port'], int):
            logging.error("Got misconfigured ip setting")
            return False
    if not settings['plugins']:
        logging.error("Got no plugin, bot will be useless?")
        return False
    for plugin in settings['plugins']:
        if not plugin:
            logging.error("Settings found empty plugin")
            return False
        if not plugin['name'] or not isinstance(plugin['name'], str):
            logging.error("Settings got plugin with no name")
            return False
    return True


def create_default_settings(settings_file):
    with open(settings_file, 'w') as file:
        file.write(json.dumps(DEFAULT_SETTINGS, indent=2))


def get_settings(settings_file=DEFAULT_SETTINGS_FILE):
    if not path.isfile(settings_file):
        create_default_settings(settings_file)

    with open(settings_file, 'r') as file:
        return json.load(file)

