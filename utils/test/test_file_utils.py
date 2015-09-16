import os
import tempfile
import unittest
import shutil

from utils import file_utils


def generate_test_file(file_name):
    with open(file_name, 'w') as f:
        f.write('\n'.join(['0', 'I', 'II', 'III', 'IV', 'V']))


class TestStrUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp()
        cls.test_file = os.path.join(cls.folder, 'file_utils_test_file')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder)

    def assert_result(self, file_name, expected_result):
        with open(file_name, 'r') as f:
            self.assertEqual(f.read().splitlines(), expected_result)

    def test_remove_first_line(self):
        generate_test_file(self.test_file)
        file_utils.remove_line_in_file(self.test_file, 0)
        self.assert_result(self.test_file, ['I', 'II', 'III', 'IV', 'V'])

    def test_remove_last_line(self):
        generate_test_file(self.test_file)
        file_utils.remove_line_in_file(self.test_file, 5)
        self.assert_result(self.test_file, ['0', 'I', 'II', 'III', 'IV'])

    def test_remove_multiple_lines(self):
        generate_test_file(self.test_file)
        file_utils.remove_line_in_file(self.test_file, 1)
        self.assert_result(self.test_file, ['0', 'II', 'III', 'IV', 'V'])
        file_utils.remove_line_in_file(self.test_file, 2)
        self.assert_result(self.test_file, ['0', 'II', 'IV', 'V'])

