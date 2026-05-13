# Changelog

All notable changes to this project are documented here. Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-13

Initial public release.

### Added

- `build_irs_curve(ccy, rates, eval_date=None, extrapolate=True)` that returns discount factors, zero rates, and forward rates from a set of par swap rates.
- Currency conventions for **PLN** (WIBOR 3M), **HUF** (BUBOR 3M), **CZK** (PRIBOR 3M), **ZAR** (JIBAR 3M, quarterly fixed).
- Per-currency calendar, day count, fixed leg frequency, IBOR index, settlement days.
- 17 standard output tenors (`ON` to `15Y`) and 8 standard forward pairs (`1y1y` to `5y5y`).
- Smoke tests on every supported currency: bootstrap succeeds, discount factors monotonically decrease, zero rates fall in a plausible range.
- GitHub Actions test workflow on Python 3.10, 3.11, 3.12 across `ubuntu-latest`, `windows-latest`, `macos-latest`.
- PyPI publication via Trusted Publisher (OIDC), no API token stored.
- MIT license.

[Unreleased]: https://github.com/fawraw/quantlib-irs-toolkit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/fawraw/quantlib-irs-toolkit/releases/tag/v0.1.0
