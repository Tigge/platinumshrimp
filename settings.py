
import json
import codecs
from os import path

from utils.json_utils import read_json

DEFAULT_SETTINGS_FILE = "settings.json"


def get_settings(settings_file=DEFAULT_SETTINGS_FILE):
    if not path.isfile(settings_file):
        with open(settings_file, 'w+') as file:
            file.write(json.dumps({
                'nickname': 'platinumshrimp',
                'realname': 'Platinumshrimp',
                'username': 'banned',
                'servers': [{
                    'name': 'chalmersit',
                    'host': 'irc.chalmers.it',
                    'port': 6667,
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
                      'settings': {
                        'chalmersit': ['#platinumshrimp']
                      }
                    }]
                }, indent=2))
    settings = read_json(settings_file)
    # TODO: Verify settings, so all required fields are set
    return settings



