"""Basic usage of quantlib_irs_toolkit.

Run with:

    python examples/basic_usage.py
"""
from __future__ import annotations

import json
from datetime import date

from quantlib_irs_toolkit import build_irs_curve


PLN_MARKET_RATES = {
    "1Y":  4.235,
    "2Y":  4.150,
    "3Y":  4.100,
    "4Y":  4.080,
    "5Y":  4.050,
    "6Y":  4.070,
    "7Y":  4.100,
    "10Y": 4.200,
    "15Y": 4.350,
}


ZAR_MARKET_RATES = {
    "1Y":  7.30,
    "2Y":  7.34,
    "3Y":  7.38,
    "5Y":  7.50,
    "10Y": 7.90,
    "15Y": 8.20,
}


def main() -> None:
    for ccy, rates in (("PLN", PLN_MARKET_RATES), ("ZAR", ZAR_MARKET_RATES)):
        result = build_irs_curve(ccy, rates, eval_date=date.today())
        if result["error"]:
            print(f"[{ccy}] error: {result['error']}")
            continue

        print(f"\n=== {ccy} curve, {result['curve_date']} ===")
        print(f"conventions: {result['conventions']}")

        print("zero rates:")
        for tenor, zr in result["zero_rates"].items():
            print(f"  {tenor:>4s}  {zr:>7.4f} %")

        print("forward rates:")
        for label, fwd in result["forward_rates"].items():
            print(f"  {label:>5s}  {fwd:>7.4f} %")


if __name__ == "__main__":
    main()
