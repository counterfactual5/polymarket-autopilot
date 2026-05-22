"""Example: fetch top Polymarket events and print them."""

from polymarket_autopilot.fetcher import fetch_events, search, fetch_price_history


def main():
    # Top events by 24h volume
    print("=== Top Events (24h volume) ===")
    events = fetch_events(limit=5)
    for ev in events:
        print(f"  {ev.get('title', '?')} — vol: ${ev.get('volume', 0):,.0f}")

    # Search
    print("\n=== Search: 'bitcoin' ===")
    results = search("bitcoin", limit=3)
    for m in results.get("markets", []):
        print(f"  {m.get('question', '?')}")

    # Price history
    print("\n=== Price History ===")
    if results.get("markets"):
        slug = results["markets"][0].get("slug", "")
        if slug:
            history = fetch_price_history(slug, interval="1d")
            print(f"  {len(history)} candles for '{slug}'")


if __name__ == "__main__":
    main()
