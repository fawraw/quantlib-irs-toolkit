"""QuantLib IRS Toolkit -- minimal helpers to bootstrap interest-rate swap curves
from market par rates, with sensible conventions for EM and frontier currencies.

Currently supported: PLN, HUF, CZK, ZAR.

Public API:

    from quantlib_irs_toolkit import build_irs_curve, SUPPORTED_CURRENCIES

    result = build_irs_curve("PLN", {"1Y": 4.235, "2Y": 4.15, "5Y": 4.05})
    print(result["zero_rates"])
"""

from .curves import (
    CCY_CONVENTIONS,
    FORWARD_PAIRS,
    INPUT_TENORS,
    OUTPUT_TENORS,
    SUPPORTED_CURRENCIES,
    build_irs_curve,
)

__all__ = [
    "build_irs_curve",
    "SUPPORTED_CURRENCIES",
    "CCY_CONVENTIONS",
    "INPUT_TENORS",
    "OUTPUT_TENORS",
    "FORWARD_PAIRS",
]

__version__ = "0.1.0"
