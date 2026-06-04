"""Tests for polymarket_autopilot.fetcher."""

import unittest


class TestFetcherImports(unittest.TestCase):
    """Verify all public symbols are importable."""

    def test_import_fetcher_package(self):
        from polymarket_autopilot.fetcher import (
            GAMMA_BASE,
            CLOB_BASE,
            DATA_BASE,
        )
        self.assertTrue(GAMMA_BASE.startswith("https://"))
        self.assertTrue(CLOB_BASE.startswith("https://"))
        self.assertTrue(DATA_BASE.startswith("https://"))

    def test_search_empty(self):
        from polymarket_autopilot.fetcher import search

        result = search("")
        self.assertEqual(result, {"events": [], "markets": [], "profiles": []})


if __name__ == "__main__":
    unittest.main()
