import unittest
from plugins.tyda.tyda import Tyda


class TestTyda(unittest.TestCase):
    def setUp(self):
        self.plugin = Tyda()

    def test_parse_translations_vårdpersonal(self):
        html = """
        <div class="list-translation-outer">
            <div class="item item-title"><span class="flag-small"><img src="/static/img/new_flags/v2/en.png" alt="Engelska" /></span></div>
            <ul class="list list-translations list-columns">
                <li class="item text">
                    <div class="item_div">
                        <a href="/search/nursing+staff">nursing staff</a>
                        &nbsp;<span class="trans-desc">[&nbsp;medicin&nbsp;]</span>
                    </div>
                </li>
                <li class="item text">
                    <div class="item_div">
                        <a href="/search/health+personnel">health personnel</a>
                        &nbsp;<span class="trans-desc">[&nbsp;medicin&nbsp;]</span>
                    </div>
                </li>
                <li class="item text">
                    <div class="item_div">
                        <a href="/search/care+staff">care staff</a>
                    </div>
                </li>
                <li class="item text">
                    <div class="item_div">
                        <a href="/search/nursing+auxiliaries">nursing auxiliaries</a>
                        &nbsp;<span class="trans-desc">[&nbsp;medicin&nbsp;]</span>
                    </div>
                </li>
            </ul>
        </div>
        """
        results = self.plugin._parse_translations(html)
        expected = [
            "nursing staff [ medicin ]",
            "health personnel [ medicin ]",
            "care staff nursing auxiliaries [ medicin ]",
        ]
        self.assertEqual(results, expected)

    def test_parse_translations_no_domain(self):
        html = """
        <div class="list-translation-outer">
            <ul class="list list-translations">
                <li class="item text">
                    <div class="item_div">
                        <a href="/search/nurse">nurse</a>
                    </div>
                </li>
            </ul>
        </div>
        """
        results = self.plugin._parse_translations(html)
        self.assertEqual(results, ["nurse"])


if __name__ == "__main__":
    unittest.main()
