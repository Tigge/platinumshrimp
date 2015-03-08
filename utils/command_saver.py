import os.path
import shutil

from twisted.python import log

from utils import str_utils, file_utils


# The CommandSaver can be used for saving string parameter lists persistent
# between bot runs.
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
#        self.saver.read(lambda *args: self.privmsg(*args), 4)
#
#    def privmsg(self, server, user, channel, message):
#       # Do cool stuff with message
#       self.saver.save(server, user, channel, message)
#
# TODO: Enable customizable separator for commands as well.  Right now,
#       <new line> is always used, meaning that a saved string can't contain
#       a line separator itself.
# TODO: More extensive testing.
# TODO: Test different param_separators
#

class CommandSaver():
    def __init__(self, filename, param_separator = " ", command_separator = "\n"):
        self.filename = filename
        self.param_separator = param_separator
        self.command_separator = command_separator

    # Call read for emptying the saved file and feed the stored information
    # to a function callback.
    def read(self, callback, numargs):
        if os.path.isfile(self.filename):
            BACKUP = self.filename + ".backup"
            shutil.move(self.filename, BACKUP)
            with open(BACKUP, "r") as f:
                for line in f.read().split(self.command_separator):
                    try:
                        # Skip empty lines
                        if len(line) == 0:
                            continue
                        log.msg("Reading: " + line)
                        callback(*(str_utils.split(line, self.param_separator, numargs)))
                    except:
                        pass
        else:
            log.msg("Unable to open file {}, file does not exist".format(self.filename))

    # Note that if any argument (except for the last one) includes the same
    # combination of characters as is used as param_separator, it will make
    # reading and spliting parameters in read() fail.
    def save(self, *args):
        with open(self.filename, 'ab') as f:
            message = self.param_separator.join(args)
            log.msg("Saving: " + message)
            f.write(str_utils.sanitize_string(message) + self.command_separator)

    def remove(self, index):
        content_array = open(self.filename, 'r').read().split(self.command_separator)
        content_array.pop(index)
        content_array = filter(None, content_array)
        with open(self.filename, 'w') as f:
            f.write(self.command_separator.join(content_array) + self.command_separator)
#        file_utils.remove_line_in_file(self.filename, index)

