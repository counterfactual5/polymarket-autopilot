"""
Mean-Reversion Strategy Example for Polymarket.

Demonstrates a simple mean-reversion signal using Polymarket's CLOB
orderbook data. The core idea: when the orderbook mid-price deviates
from a rolling average, it may revert.

Usage::

    python examples/mean_reversion.py

Warning: This is a **demo** — does NOT place real orders. For
educational / research purposes only.
"""

from polymarket_autopilot.fetcher.fetcher import (
    fetch_events,
    fetch_midpoint,
    fetch_spread,
    fetch_price_history,
)


def compute_simple_moving_average(prices: list[float], window: int = 20) -> float | None:
    """Return SMA of the last `window` prices."""
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def mean_reversion_signal(
    mid_price: float,
    sma: float,
    threshold_pct: float = 2.0,
) -> dict:
    """
    Generate a mean-reversion signal.

    Returns dict with:
      - signal: "BUY" | "SELL" | "HOLD"
      - deviation_pct: how far mid is from SMA
    """
    deviation_pct = ((mid_price - sma) / sma) * 100 if sma > 0 else 0.0

    if deviation_pct < -threshold_pct:
        return {"signal": "BUY", "deviation_pct": deviation_pct,
                "reason": f"mid ${mid_price:.4f} is {abs(deviation_pct):.1f}% below SMA ${sma:.4f}"}
    elif deviation_pct > threshold_pct:
        return {"signal": "SELL", "deviation_pct": deviation_pct,
                "reason": f"mid ${mid_price:.4f} is {deviation_pct:.1f}% above SMA ${sma:.4f}"}
    else:
        return {"signal": "HOLD", "deviation_pct": deviation_pct,
                "reason": f"mid ${mid_price:.4f} within ±{threshold_pct}% of SMA ${sma:.4f}"}


def main():
    print("=== Polymarket Mean-Reversion Strategy (Demo) ===\n")

    # 1. Fetch active events with volume
    events = fetch_events(active=True, volume_min=10000, limit=5)
    if not events:
        print("No active events found. Try again later.")
        return

    for ev in events[:3]:
        title = ev.get("title", ev.get("slug", "?"))
        markets = ev.get("markets", [])
        if not markets:
            continue

        print(f"📊 {title}")
        # Use the first market's first token
        token_id = markets[0].get("clobTokenIds", [None])[0]
        if not token_id:
            token_id = markets[0].get("tokens", [{}])[0].get("token_id", "")

        try:
            mid = fetch_midpoint(token_id)
            spread = fetch_spread(token_id)
        except Exception:
            mid = None
            spread = None

        if mid is None:
            print("  (no orderbook data)\n")
            continue

        # 2. Get price history for SMA
        try:
            history = fetch_price_history(token_id, interval="1h")
            prices = [p["p"] for p in history if p.get("p")]
            sma = compute_simple_moving_average(prices, window=20)
        except Exception:
            sma = None

        print(f"  Mid price: ${mid:.4f}")
        print(f"  Spread:    ${spread:.4f}" if spread else "  Spread:    N/A")

        if sma:
            sig = mean_reversion_signal(mid, sma, threshold_pct=2.0)
            print(f"  SMA(20):   ${sma:.4f}")
            print(f"  Signal:    {sig['signal']}")
            print(f"  {sig['reason']}")
        else:
            print("  SMA:       insufficient data (need 20 candles)")

        print()


if __name__ == "__main__":
    main()
