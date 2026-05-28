"""Tests for polymarket-autopilot risk-control policy (shared + project-specific)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from decimal import Decimal

from polymarket_autopilot.policy import (
    Policy,
    check,
    check_polymarket,
    load_policy,
)


class TestSharedChecks(unittest.TestCase):
    """Shared policy rules work in polymarket context."""

    def test_max_amount_reject(self) -> None:
        pol = Policy(max_amount=Decimal("100"))
        result = check(pol, {"amount": "200"})
        self.assertFalse(result.allowed)

    def test_allowed_chains(self) -> None:
        pol = Policy(allowed_chains=["polygon"])
        result = check(pol, {"chain": "polygon"})
        self.assertTrue(result.allowed)


class TestPriceRange(unittest.TestCase):
    """Polymarket-specific: min_price / max_price."""

    def test_within_range(self) -> None:
        pol = Policy(extra={"min_price": 0.05, "max_price": 0.95})
        result = check_polymarket(pol, {"price": "0.50"})
        self.assertTrue(result.allowed)

    def test_below_min(self) -> None:
        pol = Policy(extra={"min_price": 0.05})
        result = check_polymarket(pol, {"price": "0.01"})
        self.assertFalse(result.allowed)
        self.assertEqual(result.violations[0].rule, "min_price")

    def test_above_max(self) -> None:
        pol = Policy(extra={"max_price": 0.95})
        result = check_polymarket(pol, {"price": "0.99"})
        self.assertFalse(result.allowed)
        self.assertEqual(result.violations[0].rule, "max_price")

    def test_no_limit(self) -> None:
        pol = Policy()
        result = check_polymarket(pol, {"price": "0.01"})
        self.assertTrue(result.allowed)


class TestMaxPositionValue(unittest.TestCase):
    """Polymarket-specific: max_position_value."""

    def test_under_limit(self) -> None:
        pol = Policy(extra={"max_position_value": 5000})
        result = check_polymarket(pol, {"position_value": "2000"})
        self.assertTrue(result.allowed)

    def test_over_limit(self) -> None:
        pol = Policy(extra={"max_position_value": 5000})
        result = check_polymarket(pol, {"position_value": "6000"})
        self.assertFalse(result.allowed)
        self.assertEqual(result.violations[0].rule, "max_position_value")


class TestLoadPolicyProject(unittest.TestCase):
    """load_policy defaults to polymarket-autopilot."""

    def test_project_overlay(self) -> None:
        data = {
            "global": {"max_amount": 1000, "allowed_chains": ["polygon"]},
            "polymarket-autopilot": {
                "max_amount": 500,
                "min_price": 0.05,
                "max_price": 0.95,
                "max_position_value": 10000,
            },
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            pol = load_policy(path)
            self.assertEqual(pol.max_amount, Decimal("500"))
            self.assertEqual(pol.extra.get("min_price"), 0.05)
            self.assertEqual(pol.extra.get("max_price"), 0.95)
        finally:
            os.unlink(path)


class TestCombinedViolation(unittest.TestCase):
    """Multiple violations from shared + project-specific rules."""

    def test_amount_and_price(self) -> None:
        pol = Policy(max_amount=Decimal("100"), extra={"max_price": 0.90})
        result = check_polymarket(pol, {"amount": "500", "price": "0.99"})
        self.assertFalse(result.allowed)
        rules = {v.rule for v in result.violations}
        self.assertIn("max_amount", rules)
        self.assertIn("max_price", rules)


if __name__ == "__main__":
    unittest.main()
