"""IRS curve bootstrapping with QuantLib.

Bootstraps a discount curve from a set of market par swap rates using QuantLib's
PiecewiseFlatForward method, then extracts discount factors, zero rates, and
forward rates at a standard set of tenors.

Designed for the EM rates currencies most often missing from generic tutorials:
PLN, HUF, CZK, ZAR. The per-currency conventions table is the source of truth;
override it for other currencies as needed.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

try:
    import QuantLib as ql
    _QL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _QL_AVAILABLE = False
    logger.warning("QuantLib is not installed; bootstrapping disabled")


SUPPORTED_CURRENCIES = ("PLN", "HUF", "CZK", "ZAR")

INPUT_TENORS = ("1Y", "2Y", "3Y", "4Y", "5Y", "6Y", "7Y", "8Y", "9Y", "10Y", "12Y", "15Y")

# Output tenors: (label, count, ql.TimeUnit). The unit is resolved lazily.
OUTPUT_TENORS = (
    ("ON",  1, "Days"),
    ("1W",  1, "Weeks"),
    ("1M",  1, "Months"),
    ("3M",  3, "Months"),
    ("6M",  6, "Months"),
    ("1Y",  1, "Years"),
    ("2Y",  2, "Years"),
    ("3Y",  3, "Years"),
    ("4Y",  4, "Years"),
    ("5Y",  5, "Years"),
    ("6Y",  6, "Years"),
    ("7Y",  7, "Years"),
    ("8Y",  8, "Years"),
    ("9Y",  9, "Years"),
    ("10Y", 10, "Years"),
    ("12Y", 12, "Years"),
    ("15Y", 15, "Years"),
)

# Forward rate pairs: (start_years, length_years) -> label "AyBy".
FORWARD_PAIRS = (
    (1, 1),   # 1y1y
    (2, 1),   # 2y1y
    (3, 1),   # 3y1y
    (5, 1),   # 5y1y
    (1, 4),   # 1y4y
    (5, 5),   # 5y5y
    (2, 3),   # 2y3y
    (3, 2),   # 3y2y
)


CCY_CONVENTIONS: dict[str, dict[str, Any]] = {
    "PLN": {
        "day_count":        "ACT/365",   # ACT/365.FIXED
        "fixed_frequency":  "Annual",
        "index_name":       "WIBOR3M",
        "index_tenor":      3,           # months
        "settlement_days":  2,
        "calendar":         "Poland",
    },
    "HUF": {
        "day_count":        "ACT/360",
        "fixed_frequency":  "Annual",
        "index_name":       "BUBOR3M",
        "index_tenor":      3,
        "settlement_days":  2,
        "calendar":         "Hungary",
    },
    "CZK": {
        "day_count":        "ACT/360",
        "fixed_frequency":  "Annual",
        "index_name":       "PRIBOR3M",
        "index_tenor":      3,
        "settlement_days":  2,
        "calendar":         "CzechRepublic",
    },
    "ZAR": {
        "day_count":        "ACT/365",   # ACT/365.FIXED
        "fixed_frequency":  "Quarterly", # ZAR JIBAR convention is quarterly
        "index_name":       "JIBAR3M",
        "index_tenor":      3,
        "settlement_days":  0,           # T+0 settlement on the ZAR rates market
        "calendar":         "SouthAfrica",
    },
}


# -- Internal helpers -------------------------------------------------------

def _ql_calendar(name: str) -> "ql.Calendar":
    """Map a calendar name to a QuantLib calendar instance."""
    mapping = {
        "Poland":         ql.Poland(),
        "Hungary":        ql.Hungary(),
        "CzechRepublic":  ql.CzechRepublic(),
        "SouthAfrica":    ql.SouthAfrica(),
        "TARGET":         ql.TARGET(),
        "WeekendsOnly":   ql.WeekendsOnly(),
    }
    if name not in mapping:
        raise ValueError(f"Unknown calendar: {name!r}; supported: {list(mapping)}")
    return mapping[name]


def _ql_day_count(name: str) -> "ql.DayCounter":
    mapping = {
        "ACT/360":     ql.Actual360(),
        "ACT/365":     ql.Actual365Fixed(),
        "ACT/365.FIXED": ql.Actual365Fixed(),
        "30/360":      ql.Thirty360(ql.Thirty360.BondBasis),
    }
    if name not in mapping:
        raise ValueError(f"Unknown day count: {name!r}; supported: {list(mapping)}")
    return mapping[name]


def _ql_frequency(name: str) -> int:
    mapping = {
        "Annual":     ql.Annual,
        "Semiannual": ql.Semiannual,
        "Quarterly":  ql.Quarterly,
        "Monthly":    ql.Monthly,
    }
    if name not in mapping:
        raise ValueError(f"Unknown frequency: {name!r}; supported: {list(mapping)}")
    return mapping[name]


def _ql_currency(ccy: str) -> "ql.Currency":
    mapping = {
        "PLN": ql.PLNCurrency(),
        "HUF": ql.HUFCurrency(),
        "CZK": ql.CZKCurrency(),
        "ZAR": ql.ZARCurrency(),
    }
    if ccy not in mapping:
        raise ValueError(f"Unsupported currency: {ccy!r}")
    return mapping[ccy]


def _parse_tenor(tenor_str: str) -> tuple[int, Any]:
    """Parse '1Y', '6M', '2W', '5D' -> (count, ql.TimeUnit)."""
    tenor_str = tenor_str.strip().upper()
    if tenor_str.endswith("Y"):
        return int(tenor_str[:-1]), ql.Years
    if tenor_str.endswith("M"):
        return int(tenor_str[:-1]), ql.Months
    if tenor_str.endswith("W"):
        return int(tenor_str[:-1]), ql.Weeks
    if tenor_str.endswith("D"):
        return int(tenor_str[:-1]), ql.Days
    raise ValueError(f"Cannot parse tenor: {tenor_str!r}")


def _time_unit(name: str) -> int:
    mapping = {"Days": ql.Days, "Weeks": ql.Weeks, "Months": ql.Months, "Years": ql.Years}
    return mapping[name]


# -- Public API -------------------------------------------------------------

def build_irs_curve(
    ccy: str,
    rates: dict[str, float],
    eval_date: date | None = None,
    *,
    extrapolate: bool = True,
) -> dict[str, Any]:
    """Bootstrap an IRS discount curve from market par rates.

    Parameters
    ----------
    ccy :
        Currency code. One of ``SUPPORTED_CURRENCIES`` or any key added to
        ``CCY_CONVENTIONS`` at runtime.
    rates :
        Mapping of tenor -> rate **in percent**. For example
        ``{"1Y": 4.235, "2Y": 4.15, "5Y": 4.05}`` means 4.235 percent, etc.
        Missing tenors are skipped; you must provide at least one valid helper.
    eval_date :
        Evaluation date. Defaults to today.
    extrapolate :
        Whether to enable extrapolation on the curve. Useful when querying
        slightly outside the longest swap tenor; off by default would raise
        for any out-of-range request.

    Returns
    -------
    dict
        On success, keys ``currency``, ``curve_date``, ``settlement_date``,
        ``conventions``, ``input_tenors``, ``input_rates``, ``discount_factors``,
        ``zero_rates``, ``forward_rates``, ``error`` (``None``).
        On failure, ``error`` carries a human-readable message.
    """
    ccy = ccy.upper()

    if not _QL_AVAILABLE:
        return {"error": "QuantLib is not installed"}

    if ccy not in CCY_CONVENTIONS:
        return {
            "error": f"Unsupported currency: {ccy!r}. "
                     f"Configure CCY_CONVENTIONS[{ccy!r}] to extend."
        }

    if not rates:
        return {"error": f"No rates provided for {ccy}"}

    conv = CCY_CONVENTIONS[ccy]

    eval_date = eval_date or date.today()
    ql_eval_date = ql.Date(eval_date.day, eval_date.month, eval_date.year)
    ql.Settings.instance().evaluationDate = ql_eval_date

    calendar = _ql_calendar(conv["calendar"])
    day_count = _ql_day_count(conv["day_count"])
    fixed_frequency = _ql_frequency(conv["fixed_frequency"])
    settlement_days = int(conv["settlement_days"])

    float_tenor = ql.Period(int(conv["index_tenor"]), ql.Months)
    ibor_index = ql.IborIndex(
        conv["index_name"],
        float_tenor,
        settlement_days,
        _ql_currency(ccy),
        calendar,
        ql.ModifiedFollowing,
        False,                       # end-of-month
        day_count,
    )

    helpers = []
    used_tenors: list[str] = []
    for tenor_str in INPUT_TENORS:
        if tenor_str not in rates:
            continue
        rate_value = rates[tenor_str]
        if rate_value is None:
            continue
        try:
            count, unit = _parse_tenor(tenor_str)
        except ValueError:
            continue
        quote = ql.QuoteHandle(ql.SimpleQuote(rate_value / 100.0))
        helpers.append(
            ql.SwapRateHelper(
                quote,
                ql.Period(count, unit),
                calendar,
                fixed_frequency,
                ql.ModifiedFollowing,
                day_count,
                ibor_index,
            )
        )
        used_tenors.append(tenor_str)

    if not helpers:
        return {
            "error": f"No valid rate helpers for {ccy}",
            "provided_tenors": list(rates.keys()),
        }

    try:
        curve = ql.PiecewiseFlatForward(settlement_days, calendar, helpers, day_count)
        if extrapolate:
            curve.enableExtrapolation()
    except RuntimeError as exc:
        return {
            "error": f"QuantLib bootstrap failed: {exc}",
            "input_tenors": used_tenors,
        }

    settlement_date = calendar.advance(ql_eval_date, settlement_days, ql.Days)

    discount_factors: dict[str, float] = {}
    zero_rates: dict[str, float] = {}
    for label, count, unit_name in OUTPUT_TENORS:
        target = calendar.advance(settlement_date, count, _time_unit(unit_name))
        try:
            df = curve.discount(target)
            zr = curve.zeroRate(target, day_count, ql.Continuous).rate() * 100.0
        except RuntimeError:
            continue
        discount_factors[label] = round(df, 10)
        zero_rates[label] = round(zr, 6)

    forward_rates: dict[str, float] = {}
    for start_y, length_y in FORWARD_PAIRS:
        label = f"{start_y}y{length_y}y"
        start = calendar.advance(settlement_date, start_y, ql.Years)
        end = calendar.advance(settlement_date, start_y + length_y, ql.Years)
        try:
            fwd = curve.forwardRate(start, end, day_count, ql.Continuous).rate() * 100.0
        except RuntimeError:
            continue
        forward_rates[label] = round(fwd, 6)

    return {
        "currency":         ccy,
        "curve_date":       eval_date.isoformat(),
        "settlement_date":  settlement_date.ISO(),
        "conventions": {
            "day_count":        conv["day_count"],
            "fixed_frequency":  conv["fixed_frequency"],
            "index":            conv["index_name"],
            "settlement_days":  settlement_days,
            "calendar":         conv["calendar"],
        },
        "input_tenors":     used_tenors,
        "input_rates":      {t: rates[t] for t in used_tenors},
        "discount_factors": discount_factors,
        "zero_rates":       zero_rates,
        "forward_rates":    forward_rates,
        "error":            None,
    }
