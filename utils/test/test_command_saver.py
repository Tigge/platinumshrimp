import os
import unittest

from utils.command_saver import CommandSaver

BASIC_COUNT_CONTENT = "[[0], [1], [2], [3]]"
DOUBLE_COUNT_CONTENT = "[[0, 1], [1, 2], [2, 3]]"


class CommandSaverTest(unittest.TestCase):
    def prepare_test_file(self, content):
        filename = "test_file.save"
        with open(filename, 'w') as f:
            f.write(content)
        return filename

    def verify_content(self, filename, content):
        with open(filename, 'r') as f:
            self.assertEqual(f.read(), content)

    def test_basic_read(self):
        filename = self.prepare_test_file(BASIC_COUNT_CONTENT)
        saver = CommandSaver(filename)
        index = 0

        def counter(i):
            nonlocal index
            self.assertEqual(index, i)
            index += 1
        saver.read(counter)
        self.assertEqual(index, 4)
        self.assertFalse(os.path.isfile(filename))

    def test_basic_save(self):
        filename = "basic_save_test_file.save"
        os.remove(filename)
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
        saver.remove(0)
        self.verify_content(filename, "[[1], [3]]")
        saver.remove(1)
        self.verify_content(filename, "[[1]]")
        saver.remove(0)
        self.verify_content(filename, "[]")
        # And try removing out of index, just to make sure we don't crash:
        saver.remove(0)
        self.verify_content(filename, "[]")

    def test_basic_remove_item(self):
        filename = self.prepare_test_file(BASIC_COUNT_CONTENT)
        saver = CommandSaver(filename)
        # Start by trying to remove something that doesn't exist, and
        # something with too many parameters:
        saver.remove_item(4)
        self.verify_content(filename, BASIC_COUNT_CONTENT)
        saver.remove_item(0, 1)
        self.verify_content(filename, BASIC_COUNT_CONTENT)
        saver.remove_item(2)
        self.verify_content(filename, "[[0], [1], [3]]")
        saver.remove_item(1)
        self.verify_content(filename, "[[0], [3]]")
        saver.remove_item(3)
        self.verify_content(filename, "[[0]]")
        saver.remove_item(0)
        self.verify_content(filename, "[]")
        # And try removing a non-existng item, just to make sure we don't crash:
        saver.remove_item(0)
        self.verify_content(filename, "[]")

    # Make sure we're able to repeat a read if we save in the read callback
    def test_read_with_save(self):
        filename = self.prepare_test_file(BASIC_COUNT_CONTENT)
        saver = CommandSaver(filename)
        # Workaround for changing non-local variable in python 2:
        index = [0]
        def counter(i):
            self.assertEquals(index[0], i)
            index[0] += 1
            saver.save(i)
        saver.read(counter)
        self.assertEquals(index[0], 4)
        index = [0]
        saver.read(counter)
        self.assertEquals(index[0], 4)

    # Make sure we're able to call read with multiple parameters in one callback
    def test_double_read(self):
        filename = self.prepare_test_file(DOUBLE_COUNT_CONTENT)
        saver = CommandSaver(filename)
        index = 0

        def counter(i, j):
            nonlocal index
            self.assertEqual(index, i)
            self.assertEqual(i + 1, j)
            index += 1
        saver.read(counter)
        self.assertEqual(index, 3)
        self.assertFalse(os.path.isfile(filename))

    # Make sure we don't get any half reads when we give a callback with
    # too few parameters
    def test_double_read_too_few_parameters(self):
        filename = self.prepare_test_file(DOUBLE_COUNT_CONTENT)
        saver = CommandSaver(filename)
        index = 0

        def counter(i):
            nonlocal index
            index += 1
        saver.read(counter)
        self.assertEqual(index, 0, "Got read call with too few parameters")

    def test_double_remove(self):
        filename = self.prepare_test_file(DOUBLE_COUNT_CONTENT)
        saver = CommandSaver(filename)
        saver.remove(1)
        self.verify_content(filename, "[[0, 1], [2, 3]]")
        saver.remove(1)
        self.verify_content(filename, "[[0, 1]]")
        saver.remove(0)
        self.verify_content(filename, "[]")
        # And try removing out of index, just to make sure we don't crash:
        saver.remove(0)
        self.verify_content(filename, "[]")

    def test_double_remove_item(self):
        filename = self.prepare_test_file(DOUBLE_COUNT_CONTENT)
        saver = CommandSaver(filename)
        # Start by trying to remove something that doesn't exist, and something
        # with the wrong amount of parameters:
        saver.remove_item([1, 1])
        self.verify_content(filename, DOUBLE_COUNT_CONTENT)
        saver.remove_item(0)
        self.verify_content(filename, DOUBLE_COUNT_CONTENT)
        saver.remove_item(1, 2)
        self.verify_content(filename, "[[0, 1], [2, 3]]")
        saver.remove_item(0, 1)
        self.verify_content(filename, "[[2, 3]]")
        saver.remove_item(2, 3)
        self.verify_content(filename, "[]")
        # And try removing something again, just to make sure we don't crash:
        saver.remove_item(2, 3)
        self.verify_content(filename, "[]")

    def test_double_save(self):
        filename = "double_save_test_file.save"
        os.remove(filename)
        saver = CommandSaver(filename)
        saver.save(0, 1)
        saver.save(1, 2)
        saver.save(2, 3)
        self.verify_content(filename, DOUBLE_COUNT_CONTENT)

