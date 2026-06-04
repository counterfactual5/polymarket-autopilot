# Changelog

## [0.6.0] — 2026-06-05

### Added
- **Market snapshot validation** (`market_snapshot.py`): Polymarket-specific CLOB
  sanity checks — prices in (0,1), crossed-book detection, spread limits, mid-price
  divergence guard. Raises `MarketDataError` on degenerate/stale snapshots.
- **Drawdown metrics** (`metrics.py`): venue-agnostic `drawdown_series`,
  `max_drawdown`, `rank_drawdown_leaderboard` for equity-curve analysis.

## [0.1.0] — 2026-05-23

### Added
- Market data fetcher: 25+ endpoints covering Gamma, CLOB, and Data APIs
- Event/market browsing with pagination, filtering, and search
- Price history (OHLCV), orderbook depth, spreads, and midpoints
- Order execution: limit orders with EIP-712 signing (optional eth-account)
- Position tracking, order management, and balance queries
- Strategy framework: mean-reversion, momentum, convergence
- Zero-dependency core (trading extra is opt-in)
- 15 tests covering fetcher, trading, models, and error handling
- GitHub Actions CI (Python 3.10, 3.11, 3.12)
- MIT License

[0.1.0]: https://github.com/counterfactual5/polymarket-autopilot/releases/tag/v0.1.0
