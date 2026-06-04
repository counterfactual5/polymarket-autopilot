"""Market-data snapshot validation for Polymarket CLOB books.

Guards every trade path against acting on degenerate or internally
inconsistent order-book data. Polymarket outcome tokens are probabilities:
a healthy price sits strictly between 0 and 1, so the checks here differ from
a perp venue — exactly 0 or 1 means a resolved/degenerate market, and the
spread is measured in probability points, not bps.

Rules enforced:
  - price (and any provided mid) is a number strictly in (0, 1)
  - the book has both a bid and an ask side
  - best bid / best ask are each strictly in (0, 1)
  - the book is not crossed (best_bid <= best_ask)
  - the spread does not exceed ``max_spread`` (default 0.10 == 10 cents)
  - a provided mid agrees with the live book

Pure stdlib + Decimal, no network calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

# Reject books whose top-of-book spread exceeds this many probability points.
DEFAULT_MAX_SPREAD = Decimal("0.10")

# How far a reported mid may sit outside [best_bid, best_ask] before the
# snapshot is treated as inconsistent (stale / bad feed).
DEFAULT_MID_BAND = Decimal("0.05")

_ONE = Decimal("1")
_ZERO = Decimal("0")


class MarketDataError(ValueError):
    """Raised when a market-data snapshot is not safe to trade on."""


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


@dataclass
class SnapshotCheck:
    ok: bool
    token_id: str
    mid: Decimal | None = None
    best_bid: Decimal | None = None
    best_ask: Decimal | None = None
    spread: Decimal | None = None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        def _t(v: Decimal | None) -> str | None:
            return format(v.normalize(), "f") if isinstance(v, Decimal) else None

        return {
            "ok": self.ok,
            "token_id": self.token_id,
            "mid": _t(self.mid),
            "best_bid": _t(self.best_bid),
            "best_ask": _t(self.best_ask),
            "spread": _t(self.spread),
            "reasons": list(self.reasons),
        }


def _best_levels(book: dict[str, Any]) -> tuple[Decimal | None, Decimal | None]:
    """Return (best_bid, best_ask) from a CLOB book.

    CLOB ``/book`` returns ``bids`` and ``asks`` arrays of ``{price, size}``.
    Best bid is the highest bid price; best ask is the lowest ask price. We
    compute max/min explicitly rather than trusting sort order.
    """
    def _prices(side: Any) -> list[Decimal]:
        out: list[Decimal] = []
        for lvl in side or []:
            px = _to_decimal(lvl.get("price")) if isinstance(lvl, dict) else None
            if px is not None:
                out.append(px)
        return out

    bids = _prices((book or {}).get("bids"))
    asks = _prices((book or {}).get("asks"))
    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None
    return best_bid, best_ask


def _in_unit_interval(v: Decimal) -> bool:
    return _ZERO < v < _ONE


def validate_market_snapshot(
    token_id: str,
    book: dict[str, Any] | None,
    *,
    mid: Any = None,
    max_spread: Decimal = DEFAULT_MAX_SPREAD,
    mid_band: Decimal = DEFAULT_MID_BAND,
) -> SnapshotCheck:
    """Validate a Polymarket book/price snapshot without raising."""
    reasons: list[str] = []

    mid_dec = _to_decimal(mid) if mid is not None else None
    if mid is not None and mid_dec is None:
        reasons.append(f"mid for {token_id} is not a number: {mid!r}")
    elif mid_dec is not None and not _in_unit_interval(mid_dec):
        reasons.append(f"mid for {token_id} outside (0,1): {mid_dec}")

    best_bid, best_ask = _best_levels(book or {})
    if best_bid is None:
        reasons.append(f"book for {token_id} has no bid side")
    elif not _in_unit_interval(best_bid):
        reasons.append(f"best bid for {token_id} outside (0,1): {best_bid}")
    if best_ask is None:
        reasons.append(f"book for {token_id} has no ask side")
    elif not _in_unit_interval(best_ask):
        reasons.append(f"best ask for {token_id} outside (0,1): {best_ask}")

    spread: Decimal | None = None
    if best_bid is not None and best_ask is not None and _in_unit_interval(best_bid) and _in_unit_interval(best_ask):
        if best_bid > best_ask:
            reasons.append(
                f"crossed book for {token_id}: bid {best_bid} > ask {best_ask}"
            )
        else:
            spread = best_ask - best_bid
            if spread > max_spread:
                reasons.append(
                    f"spread for {token_id} too wide: {spread} > {max_spread}"
                )
            if mid_dec is not None and _in_unit_interval(mid_dec):
                if mid_dec < best_bid - mid_band or mid_dec > best_ask + mid_band:
                    reasons.append(
                        f"mid {mid_dec} for {token_id} diverges from book "
                        f"[{best_bid}, {best_ask}] beyond {mid_band}"
                    )

    return SnapshotCheck(
        ok=not reasons,
        token_id=token_id,
        mid=mid_dec,
        best_bid=best_bid,
        best_ask=best_ask,
        spread=spread,
        reasons=reasons,
    )


def assert_tradeable_snapshot(
    token_id: str,
    book: dict[str, Any] | None,
    *,
    mid: Any = None,
    max_spread: Decimal = DEFAULT_MAX_SPREAD,
    mid_band: Decimal = DEFAULT_MID_BAND,
) -> SnapshotCheck:
    """Validate a snapshot and raise :class:`MarketDataError` when unsafe."""
    check = validate_market_snapshot(
        token_id, book, mid=mid, max_spread=max_spread, mid_band=mid_band
    )
    if not check.ok:
        raise MarketDataError(
            f"unsafe market snapshot for {token_id}: " + "; ".join(check.reasons)
        )
    return check
