from twisted.trial import unittest

from utils import file_utils

TEST_FILE = 'file_utils_test_file'

def generate_test_file(file_name):
    with open(file_name, 'w') as f:
        f.write('\n'.join(['0', 'I', 'II', 'III', 'IV', 'V']))

class TestStrUtils(unittest.TestCase):

    def assert_result(self, file_name, expected_result):
        with open(file_name, 'r') as f:
            self.assertEquals(f.read().splitlines(), expected_result)

    def test_remove_first_line(self):
        generate_test_file(TEST_FILE)
        file_utils.remove_line_in_file(TEST_FILE, 0)
        self.assert_result(TEST_FILE, ['I', 'II', 'III', 'IV', 'V'])

    def test_remove_last_line(self):
        generate_test_file(TEST_FILE)
        file_utils.remove_line_in_file(TEST_FILE, 5)
        self.assert_result(TEST_FILE, ['0', 'I', 'II', 'III', 'IV'])

    def test_remove_multiple_lines(self):
        generate_test_file(TEST_FILE)
        file_utils.remove_line_in_file(TEST_FILE, 1)
        self.assert_result(TEST_FILE, ['0', 'II', 'III', 'IV', 'V'])
        file_utils.remove_line_in_file(TEST_FILE, 2)
        self.assert_result(TEST_FILE, ['0', 'II', 'IV', 'V'])

