"""Tests for polymarket_autopilot.trading."""

import unittest
import os


class TestTradingImports(unittest.TestCase):
    """Verify public symbols are importable."""

    def test_import_dataclasses(self):
        from polymarket_autopilot.trading import Order, Position

        order = Order(token_id="abc", side="buy", price=0.5, size=10)
        self.assertEqual(order.side, "buy")
        self.assertEqual(order.price, 0.5)

        pos = Position(
            token_id="abc", side="long", size=10, average_price=0.5, unrealized_pnl=1.0
        )
        self.assertEqual(pos.unrealized_pnl, 1.0)

    def test_from_env_raises_without_vars(self):
        from polymarket_autopilot.trading import PolymarketTrader

        # Remove env vars to ensure clean state
        env_keys = ["POLYMARKET_API_KEY", "POLYMARKET_ADDRESS", "POLYMARKET_PRIVATE_KEY"]
        saved = {k: os.environ.pop(k, None) for k in env_keys}
        try:
            with self.assertRaises(KeyError):
                PolymarketTrader.from_env()
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

if __name__ == "__main__":
    unittest.main()
