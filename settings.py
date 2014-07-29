
import json
import codecs

from os import path

DEFAULT_SETTINGS_FILE = "settings.json"

def GetSettings(settings_file=DEFAULT_SETTINGS_FILE):
    if not path.isfile(settings_file):
        with open(settings_file, 'w+') as file:
            file.write(json.dumps({
                'nickname': 'platinumshrimp',
                'realname': 'Platinum Shrimp',
                'username': 'banned',
                'servers': [{
                    'host': 'irc.chalmers.it',
                    'port': 6667,
                    'channels': [{'name': '#platinumshrimp'}]
                    }]
                }, ensure_ascii=True))
            #TODO: Prettify output
    def ascii_encode_dict(data):
        if type(data) == dict:
            return dict(map(ascii_encode_dict, pair) for pair in data.items())
        elif type(data) == unicode:
            return data.encode('ascii')
        else:
            return data
    settings = json.load(open(settings_file, 'r'), object_hook=ascii_encode_dict)
    #TODO: Verify settings, so all required fields are set
    return settings



