# Portability & Sharing Validation

Validation date: 2026-09-16 (Asia/Taipei)

## Final State

`PORTABILITY_AND_SHARING_READY`

Components included: `HTML_UI_PRODUCTION_READY`, `DIRECT_FILE_UX_FIXED`, `SHARE_SNAPSHOT_READY`, and `REPO_ARCHIVED`.

## Root Cause

`DIRECT_FILE_OPEN_UX_TRAP`: opening `docs/index.html` as `file://` caused the existing Dashboard JavaScript to call `fetch()` and show a misleading `Failed to fetch` message. The interactive UI remains HTTP-based by design.

## Direct File UX

`docs/script.js` now checks `window.location.protocol === "file:"` before any data load. It hides the empty Dashboard sections and shows a direct-file notice with `START_HERE.cmd` instructions and a working link to `../reports/daily_market_report.html`. HTTP errors remain separate and refer to missing or invalid Dashboard data, not GitHub Actions.

## Windows Launcher

- `START_HERE.cmd` is the first user entry and delegates to `start_dashboard.cmd`.
- `start_dashboard.cmd` pauses only on failure and preserves the error message.
- `scripts/start_dashboard.ps1` supports `-NoBrowser`, `-SkipPull`, and `-Port`.
- The launcher preserves dirty trees, pulls only clean `main`, selects a fallback port, starts Python standard-library HTTP server with the compatibility `-d` directory flag, checks `/` and `/data/daily_radar.json` with HTTP 200 plus JSON parsing, and opens the browser only after health passes.
- Windows PowerShell 5.1 runtime validation: `-NoBrowser -SkipPull -Port 8766` — PASS.
- `START_HERE.cmd -NoBrowser -SkipPull -Port 8781` — PASS; URL printed as `http://127.0.0.1:8781/` and browser was not opened.

## Fresh Clone Windows

README documents the fresh-clone flow: Git clone of the private repo, then double-click `START_HERE.cmd`. Viewer usage does not require updater dependencies. A no-browser smoke path is available with `START_HERE.cmd -NoBrowser` or `start_dashboard.cmd -NoBrowser`.

## macOS Launcher

- `start_dashboard.command` delegates to `scripts/start_dashboard.sh`.
- The shell launcher resolves its own repo root, preserves dirty trees, uses `python3`/`python`, selects a fallback port, performs HTTP and JSON health checks, and uses `open` only after success.
- `bash -n scripts/start_dashboard.sh` — PASS using Git for Windows Bash.
- Executable mode is staged as `100755` for both macOS launcher files.
- macOS runtime was not executed on this Windows host: `MACOS_LAUNCHER_IMPLEMENTED_RUNTIME_PENDING`.

## Self-contained Report

`reports/daily_market_report.html` remains directly readable without a server or local JSON fetch. It contains Macro, Watchlist, freshness, units, limitations, and disclaimer content.

## Stranger Share Snapshot

- Run `export_share_snapshot.cmd`.
- Output: `exports/share/tw_stock_chip_radar_demo_YYYYMMDD_HHMM.html`.
- The output is a single fixed-time HTML snapshot and does not auto-update.
- It includes `台股籌碼雷達｜Demo Snapshot`, Generated, Data Freshness, and `僅供研究展示，不是投資建議。`.
- The generated `exports/share/` directory is gitignored so a personal timestamped snapshot is not accidentally committed.
- Snapshot runtime validation — PASS; `export_share_snapshot.cmd` succeeded and the output remained self-contained without a server.

## Privacy Scan

Export scans source and output for Windows/macOS absolute paths, the private GitHub repository URL, GitHub tokens/PATs, API/access keys, and email addresses. Current snapshot scan — PASS.

## Tests

- `python -m unittest discover -s tests -v` — 10 passed, 0 failed.
- `python -m py_compile generate_daily_report.py tests/test_mvp.py` — PASS.
- `node --check docs/script.js` — PASS.
- PowerShell parser checks for all `.ps1` files — PASS.
- Direct-file guard, launcher contract, and snapshot contract tests — PASS.
- Local HTTP smoke: `/`, `/script.js`, `/style.css`, `/data/daily_radar.json` — all HTTP 200.

## GitHub Actions

Branch Actions and main final Actions are to be recorded after this branch is pushed and merged. The existing workflow remains unchanged; no Windows runner matrix was added.

## PR / Merge

Branch: `codex/usage-portability-sharing-fix`.

PR and merge commit will be recorded after branch validation and clean diff review. No generated data churn is expected in the PR.

## Daily Usage

1. Windows: double-click `START_HERE.cmd`.
2. macOS: double-click `start_dashboard.command`.
3. Direct report: open `reports/daily_market_report.html` or use `open_daily_report.cmd`.
4. Stranger demo: run `export_share_snapshot.cmd` and share only the generated HTML.
5. Do not double-click `docs/index.html` for the interactive UI.

## Drive

The validation report is committed to the private repository. No Drive API, OAuth, sync framework, or MCP uploader was added. `DRIVE_SYNC_PENDING_CHATGPT`.

## Privacy

The GitHub repository remains private. GitHub Pages, Netlify, Vercel, Cloudflare Pages, tunnels, login, and public hosting were not enabled.

## Remaining Risks

- macOS runtime needs a real Mac for final execution; syntax and executable mode are validated here.
- The interactive chart retains its existing Chart.js CDN dependency; the daily HTML report is self-contained.
- A Share Snapshot cannot be remotely revoked or made to expire after distribution; it is explicitly fixed-time and non-updating.
- GitHub Actions retains its existing Node.js deprecation annotation for action versions; the workflow run remains successful.
