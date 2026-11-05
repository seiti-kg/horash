import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import vt_incognito  # noqa: E402


class NormalizeInputTests(unittest.TestCase):
    def test_hash_is_lowercased_and_converted_to_vt_url(self):
        result = vt_incognito.normalize_input("A" * 64)
        self.assertEqual(result, vt_incognito.VT_URL.format(hash="a" * 64))

    def test_https_url_is_accepted(self):
        url = "https://www.virustotal.com/gui/file/" + "b" * 64
        self.assertEqual(vt_incognito.normalize_input(url), url)

    def test_http_url_with_host_is_accepted(self):
        self.assertEqual(vt_incognito.normalize_input("http://example.com/x"), "http://example.com/x")

    def test_test_string_is_rejected(self):
        with self.assertRaises(ValueError):
            vt_incognito.normalize_input("test")

    def test_short_string_is_rejected(self):
        with self.assertRaises(ValueError):
            vt_incognito.normalize_input("abc")

    def test_non_hex_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            vt_incognito.normalize_input("g" * 64)

    def test_non_http_scheme_is_rejected(self):
        for value in ("ftp://example.com/x", "javascript:alert(1)", "file:///C:/x"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                vt_incognito.normalize_input(value)

    def test_http_without_host_is_rejected(self):
        with self.assertRaises(ValueError):
            vt_incognito.normalize_input("http://")


if __name__ == "__main__":
    unittest.main()
