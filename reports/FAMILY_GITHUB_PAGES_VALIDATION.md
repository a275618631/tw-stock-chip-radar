# Family GitHub Pages Validation

Validation date: 2026-09-16 (Asia/Taipei)

## Final State

`BLOCKED_PRIVATE_REPO_PAGES_PLAN`

The stock selector and GitHub Pages compatibility work are complete, but deployment is stopped by the explicit handoff stop condition. GitHub API returned: `Your current plan does not support GitHub Pages for this repository.`

## Repo Visibility

`Private` — unchanged.

## Pages Visibility

No public Pages URL is active. No public copy or alternate hosting was created.

## GitHub Plan Gate

`BLOCKED_PRIVATE_REPO_PAGES_PLAN` — `POST /repos/a275618631/tw-stock-chip-radar/pages` with `main /docs` returned HTTP 422 because the current plan does not support GitHub Pages for this private repository.

## Pages Source

Prepared as `main /docs`, with `docs/.nojekyll`, relative asset paths, and `docs/robots.txt`; deployment was not created because of the plan gate.

## Production URL

Expected after a supported plan is available:

`https://a275618631.github.io/tw-stock-chip-radar/`

Not deployed in this run.

## Personal / Family Use

The intended site is for personal and family non-commercial use only. The local Dashboard and static daily report remain available.

## Runtime Verification

- Local HTTP Dashboard: PASS.
- GitHub Pages remote HTTP/UI runtime: NOT RUN because Pages deployment was blocked.
- Browser was not opened; this follows the user instruction.

## Data Freshness

The post-merge main Actions run completed successfully and updated `docs/data/daily_radar.json`, `docs/data/stock_catalog.json`, timeseries files, and the daily report.

## Interactive Features

- Stock selector: PASS; searchable catalog contains 2,465 generated Taiwan market instruments and supports direct valid-code input.
- Institutional chart: PASS by local contract and data-file smoke checks.
- Broker and macro sections: preserved.
- Pages interactive runtime: pending deployment.

## Mobile Smoke

Existing responsive CSS and table overflow behavior are preserved. Remote 390px / 768px / desktop smoke is pending because Pages is not deployed.

## Search Index Minimization

- `docs/robots.txt`: added with `Disallow: /`.
- `noindex,nofollow,noarchive` meta: added to `docs/index.html` and `docs/broker_stats.html`.
- This reduces indexing only; it is not access control.

## Privacy Scan

PASS for `docs/`: no Windows/macOS user paths, email addresses, GitHub tokens, private Repo URL, cookies, credentials, or local debug logs.

## Tests

- `.venv/Scripts/python.exe -m unittest discover -s tests -v` — 12 passed, 0 failed.
- Python compile — PASS.
- `node --check docs/script.js` — PASS.
- PowerShell parser — PASS.
- Bash syntax — PASS from previous portability validation.
- Local HTTP smoke — PASS.

## GitHub Actions

- Feature/main merge: [PR #7](https://github.com/a275618631/tw-stock-chip-radar/pull/7) — merged.
- Main validation: [run 35077502214](https://github.com/a275618631/tw-stock-chip-radar/actions/runs/35077502214) — success in 8m05s.
- Main generated-data commit: `b5f5d5cac`.
- Existing Node.js 20 deprecation annotation is non-blocking.

## PR / Merge

- Branch: `codex/github-pages-family-web`.
- Merge commit: `dac0886716b8600d0fb9ab2ae9b78aa38f46176c`.
- No Pages deployment PR was created after the stop condition.

## Remaining Risks

- GitHub Pages remains unavailable until the account has a supported plan; do not change Repo visibility solely for this task.
- Remote Pages runtime, Chart.js CDN, and mobile smoke remain unverified.
- Drive status: `DRIVE_SYNC_PENDING_CHATGPT`; no uploader or OAuth was added.
- macOS runtime still needs a real Mac; launcher syntax and executable mode were previously validated.
