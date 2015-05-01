import json
import os.path
import shutil

from twisted.python import log

from utils.json_utils import read_json


# The CommandSaver can be used for saving string parameter lists persistent
# between bot runs.
#
# Note that the CommandSaver is NOT thread safe!
#
# Here's an example of using the CommandSaver for saving commands sent
# to a plugin using privmsg.  These commands will be saved to a SAVE_FILE
# and the plugin will receive the same commands the next time the bot
# starts up:
#
#  class ExamplePlugin(plugin.Plugin): 
#    def __init__(self):
#       self.saver = command_saver.CommandSaver(SAVE_FILE)
#
#    def started(self, settings):
#        self.saver.read(lambda *args: self.privmsg(*args))
#
#    def privmsg(self, server, user, channel, message):
#       # Do cool stuff with message
#       self.saver.save(server, user, channel, message)
#


class CommandSaver():
    def __init__(self, filename):
        self.filename = filename

    # Call read for emptying the saved file and feed the stored information
    # to a function callback.
    def read(self, callback):
        if os.path.isfile(self.filename):
            BACKUP = self.filename + ".backup"
            shutil.move(self.filename, BACKUP)
            data = read_json(BACKUP) or []
            for line in data:
                try:
                    callback(*line)
                except Exception,e:
                    log.err("Error while reading: " + str(e))
        else:
            log.err("Unable to open file {}, file does not exist".format(self.filename))

    # Note that if any argument (except for the last one) includes the same
    # combination of characters as is used as param_separator, it will make
    # reading and spliting parameters in read() fail.
    def save(self, *args):
        data = read_json(self.filename) or []
        data.append(args)
        with open(self.filename, 'w+') as file:
            file.write(json.dumps(data))

    # This will remove a single item matching the arguments given.
    # Note that this has to be an exact match for the item to be removed
    def remove_item(self, *args):
        data = read_json(self.filename) or []
        try:
          data.remove(list(args))
        except:
          log.err("Can't remove " + str(list(args)) + " from " + str(data))
        with open(self.filename, 'w+') as file:
            file.write(json.dumps(data))

    def remove(self, index):
        data = read_json(self.filename) or []
        if index >= len(data):
            log.err("Trying to remove something out of index? size: {}, index: {}".format(len(data), index))
            return
        del data[index]
        with open(self.filename, 'w+') as file:
            file.write(json.dumps(data))

