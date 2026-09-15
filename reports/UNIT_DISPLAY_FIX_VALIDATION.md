# Unit Display Fix Validation

Validation date: 2026-09-15 (Asia/Taipei)

## Root Cause

`generate_daily_report.py` used one formatter for both institutional flow and broker volume. TWSE/TPEx institutional fields are raw share counts, while the Fubon broker table is already expressed in lots (張). The previous report therefore labelled values such as `-11,191,022` as `張` without conversion.

## Official Source Unit

- TWSE: `股` (shares). The T86 daily report headers use `外陸資買賣超股數`, `投信買賣超股數`, `自營商買賣超股數` and `三大法人買賣超股數`.
- TPEx: `股` (shares). The dailyTrade response fields are `買賣超股數`; the official note defines the total as the sum of the three institutional net share counts.
- Broker: `張` (lots). The Fubon broker table is parsed without any scale conversion; `net_vol=709` remains `+709 張`.

## Evidence

Official sources:

- TWSE T86: https://www.twse.com.tw/fund/T86?response=csv&date=20260914&selectType=ALLBUT0999
- TPEx institutional daily detail: https://www.tpex.org.tw/zh-tw/mainboard/trading/major-institutional/detail/day.html

Same-date cross-check (`2026-09-14`):

| Market / code | Official institutional values | Local CSV values | Result |
|---|---|---|---|
| TWSE 2330 | foreign `-11,191,022`, trust `532,435`, dealer `196,288` shares | identical | PASS |
| TWSE 2454 | foreign `734,793`, trust `106,094`, dealer `11,185` shares | identical | PASS |
| TPEx 00679B | foreign `-75,690`, trust `0`, dealer `6,861,753` shares | identical | PASS |
| TPEx 00687B | foreign `221,053`, trust `0`, dealer `1,783,312` shares | identical | PASS |

The current watchlist contains ordinary shares (2330, 2317, 2454), for which `1 張 = 1,000 股` applies. Raw CSV files remain in source share units.

## Implementation

- Added `_fmt_institutional_flow()` to convert shares to lots while preserving a fractional remainder to three decimals.
- Added `_fmt_broker_volume()` to keep broker values in their existing lot unit.
- Added an explicit unit-semantics line to the daily report.
- Hardened daily validation to require the common target date to be present in each market feed, allowing one market to publish a later date without rejecting the common-date update.
- Did not change ranking logic, chip classification, aggregation windows, institutional fetchers, or broker crawler.

## Before / After

- Before: `2330 外資：當日 -11,191,022 張`
- After: `2330 外資：當日 -11,191.022 張`
- Broker unchanged: `群益金鼎 (+709 張)`
- Missing values remain `—`.

## Tests

- `py -3 -m unittest discover -s tests -v` could not locate the system Python installation in this shell.
- Bundled runtime equivalent: `C:\Users\Y6T2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v`
- Result: 7 passed, 0 failed.
- `generate_daily_report.py` regenerated the report successfully.

## Regression Result

- 2330, 2317, and 2454 report values now use institutional share-to-lot conversion.
- Classification remained unchanged versus the pre-fix report: 2330 `negative`, 2317 `neutral`, 2454 `positive`.
- Broker values remain displayed in 張.

## GitHub Actions

The first post-fix run ([34944653467](https://github.com/a275618631/tw-stock-chip-radar/actions/runs/34944653467)) exposed the pre-existing asynchronous-market-date validation issue and failed before reaching the report step. The minimal validation hardening above was added before the final remote run.

- Final run: [34945780520](https://github.com/a275618631/tw-stock-chip-radar/actions/runs/34945780520) — `success`.
- Verified remotely: `update_all.py`, `update_broker.py`, Fubon ranking verification, broker statistics, macro context `6/6`, daily report generation, and branch push.
- Remote report readback confirmed converted institutional values and unchanged broker lots, including `群益金鼎 (+709 張)`.

## Pull Request

- PR: [#1](https://github.com/a275618631/tw-stock-chip-radar/pull/1)
- Title: `fix: correct institutional flow unit display`
- Base: `main`
- Head: `codex/fix-institutional-flow-unit`
- Status: open; not merged.

## Remaining Risks

- TPEx documents exceptions for certain foreign-currency ETFs whose trading unit can be 100 beneficiary units. The current report watchlist is ordinary shares; extending the formatter to those ETF codes would require code-specific lot-size metadata.
- Broker data remains an observed broker-table proxy and does not identify a confirmed beneficial owner.
