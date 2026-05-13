# quantlib-irs-toolkit

[![Tests](https://github.com/fawraw/quantlib-irs-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/fawraw/quantlib-irs-toolkit/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/github/license/fawraw/quantlib-irs-toolkit)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/fawraw/quantlib-irs-toolkit)](https://github.com/fawraw/quantlib-irs-toolkit/releases)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

Minimal, opinionated [QuantLib](https://www.quantlib.org/) helpers to bootstrap interest-rate swap curves from market par rates, with sensible conventions for the EM and frontier currencies most often missing from generic tutorials.

Currently supported out of the box:

- **PLN** (WIBOR 3M)
- **HUF** (BUBOR 3M)
- **CZK** (PRIBOR 3M)
- **ZAR** (JIBAR 3M, quarterly fixed)

Adding a new currency is a single dict entry; see [Adding a currency](#adding-a-currency).

## Install

QuantLib's Python bindings are the only dependency.

```bash
pip install quantlib-irs-toolkit
```

For local development:

```bash
git clone https://github.com/fawraw/quantlib-irs-toolkit.git
cd quantlib-irs-toolkit
pip install -e ".[test]"
pytest
```

QuantLib wheels are available on PyPI for the major platforms. On macOS Apple Silicon you may need to install QuantLib via `brew install quantlib` first.

## Quick start

```python
from quantlib_irs_toolkit import build_irs_curve

result = build_irs_curve(
    ccy="PLN",
    rates={
        "1Y": 4.235,
        "2Y": 4.150,
        "3Y": 4.100,
        "5Y": 4.050,
        "7Y": 4.100,
        "10Y": 4.200,
        "15Y": 4.350,
    },
)

print(result["zero_rates"])
# {'ON': 4.187..., '1W': 4.187..., '1M': 4.190..., ..., '15Y': 4.391...}

print(result["forward_rates"])
# {'1y1y': 4.067..., '5y5y': 4.231..., ...}
```

`rates` are quoted in **percent**: `4.235` means 4.235 %, not 0.04235.

## What you get back

```python
{
    "currency":         "PLN",
    "curve_date":       "2026-05-13",
    "settlement_date":  "20260515",
    "conventions": {
        "day_count":       "ACT/365",
        "fixed_frequency": "Annual",
        "index":           "WIBOR3M",
        "settlement_days": 2,
        "calendar":        "Poland",
    },
    "input_tenors": ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y"],
    "input_rates":  { ... },
    "discount_factors": { "ON": 0.9999..., "1M": 0.9965..., ..., "15Y": 0.5235... },
    "zero_rates":       { "ON": 4.187, "1M": 4.190, ..., "15Y": 4.391 },
    "forward_rates":    { "1y1y": 4.067, "2y1y": 4.055, ..., "5y5y": 4.231 },
    "error":            None,
}
```

If something goes wrong (bad currency, missing rates, unbootstrappable inputs), `error` is a human-readable message and the other fields may be absent.

## Conventions per currency

| Currency | Day count   | Fixed freq | Floating index | Settle | Calendar      |
|----------|-------------|------------|----------------|--------|---------------|
| PLN      | ACT/365     | Annual     | WIBOR 3M       | T+2    | Poland        |
| HUF      | ACT/360     | Annual     | BUBOR 3M       | T+2    | Hungary       |
| CZK      | ACT/360     | Annual     | PRIBOR 3M      | T+2    | CzechRepublic |
| ZAR      | ACT/365     | Quarterly  | JIBAR 3M       | T+0    | SouthAfrica   |

The conventions table (`CCY_CONVENTIONS` in `curves.py`) is the source of truth. If you disagree with a value (eg. your desk uses a different settlement period for ZAR), patch it at runtime:

```python
from quantlib_irs_toolkit import CCY_CONVENTIONS
CCY_CONVENTIONS["ZAR"]["settlement_days"] = 2   # T+2 instead of T+0
```

## Adding a currency

```python
from quantlib_irs_toolkit import CCY_CONVENTIONS, build_irs_curve

CCY_CONVENTIONS["TRY"] = {
    "day_count":        "ACT/360",
    "fixed_frequency":  "Quarterly",
    "index_name":       "TRLIBOR3M",
    "index_tenor":      3,
    "settlement_days":  2,
    "calendar":         "TARGET",   # use TARGET or WeekendsOnly if QL has no native calendar
}

result = build_irs_curve("TRY", { "1Y": 45.0, "2Y": 40.0, "5Y": 32.0 })
```

Supported calendar names (from `_ql_calendar`): `Poland`, `Hungary`, `CzechRepublic`, `SouthAfrica`, `TARGET`, `WeekendsOnly`. Extend the mapping in `curves.py` if you need more.

## Output tenors

By default, the toolkit returns:

- **Discount factors and zero rates** at: `ON, 1W, 1M, 3M, 6M, 1Y, 2Y, 3Y, 4Y, 5Y, 6Y, 7Y, 8Y, 9Y, 10Y, 12Y, 15Y`
- **Forward rates** at: `1y1y, 2y1y, 3y1y, 5y1y, 1y4y, 5y5y, 2y3y, 3y2y`

Both sets are exposed as tuples (`OUTPUT_TENORS`, `FORWARD_PAIRS`) and can be overridden by copying and editing `curves.py`.

## Method

The bootstrapping uses QuantLib's `PiecewiseFlatForward` with `SwapRateHelper` instances for each input tenor. Extrapolation is enabled by default so queries slightly past the longest swap don't raise; pass `extrapolate=False` to `build_irs_curve` if you'd rather fail loudly.

The IBOR index is built generically (`ql.IborIndex`) rather than relying on QuantLib's built-in `Euribor`-style classes, because the EM indices (`WIBOR`, `BUBOR`, `PRIBOR`, `JIBAR`) are not all natively shipped in QuantLib.

## Not in scope

- Multi-curve pricing (separate discount and projection curves)
- OIS-discounted swap pricing
- Cross-currency basis
- Sensitivity / bucketed risk

These are deliberately out of scope for v0. If you need them, this code is a reasonable starting point but you'll want to extend the helpers and the curve construction.

## License

MIT. See [LICENSE](LICENSE).
