import os

from twisted.trial import unittest

from utils.command_saver import CommandSaver

BASIC_COUNT_CONTENT = "[[0], [1], [2], [3]]"

class CommandSaverTest(unittest.TestCase):
    def prepare_test_file(self, content):
        filename = "test_file.save"
        with open(filename, 'w') as f:
            print>>f, content
        return filename

    def verify_content(self, filename, content):
        with open(filename, 'r') as f:
          self.assertEquals(f.read(), content)

    def test_basic_read(self):
        filename = self.prepare_test_file(BASIC_COUNT_CONTENT)
        saver = CommandSaver(filename)
        # Workaround for changing non-local variable in python 2:
        index = [0]
        def counter(i):
            self.assertEquals(index[0], int(i))
            index[0]+=1
        saver.read(counter)
        self.assertEquals(index[0], 4)
        self.assertFalse(os.path.isfile(filename))

    def test_basic_save(self):
        filename = "basic_save_test_file.save"
        saver = CommandSaver(filename)
        saver.save(0)
        saver.save(1)
        saver.save(2)
        saver.save(3)
        self.verify_content(filename, BASIC_COUNT_CONTENT)

    def test_basic_remove(self):
        filename = self.prepare_test_file(BASIC_COUNT_CONTENT)
        saver = CommandSaver(filename)
        saver.remove(2)
        self.verify_content(filename, "[[0], [1], [3]]")

