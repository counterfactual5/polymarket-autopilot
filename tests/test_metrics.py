"""Tests for drawdown / leaderboard metrics."""
import unittest
from decimal import Decimal

from polymarket_autopilot.metrics import (
    drawdown_series,
    max_drawdown,
    rank_drawdown_leaderboard,
)


class TestDrawdown(unittest.TestCase):
    def test_rising_zero(self):
        self.assertEqual(drawdown_series([100, 110, 120]), [Decimal("0")] * 3)

    def test_decline(self):
        self.assertEqual(drawdown_series([100, 80])[1], Decimal("20"))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            max_drawdown([])

    def test_max_dd(self):
        stats = max_drawdown([100, 80, 60, 80])
        self.assertEqual(stats.max_drawdown_pct, Decimal("40"))
        self.assertEqual(stats.current_drawdown_pct, Decimal("20"))
        self.assertFalse(stats.recovered)

    def test_recovered(self):
        stats = max_drawdown([100, 70, 130])
        self.assertEqual(stats.current_drawdown_pct, Decimal("0"))
        self.assertTrue(stats.recovered)

    def test_as_dict(self):
        d = max_drawdown([100, 80]).as_dict()
        self.assertEqual(d["max_drawdown_pct"], "20")


class TestLeaderboard(unittest.TestCase):
    def test_ranks(self):
        board = rank_drawdown_leaderboard({
            "steady": [100, 99, 101, 105],
            "volatile": [100, 50, 120],
            "moderate": [100, 90, 110],
        })
        self.assertEqual([e.name for e in board], ["steady", "moderate", "volatile"])

    def test_tie_break(self):
        board = rank_drawdown_leaderboard({
            "a": [100, 90, 100],
            "b": [100, 90, 130],
        })
        self.assertEqual(board[0].name, "b")

    def test_serialize(self):
        d = rank_drawdown_leaderboard({"x": [100, 80]})[0].as_dict()
        self.assertEqual(d["rank"], 1)
        self.assertEqual(d["final_equity"], "80")


if __name__ == "__main__":
    unittest.main()
