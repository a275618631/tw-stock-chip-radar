# HTML UI Validation Report

Validation date: 2026-09-16 (Asia/Taipei)

## Final State

`HTML_UI_PRODUCTION_READY`

## Architecture

The existing static HTML/CSS/JavaScript application remains the UI foundation. A single payload builder now produces the Markdown report, self-contained HTML report, and Dashboard JSON from the same institutional, broker, macro, and watchlist inputs.

No React, Vue, API server, database, hosting, login system, or new data provider was added.

## Existing UI Reused

- `docs/index.html`
- `docs/script.js`
- `docs/style.css`
- Existing institutional chart, filters, rankings, broker section, and `docs/broker_stats.html`

## New Components

- `config/watchlist.json` as the enabled Watchlist source of truth.
- `docs/data/daily_radar.json` for the Dashboard payload.
- `reports/daily_market_report.html` as a self-contained reading copy.
- `start_dashboard.cmd` + `scripts/start_dashboard.ps1` for local Dashboard startup.
- `open_daily_report.cmd` + `scripts/open_daily_report.ps1` for cached HTML report opening.

## Daily Radar

The default homepage is `今日雷達`, showing Data Freshness, Global Context, and the configured Watchlist. Clicking a Watchlist stock reuses the existing `loadStock(code)` path and opens the existing institutional chart.

Global Context contains TSM, ^SOX, TWD=X, JPY=X, ^N225, and ^TNX with latest value, 1D%, and 5D%. Environment labels reuse the existing deterministic score.

## Watchlist

Default enabled stocks are 2330 台積電, 2317 鴻海, and 2454 聯發科. Edit `config/watchlist.json` and rerun the normal data workflow to change the formal Watchlist. Broker coverage remains the existing hot-stock mechanism; missing coverage displays `分點：未追蹤`, not zero.

## HTML Report

The HTML report contains the conclusion, freshness, six macro indicators, Watchlist metrics, top broker buys/sells, chip status, limitations, and disclaimers. CSS and primary data are inline; the file does not fetch JSON and can be opened directly.

## Local Launcher

- `start_dashboard.cmd` calls PowerShell, preserves dirty working trees, fast-forwards clean `main` when possible, finds `.venv` / `py -3` / `python`, starts a local server on 8765 or the next available port, and opens the local URL when the user runs it.
- `open_daily_report.cmd` updates clean `main` when possible and opens the last local HTML report even when pull fails.

## Tests

- `python -m py_compile generate_daily_report.py tests/test_mvp.py` — PASS.
- `python -m unittest discover -s tests -v` — 8 passed, 0 failed.
- `node --check docs/script.js` — PASS.
- Payload schema — PASS: status, freshness, 6 macro indicators, 3 Watchlist stocks, explicit `source_unit=shares` and `unit=lots`.
- Self-contained HTML — PASS: inline CSS, no `fetch()` dependency, Chinese content present.

## Branch Actions

- Branch: `codex/daily-radar-html-ui`
- Run: [35052952544](https://github.com/a275618631/tw-stock-chip-radar/actions/runs/35052952544)
- Result: success.
- `update_all.py`, broker update, Fubon comparison, broker statistics, macro `6/6`, and all three report outputs completed.
- Feature branch commit/push was skipped by the existing main-only guard; branch SHA remained unchanged.
- Payload freshness was explicitly `partial` because institutional/broker data reached 2026-09-16 while macro `as_of` remained 2026-09-15.

## Main Actions

- PR #3 was squash-merged cleanly as commit `e2be763651aeec4c34ecd07f07f4a6aa61d495f8`.
- Final run: [35057796714](https://github.com/a275618631/tw-stock-chip-radar/actions/runs/35057796714) — success.
- All update, broker, Fubon comparison, broker statistics, macro `6/6`, report generation, and commit/push steps passed.
- Generated-data commit: `156c72260` (`chore: daily data update 2026-09-16`).
- Main output read-back passed: `docs/data/daily_radar.json`, `reports/daily_market_report.html`, and `reports/daily_market_report.md` exist; JSON contains 6 macro indicators, 3 Watchlist stocks, explicit lots semantics, and visible `partial` freshness.
- The main-only generated-data commit policy remains unchanged for production updates.

## UI Smoke

With a local static server, these endpoints returned HTTP 200:

- `/`
- `/script.js`
- `/style.css`
- `/data/daily_radar.json`

Desktop/tablet/mobile CSS paths were reviewed for responsive stacking, horizontal table scrolling, and readable status labels. No graphical browser automation was launched.

## Data Freshness

Every user-facing output exposes institutional date, broker date, macro date, and generated time. `ok`, `partial`, and `missing` are preserved as visible states; an older or missing source is never silently shown as current.

## Unit Semantics

Institutional source fields remain raw shares (`股`) and are converted once with `shares / 1000` for display as lots (`張`). Broker Fubon values remain their original lot unit. Existing classification and ranking logic is reused unchanged.

## Privacy

Private-first local UI. GitHub Pages, Netlify, Cloudflare Pages, Vercel, and other public hosting were not enabled.

## Daily User Instructions

1. Double-click `start_dashboard.cmd` for the interactive Dashboard.
2. Double-click `open_daily_report.cmd` for the direct HTML report.
3. Review Data Freshness before interpreting Global Context or Watchlist signals.
4. Treat `positive / neutral / negative` as research sorting signals, not trading instructions.

## Remaining Risks

- Global market sessions can publish on different dates; the UI intentionally reports `partial` until freshness aligns.
- The interactive chart still uses the existing Chart.js CDN dependency; the local static server and network access are needed for that chart library, while the daily HTML report is self-contained.
- Broker branches are behavioral proxies and do not identify confirmed beneficial owners.
