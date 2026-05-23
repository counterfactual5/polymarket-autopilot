# Contributing to polymarket-autopilot

## Setup

```bash
git clone https://github.com/counterfactual5/polymarket-autopilot.git
cd polymarket-autopilot
uv pip install -e ".[dev,trading]"
```

## Running Tests

```bash
uv run pytest tests/ -v
```

15 tests covering fetcher API, trading, order/position models, error handling, and pagination.

## Code Style

- Python 3.10+ compatible
- 120-char line length
- Public functions have docstrings
- Core package has zero dependencies (trading needs only eth-account)

## Project Structure

```
src/polymarket_autopilot/
├── fetcher/          # Market data: Gamma, CLOB, and Data APIs
│   └── fetcher.py    # 25+ endpoints
└── trading/          # Authenticated trading
    └── trading.py    # EIP-712 signing, order execution
```

## Pull Requests

1. Fork → feature branch → changes + tests → PR to `master`
2. Keep PRs focused — one concern per PR
