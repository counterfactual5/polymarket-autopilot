"""Example: place an order on Polymarket.

Requires env vars: POLYMARKET_API_KEY, POLYMARKET_ADDRESS, POLYMARKET_PRIVATE_KEY
"""

import os

from polymarket_autopilot.trading import PolymarketTrader, Order


def main():
    trader = PolymarketTrader.from_env()

    # View open orders
    print("Open orders:")
    orders = trader.get_orders()
    for o in orders:
        print(f"  {o}")

    # View positions
    print("\nPositions:")
    positions = trader.get_positions()
    for p in positions:
        print(f"  {p.token_id}: {p.side} {p.size} @ {p.average_price}")

    # Place an order (uncomment to use)
    # order = Order(
    #     token_id="<your-token-id>",
    #     side="buy",
    #     price=0.55,
    #     size=10.0,
    # )
    # result = trader.place_order(order)
    # print(f"Order result: {result}")


if __name__ == "__main__":
    main()
