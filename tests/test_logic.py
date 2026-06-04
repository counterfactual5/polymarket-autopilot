"""Logic tests for polymarket_autopilot."""
import unittest
from unittest import mock

from polymarket_autopilot.fetcher.fetcher import _paginate, search
from polymarket_autopilot.trading.trading import Order, Position


# ---------------------------------------------------------------------------
# fetcher tests
# ---------------------------------------------------------------------------

class TestPaginate(unittest.TestCase):

    def test_paginate_single_page(self):
        """One page → returns all items, no extra calls."""
        mock_get = mock.MagicMock(return_value=[{"id": 1}, {"id": 2}])
        with mock.patch("polymarket_autopilot.fetcher.fetcher._get", mock_get):
            result = _paginate("https://example.com/api", page_size=100)
        self.assertEqual(len(result), 2)
        mock_get.assert_called_once()

    def test_paginate_max_results(self):
        """max_results=10 caps output even with more data."""
        large_page = [{"id": i} for i in range(100)]
        mock_get = mock.MagicMock(return_value=large_page)
        with mock.patch("polymarket_autopilot.fetcher.fetcher._get", mock_get):
            result = _paginate("https://example.com/api", page_size=50, max_results=10)
        self.assertEqual(len(result), 10)

    def test_paginate_multi_page(self):
        """Two pages → calls _get twice and merges."""
        mock_get = mock.MagicMock(side_effect=[
            [{"id": i} for i in range(5)],
            [{"id": i} for i in range(5, 8)],
        ])
        with mock.patch("polymarket_autopilot.fetcher.fetcher._get", mock_get):
            result = _paginate("https://example.com/api", page_size=5)
        self.assertEqual(len(result), 8)
        self.assertEqual(mock_get.call_count, 2)

    def test_paginate_empty(self):
        """Empty response → empty list."""
        mock_get = mock.MagicMock(return_value=[])
        with mock.patch("polymarket_autopilot.fetcher.fetcher._get", mock_get):
            result = _paginate("https://example.com/api")
        self.assertEqual(result, [])
        mock_get.assert_called_once()


class TestSearch(unittest.TestCase):

    def setUp(self):
        self.events = [
            {"title": "Will Bitcoin hit $200k in 2026?", "slug": "btc-200k", "description": "Bitcoin prediction"},
            {"title": "Ethereum ETF approved by July?", "slug": "eth-etf", "description": "ETH ETF"},
            {"title": "US GDP Q3 2026", "slug": "us-gdp", "description": "GDP forecast"},
        ]
        self.markets = [
            {"question": "Bitcoin $200k — YES", "slug": "btc-200k-yes", "description": "", "groupItemTitle": "BTC"},
            {"question": "Ethereum ETF — YES", "slug": "eth-etf-yes", "description": "", "groupItemTitle": "ETH"},
        ]

    def test_search_exact_match(self):
        """Exact query ranks high."""
        mock_get = mock.MagicMock(side_effect=[self.events, self.markets])
        with mock.patch("polymarket_autopilot.fetcher.fetcher._get", mock_get):
            result = search(query="Bitcoin", limit=5)
        self.assertIn("events", result)
        self.assertIn("markets", result)
        # "Bitcoin" should match the first event
        self.assertTrue(len(result["events"]) >= 1)

    def test_search_no_match(self):
        """Query with no matches returns empty."""
        mock_get = mock.MagicMock(side_effect=[self.events, self.markets])
        with mock.patch("polymarket_autopilot.fetcher.fetcher._get", mock_get):
            result = search(query="zzzUnlikelyQueryzzz", limit=5)
        self.assertEqual(result["events"], [])
        self.assertEqual(result["markets"], [])


# ---------------------------------------------------------------------------
# trading tests
# ---------------------------------------------------------------------------

class TestOrderModel(unittest.TestCase):

    def test_order_creation(self):
        order = Order(token_id="abc123", side="buy", price=0.55, size=10)
        self.assertEqual(order.token_id, "abc123")
        self.assertEqual(order.side, "buy")
        self.assertEqual(order.price, 0.55)
        self.assertEqual(order.size, 10)
        self.assertEqual(order.order_type, "limit")

    def test_order_defaults(self):
        order = Order(token_id="xyz", side="sell", price=0.3, size=5)
        self.assertEqual(order.client_order_id, None)
        self.assertEqual(order.nonce, None)


class TestPositionModel(unittest.TestCase):

    def test_position_creation(self):
        pos = Position(
            token_id="abc", side="long", size=100, average_price=0.5, unrealized_pnl=2.5
        )
        self.assertEqual(pos.size, 100)
        self.assertEqual(pos.unrealized_pnl, 2.5)

    def test_get_balance_error_handling(self):
        """get_balance catches errors gracefully."""
        from polymarket_autopilot.trading.trading import PolymarketTrader
        import urllib.error

        trader = PolymarketTrader(
            api_key="test-key",
            address="0x1234567890abcdef1234567890abcdef12345678",
        )

        with mock.patch("polymarket_autopilot.trading.trading._request",
                        side_effect=urllib.error.URLError("connection refused")):
            result = trader.get_balance()

        self.assertEqual(result["usdc_balance"], 0.0)
        self.assertIn("address", result)

    def test_get_positions_unit_conversion(self):
        """Position size/price converted from micro-units."""
        from polymarket_autopilot.trading.trading import PolymarketTrader

        trader = PolymarketTrader(
            api_key="test-key",
            address="0x1234567890abcdef1234567890abcdef12345678",
        )

        mock_response = {
            "positions": [{
                "tokenID": "tok1",
                "side": "buy",
                "size": "5000000",         # 5.0 shares
                "averagePrice": "550000",  # 0.55 USDC
                "unrealizedPnl": "10000",  # 0.01 USDC
            }]
        }
        with mock.patch("polymarket_autopilot.trading.trading._request",
                        return_value=mock_response):
            positions = trader.get_positions()

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].size, 5.0)
        self.assertEqual(positions[0].average_price, 0.55)
        self.assertEqual(positions[0].unrealized_pnl, 0.01)
