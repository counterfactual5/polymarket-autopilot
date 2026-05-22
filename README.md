<div align="center">

# 🎯 Polymarket Autopilot

### The Python SDK Polymarket never shipped.

**Fetch markets. Place orders. Track positions.** All in pure Python.

Zero Dependencies · Polymarket CLOB API · EIP-712 Signing · 25+ API Endpoints

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Zero Deps](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](pyproject.toml)

[Installation](#installation) · [Market Data](#-fetch-market-data) · [Trading](#-place--manage-orders) · [API Reference](#api-reference)

</div>

---

## The Problem

Polymarket is the world's largest prediction market — but they don't offer a Python SDK. Their [official docs](https://docs.polymarket.com) show raw `curl` commands and JavaScript examples. If you want to build trading bots, analyze markets, or automate strategies in Python, you're on your own.

**polymarket-autopilot fills that gap.** One `pip install` gives you 25+ endpoints covering market data, trading, and portfolio management — pure Python, zero dependencies.

```
  Without this library:                    With this library:

  1. Read Polymarket API docs              1. pip install polymarket-autopilot
  2. Write HTTP client from scratch        2. from polymarket_autopilot.fetcher import search
  3. Implement EIP-712 signing             3. results = search("US election")
  4. Debug authentication headers
  5. Handle pagination manually            ✅ Done.
```

---

## Features

### 📊 Market Data (no auth required)

- **Events** — browse active, closed, featured events by volume and recency
- **Markets** — full market details or simplified lightweight listings
- **Search** — fuzzy search across all events and markets
- **Price History** — OHLCV candles at any interval (1m, 1h, 1d)
- **Orderbook** — full bid/ask depth for any outcome token
- **Spreads & Midpoints** — real-time pricing data
- **Open Interest** — market-wide position statistics
- **Leaderboard** — top traders by PnL
- **Tags & Series** — browse by category (politics, crypto, sports, etc.)
- **Trades** — recent fills filtered by market, maker, or taker

### ⚡ Trading (auth required)

- **Place Orders** — limit orders on any outcome with EIP-712 signing
- **Cancel Orders** — cancel single or all orders
- **View Positions** — current holdings across all markets
- **View Open Orders** — pending orders with optional market filter
- **Balance Check** — USDC balance query

### 🔧 Engineering

- **Zero dependencies** — pure Python stdlib (urllib, json, hashlib)
- **Pagination handled** — automatic cursor-based pagination for large result sets
- **Retry logic** — built-in retry with exponential backoff
- **Gzip support** — automatic decompression for faster responses
- **Type-annotated** — full type hints for IDE autocomplete

---

## Installation

```bash
# Market data only (zero deps)
pip install polymarket-autopilot

# Add trading support (eth-account for EIP-712 signing)
pip install "polymarket-autopilot[trading]"
```

That's it. No Node.js. No curl. No web3.py. Pure Python.

---

## Quick Start

### 📊 Fetch Market Data

```python
from polymarket_autopilot.fetcher import (
    fetch_events, search, fetch_price_history,
    fetch_orderbook, fetch_spread, resolve_market_token_id,
)
```

**Browse trending events:**

```python
events = fetch_events(limit=5)
for ev in events:
    print(f"  {ev['title']}")
    print(f"    Volume: ${ev.get('volume', 0):,.0f}")
    print(f"    Markets: {len(ev.get('markets', []))}")
```

```
  Will Bitcoin reach $150K by end of 2026?
    Volume: $12,450,000
    Markets: 2
  US Presidential Election 2028
    Volume: $8,320,000
    Markets: 5
  Will ETH flip BTC in market cap?
    Volume: $3,100,000
    Markets: 1
```

**Search for a market:**

```python
results = search("bitcoin 100k")
for market in results.get("markets", [])[:3]:
    print(f"  {market['question']}")
    print(f"    YES: {market.get('outcomePrices', ['?'])[0]}")
```

```
  Will Bitcoin reach $100,000 by December 2026?
    YES: 0.452
  Will Bitcoin be above $100K on June 1?
    YES: 0.381
  Bitcoin $100K end of year?
    YES: 0.417
```

**Get price history:**

```python
history = fetch_price_history("will-bitcoin-hit-100k", interval="1d")
for candle in history[-5:]:
    print(f"  {candle['timestamp']}  O:{candle['open']} H:{candle['high']} L:{candle['low']} C:{candle['close']}")
```

**Check the orderbook:**

```python
token_id = resolve_market_token_id("will-bitcoin-hit-100k", outcome_index=0)  # YES
book = fetch_orderbook(token_id)
spread = fetch_spread(token_id)
print(f"  Bid: {book['bids'][0]['price']}  Ask: {book['asks'][0]['price']}")
print(f"  Spread: {spread['spread']}")
```

### ⚡ Place & Manage Orders

```python
import os
from polymarket_autopilot.trading import PolymarketTrader, Order

# Configure via environment variables
# export POLYMARKET_API_KEY="..."
# export POLYMARKET_ADDRESS="0x..."
# export POLYMARKET_PRIVATE_KEY="..."  # via env var, never on disk

trader = PolymarketTrader.from_env()
```

**Buy YES on a market:**

```python
token_id = resolve_market_token_id("will-bitcoin-hit-100k", outcome_index=0)

order = Order(
    token_id=token_id,
    side="buy",       # "buy" or "sell"
    price=0.45,       # price in USDC (0-1 range for binary options)
    size=10,          # quantity in USDC
)

result = trader.place_order(order)
print(f"  Order ID: {result['orderID']}")
print(f"  Status: {result['status']}")
```

```
  Order ID: 12345678
  Status: LIVE
```

**Check your positions:**

```python
positions = trader.get_positions()
for pos in positions:
    print(f"  {pos.token_id[:10]}...  {pos.side} {pos.size} @ avg {pos.avg_price}")
```

**Manage open orders:**

```python
# View open orders
orders = trader.get_orders()
for o in orders:
    print(f"  {o['id']}: {o['side']} {o['original_size']} @ {o['price']}")

# Cancel a specific order
trader.cancel_order("12345678")

# Cancel all orders for a token
trader.cancel_all_orders(token_id=token_id)
```

---

## API Reference

### Market Data (no auth)

| Function | Endpoint | Description |
|---|---|---|
| `fetch_events()` | Gamma API | Browse events with filters (active, closed, featured) |
| `fetch_event_by_id()` | Gamma API | Get single event by ID |
| `fetch_event_by_slug()` | Gamma API | Get single event by URL slug |
| `fetch_markets()` | Gamma API | Browse markets with full details |
| `fetch_market_by_id()` | Gamma API | Get single market by ID |
| `fetch_market_by_slug()` | Gamma API | Get single market by URL slug |
| `fetch_simplified_markets()` | Gamma API | Lightweight market list (faster) |
| `search()` | Gamma API | Fuzzy search across events and markets |
| `fetch_event_tags()` | Gamma API | Tags for an event |
| `fetch_tags()` | Gamma API | All available tags/categories |
| `fetch_series()` | Gamma API | Market series/collections |
| `fetch_price_history()` | CLOB API | OHLCV price candles |
| `fetch_orderbook()` | CLOB API | Full bid/ask order book |
| `fetch_midpoint()` | CLOB API | Midpoint price for a token |
| `fetch_spread()` | CLOB API | Bid-ask spread |
| `fetch_trades()` | CLOB API | Recent trade fills |
| `fetch_open_interest()` | Data API | Open interest statistics |
| `fetch_leaderboard()` | Data API | Top traders by PnL |
| `resolve_market_token_id()` | — | Convert market slug → CLOB token ID |
| `fetch_all_snapshot()` | Multiple | Bulk snapshot of events + markets |

### Trading (auth required)

| Method | Description |
|---|---|
| `PolymarketTrader.from_env()` | Create trader from environment variables |
| `trader.place_order(order)` | Place a limit order (EIP-712 signed) |
| `trader.cancel_order(order_id)` | Cancel a specific order |
| `trader.cancel_all_orders(token_id?)` | Cancel all orders (optionally filtered) |
| `trader.get_orders(token_id?)` | List open orders |
| `trader.get_positions()` | List current positions |
| `trader.get_balance()` | Check USDC balance |

---

## Architecture

```
polymarket_autopilot/
├── fetcher/              Market data (no auth)
│   └── fetcher.py          25 endpoints — Gamma, CLOB, Data APIs
│       ├── Gamma API       Events, markets, tags, series, search
│       ├── CLOB API        Prices, orderbook, spreads, trades
│       └── Data API        Leaderboard, open interest
│
└── trading/              Authenticated trading
    └── trading.py          Order execution + portfolio management
        ├── Order           Limit order dataclass
        ├── Position        Position dataclass
        └── PolymarketTrader  Main trading client
            ├── EIP-712 signing (eth-account, optional)
            ├── Place / cancel orders
            └── Position & balance queries
```

```
Data Flow:

  User Code
     │
     ├── fetcher.search("bitcoin") ──→ Polymarket Gamma API ──→ Market list
     │                                                          │
     ├── fetcher.fetch_orderbook() ──→ Polymarket CLOB API ──→ Order book
     │                                                          │
     └── trader.place_order(order) ──→ EIP-712 Sign ──→ Polymarket CLOB ──→ ✅ Order placed
```

## Security

| Concern | How we handle it |
|---|---|
| Private keys | Environment variable only — never on disk, never logged |
| Order signing | In-process via eth-account — no external CLI, no IPC |
| API keys | Passed via env vars, not hardcoded or stored in config files |
| HTTP requests | urllib with gzip + retry — no third-party HTTP libraries |

```bash
# Required for trading
export POLYMARKET_API_KEY="your-api-key"
export POLYMARKET_ADDRESS="0x..."
export POLYMARKET_PRIVATE_KEY="0x..."  # via env var, never written to a file
```

## For AI Agent Developers

This library is designed as the execution backend for AI trading agents:

```python
# 1. Research   →  search markets, check prices and spreads
# 2. Analyze    →  fetch orderbook depth, price history, open interest
# 3. Decide     →  your model / strategy logic
# 4. Execute    →  place_order() with EIP-712 signing
# 5. Monitor    →  get_positions(), get_orders()
```

Works with [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Cursor](https://cursor.sh), [Codex](https://github.com/openai/codex), or any Python-capable agent.

## Development

```bash
pip install -e ".[trading]"
python -m pytest tests/ -v
```

## Roadmap

- [ ] Strategy framework (mean-reversion, momentum, convergence)
- [ ] Market analysis (probability trends, volume anomalies)
- [ ] Backtesting engine with historical data
- [ ] Arbitrage scanner (spread + cross-market)
- [ ] WebSocket support for real-time price feeds
- [ ] Async support (async/await)

## License

[MIT](LICENSE) — use it however you want.
