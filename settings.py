
import json
import codecs

from os import path

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
                      'name': 'autojoin',
                      'settings': {
                        'chalmersit': ['#platinumshrimp']
                      }
                    }]
                }))
            # TODO: Prettify output

    def encode_dict(data):
        if type(data) == dict:
            return dict(map(encode_dict, pair) for pair in data.items())
        elif type(data) == unicode:
            return data.encode('utf-8')
        else:
            return data
    settings = json.load(open(settings_file, 'r'), object_hook=encode_dict)
    # TODO: Verify settings, so all required fields are set
    return settings



