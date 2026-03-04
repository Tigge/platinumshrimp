import os
import unittest
import unittest.mock
import requests
from plugins.wolfram import wolfram


class WolframTest(unittest.TestCase):
    def setUp(self):
        # Path to test directory relative to project root
        self.test_dir = os.path.join("plugins", "wolfram", "test")

    def _get_test_content(self, filename):
        with open(os.path.join(self.test_dir, filename), "r") as f:
            return f.read()

    @unittest.mock.patch("requests.get")
    def test_population_france(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.ok = True
        mock_response.content = self._get_test_content("population_france.xml").encode("utf-8")
        mock_get.return_value = mock_response

        answer = wolfram.get_answer("population france", "dummy_key")
        self.assertEqual(answer, "66.4 million people (world rank: 23rd) (2023 estimate)")

    @unittest.mock.patch("requests.get")
    def test_sweden_population_minus_finland(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.ok = True
        mock_response.content = self._get_test_content(
            "Sweden_population_minus_Finland_population.xml"
        ).encode("utf-8")
        mock_get.return_value = mock_response

        answer = wolfram.get_answer("Sweden population minus Finland population", "dummy_key")
        self.assertEqual(answer, "5 million people (2023 estimates)")

    @unittest.mock.patch("requests.get")
    def test_number_of_atoms_in_universe(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.ok = True
        mock_response.content = self._get_test_content("Number_of_atoms_in_universe.xml").encode(
            "utf-8"
        )
        mock_get.return_value = mock_response

        answer = wolfram.get_answer("Number of atoms in universe", "dummy_key")
        self.assertEqual(answer, "≈ 6×10^79 atoms")

    @unittest.mock.patch("requests.get")
    def test_molar_mass_water_vs_coffeine(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.ok = True
        mock_response.content = self._get_test_content(
            "molar_mass_of_water_vs_coffeine.xml"
        ).encode("utf-8")
        mock_get.return_value = mock_response

        answer = wolfram.get_answer("molar mass of water vs coffeine", "dummy_key")
        # Note: sanitize_string replaces newlines with spaces
        expected = "water | 18.015 g/mol (grams per mole) caffeine | 194.19 g/mol (grams per mole)"
        self.assertEqual(answer, expected)

    @unittest.mock.patch("requests.get")
    def test_failed_response(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.ok = False
        mock_get.return_value = mock_response

        answer = wolfram.get_answer("any query", "dummy_key")
        self.assertIsNone(answer)

    @unittest.mock.patch("requests.get")
    def test_malformed_xml(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.ok = True
        mock_response.content = b"<invalid>xml"
        mock_get.return_value = mock_response

        answer = wolfram.get_answer("any query", "dummy_key")
        self.assertIsNone(answer)


if __name__ == "__main__":
    unittest.main()
