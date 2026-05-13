"""Smoke tests for build_irs_curve.

These tests check the basic shape of the output and a few obvious invariants
(monotonic discount factors, zero rates positive, etc.). They run only if
QuantLib is installed in the test environment.
"""
from __future__ import annotations

import pytest

ql = pytest.importorskip("QuantLib")

from quantlib_irs_toolkit import (
    SUPPORTED_CURRENCIES,
    build_irs_curve,
)


SAMPLE_RATES = {
    "PLN": {
        "1Y": 4.235, "2Y": 4.15, "3Y": 4.10, "4Y": 4.08, "5Y": 4.05,
        "6Y": 4.07, "7Y": 4.10, "10Y": 4.20, "15Y": 4.35,
    },
    "HUF": {
        "1Y": 6.50, "2Y": 6.30, "3Y": 6.20, "5Y": 6.10, "10Y": 6.30,
    },
    "CZK": {
        "1Y": 3.80, "2Y": 3.60, "3Y": 3.55, "5Y": 3.60, "10Y": 3.80,
    },
    "ZAR": {
        "1Y": 7.30, "2Y": 7.34, "3Y": 7.38, "5Y": 7.50, "10Y": 7.90, "15Y": 8.20,
    },
}


@pytest.mark.parametrize("ccy", SUPPORTED_CURRENCIES)
def test_build_irs_curve_succeeds(ccy):
    result = build_irs_curve(ccy, SAMPLE_RATES[ccy])
    assert result["error"] is None, result["error"]
    assert result["currency"] == ccy
    assert set(result["input_tenors"]).issubset(set(SAMPLE_RATES[ccy].keys()))
    assert result["zero_rates"], "expected non-empty zero rates"
    assert result["discount_factors"], "expected non-empty discount factors"


@pytest.mark.parametrize("ccy", SUPPORTED_CURRENCIES)
def test_discount_factors_monotonically_decreasing(ccy):
    result = build_irs_curve(ccy, SAMPLE_RATES[ccy])
    dfs = list(result["discount_factors"].values())
    for earlier, later in zip(dfs, dfs[1:]):
        assert later <= earlier + 1e-9, (
            f"Discount factors should decrease over time, got {earlier} -> {later}"
        )


@pytest.mark.parametrize("ccy", SUPPORTED_CURRENCIES)
def test_zero_rates_in_plausible_range(ccy):
    result = build_irs_curve(ccy, SAMPLE_RATES[ccy])
    for label, zr in result["zero_rates"].items():
        assert 0 < zr < 50, f"{ccy} {label}: implausible zero rate {zr}"


def test_unsupported_currency_returns_error():
    result = build_irs_curve("XYZ", {"1Y": 1.0})
    assert result["error"] and "Unsupported" in result["error"]


def test_empty_rates_returns_error():
    result = build_irs_curve("PLN", {})
    assert result["error"] is not None


def test_forward_rates_present_for_long_enough_curve():
    result = build_irs_curve("PLN", SAMPLE_RATES["PLN"])
    assert "1y1y" in result["forward_rates"]
    assert "5y5y" in result["forward_rates"]
