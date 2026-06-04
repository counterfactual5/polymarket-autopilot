"""Tests for Polymarket market-data snapshot validation."""
import unittest
from decimal import Decimal

from polymarket_autopilot.market_snapshot import (
    MarketDataError,
    SnapshotCheck,
    assert_tradeable_snapshot,
    validate_market_snapshot,
)


def _book(bid="0.52", ask="0.54"):
    return {
        "bids": [{"price": bid, "size": "100"}, {"price": "0.50", "size": "50"}],
        "asks": [{"price": ask, "size": "80"}, {"price": "0.56", "size": "30"}],
    }


class TestValidate(unittest.TestCase):
    def test_healthy(self):
        c = validate_market_snapshot("tok", _book(), mid="0.53")
        self.assertTrue(c.ok)
        self.assertEqual(c.best_bid, Decimal("0.52"))
        self.assertEqual(c.best_ask, Decimal("0.54"))

    def test_picks_best_levels_regardless_of_order(self):
        book = {
            "bids": [{"price": "0.40", "size": "1"}, {"price": "0.52", "size": "1"}],
            "asks": [{"price": "0.60", "size": "1"}, {"price": "0.54", "size": "1"}],
        }
        c = validate_market_snapshot("tok", book)
        self.assertEqual(c.best_bid, Decimal("0.52"))
        self.assertEqual(c.best_ask, Decimal("0.54"))

    def test_price_outside_unit_interval(self):
        c = validate_market_snapshot("tok", _book(), mid="1.5")
        self.assertFalse(c.ok)
        self.assertTrue(any("outside (0,1)" in r for r in c.reasons))

    def test_empty_book(self):
        c = validate_market_snapshot("tok", {"bids": [], "asks": []})
        self.assertFalse(c.ok)
        self.assertTrue(any("no bid" in r for r in c.reasons))
        self.assertTrue(any("no ask" in r for r in c.reasons))

    def test_crossed_book(self):
        c = validate_market_snapshot("tok", _book(bid="0.60", ask="0.40"))
        self.assertFalse(c.ok)
        self.assertTrue(any("crossed" in r for r in c.reasons))

    def test_spread_too_wide(self):
        book = {"bids": [{"price": "0.20", "size": "1"}], "asks": [{"price": "0.80", "size": "1"}]}
        c = validate_market_snapshot("tok", book)
        self.assertFalse(c.ok)
        self.assertTrue(any("too wide" in r for r in c.reasons))

    def test_mid_diverges(self):
        c = validate_market_snapshot("tok", _book(), mid="0.90")
        self.assertFalse(c.ok)
        self.assertTrue(any("diverges" in r for r in c.reasons))

    def test_edge_prices_zero_one_rejected(self):
        book = {"bids": [{"price": "0", "size": "1"}], "asks": [{"price": "1", "size": "1"}]}
        c = validate_market_snapshot("tok", book)
        self.assertFalse(c.ok)
        self.assertTrue(any("outside (0,1)" in r for r in c.reasons))


class TestAssert(unittest.TestCase):
    def test_passes(self):
        c = assert_tradeable_snapshot("tok", _book(), mid="0.53")
        self.assertIsInstance(c, SnapshotCheck)

    def test_raises(self):
        with self.assertRaises(MarketDataError):
            assert_tradeable_snapshot("tok", {"bids": [], "asks": []})

    def test_as_dict(self):
        d = validate_market_snapshot("tok", _book(), mid="0.53").as_dict()
        self.assertEqual(d["best_bid"], "0.52")
        self.assertEqual(d["token_id"], "tok")


if __name__ == "__main__":
    unittest.main()
