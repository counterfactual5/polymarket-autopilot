"""
Polymarket Trading Client
=========================
Authenticated CLOB API client for placing orders and managing positions.

Authentication:
  - Requires API key from Polymarket
  - Requires wallet private key for signing orders (via env var or eth-account)

Environment variables:
  - ``POLYMARKET_API_KEY``
  - ``POLYMARKET_ADDRESS``
  - ``POLYMARKET_PRIVATE_KEY``
"""

import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

# Optional: eth-account for direct signing
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct

    HAS_ETH_ACCOUNT = True
except ImportError:
    HAS_ETH_ACCOUNT = False
    Account = None
    encode_defunct = None


# ────────────────────────────── Configuration ──────────────────────────────

CLOB_BASE = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137


@dataclass
class Order:
    """Order specification."""

    token_id: str
    side: str  # "buy" or "sell"
    price: float  # Price in USDC (0-1 for binary options)
    size: float  # Number of shares
    order_type: str = "limit"
    client_order_id: Optional[str] = None
    nonce: Optional[int] = None


@dataclass
class Position:
    """Current position in a market."""

    token_id: str
    side: str
    size: float
    average_price: float
    unrealized_pnl: float


# ─────────────────────────── HTTP helpers ──────────────────────────────────

def _request(
    url: str,
    *,
    method: str = "GET",
    headers: dict | None = None,
    data: bytes | None = None,
    timeout: int = 30,
) -> Any:
    """Perform an HTTP request using stdlib urllib (no *requests*)."""
    req = urllib.request.Request(url, data=data, method=method, headers={
        "User-Agent": "polymarket-trader/1.0",
        "Accept-Encoding": "gzip, deflate",
        **(headers or {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise PolymarketAPIError(exc.code, body, str(exc.url)) from exc


class PolymarketAPIError(Exception):
    """HTTP error from the Polymarket CLOB API."""

    def __init__(self, status_code: int, body: str, url: str = ""):
        self.status_code = status_code
        self.body = body
        self.url = url
        super().__init__(f"HTTP {status_code}: {body[:200]}")


# ═══════════════════════════════════════════════════════════════════════


class PolymarketTrader:
    """
    Authenticated Polymarket trading client.

    Usage::

        trader = PolymarketTrader.from_env()

        order = Order(token_id="...", side="buy", price=0.55, size=10)
        result = trader.place_order(order)
    """

    def __init__(
        self,
        api_key: str,
        address: str,
        private_key: Optional[str] = None,
        private_key_env: Optional[str] = None,
    ):
        if not HAS_ETH_ACCOUNT and not private_key and not private_key_env:
            raise ImportError(
                "eth-account is required for signing orders. "
                "Install with: pip install polymarket-autopilot[trading]"
            )

        self.api_key = api_key
        self.address = address.lower()

        # Resolve private key
        if private_key:
            self.private_key = private_key
        elif private_key_env:
            self.private_key = os.environ.get(private_key_env)
        else:
            self.private_key = os.environ.get("POLYMARKET_PRIVATE_KEY")

        # Initialise account
        if self.private_key and Account:
            self.account = Account.from_key(self.private_key)
        elif self.private_key:
            raise ImportError("eth-account required to use private_key")
        else:
            self.account = None

        self._base_headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

    @classmethod
    def from_env(cls) -> "PolymarketTrader":
        """Create a trader from standard environment variables."""
        return cls(
            api_key=os.environ["POLYMARKET_API_KEY"],
            address=os.environ["POLYMARKET_ADDRESS"],
            private_key_env="POLYMARKET_PRIVATE_KEY",
        )

    # ─────────────────────────── Signature ─────────────────────────────────

    def _sign_message(self, message: str) -> str:
        """Sign a message with the wallet private key."""
        if not self.account:
            raise ValueError("No signer available — set POLYMARKET_PRIVATE_KEY")
        message_encoded = encode_defunct(text=message)
        signed = self.account.sign_message(message_encoded)
        return signed.signature.hex()

    def _get_nonce(self) -> int:
        """Get current nonce for the address."""
        url = f"{CLOB_BASE}/nonce/{self.address}"
        data = _request(url, headers=self._base_headers)
        return data.get("nonce", int(time.time()))

    # ─────────────────────────── Orders ────────────────────────────────────

    def place_order(self, order: Order) -> dict:
        """Place an order on Polymarket."""
        if order.nonce is None:
            order.nonce = self._get_nonce()

        payload = {
            "orderId": str(order.nonce),
            "tokenID": order.token_id,
            "side": order.side.upper(),
            "orderType": order.order_type.upper(),
            "price": int(order.price * 1_000_000),
            "size": int(order.size * 1_000_000),
            "address": self.address,
            "nonce": order.nonce,
        }

        message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        payload["signature"] = self._sign_message(message)

        body = json.dumps(payload).encode("utf-8")
        headers = {**self._base_headers, "Content-Type": "application/json"}
        return _request(f"{CLOB_BASE}/orders", method="POST", headers=headers, data=body)

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an existing order."""
        return _request(
            f"{CLOB_BASE}/orders/{order_id}",
            method="DELETE",
            headers=self._base_headers,
        )

    def cancel_all_orders(self, token_id: Optional[str] = None) -> dict:
        """Cancel all orders, optionally filtered by token."""
        url = f"{CLOB_BASE}/orders"
        if token_id:
            url += "?" + urllib.parse.urlencode({"tokenID": token_id})
        return _request(url, method="DELETE", headers=self._base_headers)

    def get_orders(self, token_id: Optional[str] = None) -> list:
        """Get open orders for the account."""
        params = {"address": self.address}
        if token_id:
            params["tokenID"] = token_id
        url = f"{CLOB_BASE}/orders?" + urllib.parse.urlencode(params)
        return _request(url, headers=self._base_headers)

    # ─────────────────────────── Positions ─────────────────────────────────

    def get_positions(self) -> list[Position]:
        """Get current positions for the account."""
        data = _request(
            f"{CLOB_BASE}/portfolio/{self.address}",
            headers=self._base_headers,
        )
        positions = []
        for pos in data.get("positions", []):
            positions.append(
                Position(
                    token_id=pos["tokenID"],
                    side=pos["side"],
                    size=float(pos["size"]) / 1_000_000,
                    average_price=float(pos["averagePrice"]) / 1_000_000,
                    unrealized_pnl=float(pos.get("unrealizedPnl", 0)) / 1_000_000,
                )
            )
        return positions

    # ─────────────────────────── Balance ──────────────────────────────────

    def get_balance(self) -> dict:
        """Get USDC balance for the account."""
        try:
            data = _request(
                f"{CLOB_BASE}/balance?address={self.address}",
                headers=self._base_headers,
            )
            return {
                "usdc_balance": float(data.get("balance", 0)),
                "address": self.address,
            }
        except (PolymarketAPIError, urllib.error.URLError, ValueError):
            return {
                "usdc_balance": 0.0,
                "address": self.address,
                "note": "balance query unavailable",
            }
