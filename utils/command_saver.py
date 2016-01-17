import json
import os
import logging

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

    def read_json(self, filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except IOError:
            return []

    # Call read for emptying the saved file and feed the stored information
    # to a function callback.
    def read(self, callback):
        if os.path.isfile(self.filename):
            BACKUP = self.filename + ".backup"
            # On Linux, os.rename will silently overwrite, but that is not the
            # case on Windows, so just remove the old backup if it exists:
            if os.path.isfile(BACKUP):
                os.remove(BACKUP)
            os.rename(self.filename, BACKUP)
            if os.path.isfile(self.filename):
                log.err("os.rename did not move file, removing it manually")
                os.remove(self.filename)
            data = self.read_json(BACKUP)
            for line in data:
                try:
                    callback(*line)
                except:
                    logging.error("Error while reading.  Not the right amount of parameters maybe?")
        else:
            logging.error("Unable to open file %s, file does not exist", self.filename)

    def save(self, *args):
        data = self.read_json(self.filename)
        data.append(args)
        with open(self.filename, 'w+') as file:
            file.write(json.dumps(data))

    # This will remove a single item matching the arguments given.
    # Note that this has to be an exact match for the item to be removed
    def remove_item(self, *args):
        data = self.read_json(self.filename)
        try:
            data.remove(list(args))
        except:
            logging.error("Can't remove %s from %s", list(args), data)
        with open(self.filename, 'w+') as file:
            file.write(json.dumps(data))

    def remove(self, index):
        data = self.read_json(self.filename)
        if index >= len(data):
            logging.error("Trying to remove something out of index? size: %d, index: %d", len(data), index)
            return
        del data[index]
        with open(self.filename, 'w+') as file:
            file.write(json.dumps(data))

