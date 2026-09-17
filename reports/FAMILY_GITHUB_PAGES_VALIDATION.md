# Family GitHub Pages Validation

Validation date: 2026-09-17 (Asia/Taipei)

## Final State

`FAMILY_GITHUB_PAGES_ARCHIVED`

The short-term personal/family non-commercial test is complete. GitHub Pages was disabled and the repository visibility was restored to Private. The historical public URL is retained below for traceability only and is no longer active.

## Repo Visibility

`Private` — restored after the temporary family test. The source is no longer publicly accessible.

Archive verification: `gh repo view` reports `isPrivate=true`; `GET /pages` returns HTTP 404 after Pages deletion.

## Pages Visibility

GitHub Pages is disabled. The historical public URL is no longer active. No alternate hosting was created.

## GitHub Plan Gate

Private-plan gate was confirmed by the earlier HTTP 422. Per the temporary-test handoff, the Repo was then intentionally changed to Public and Pages creation succeeded.

## Pages Source (historical)

`main /docs`, with `docs/.nojekyll`, relative asset paths, and `docs/robots.txt`; this was the temporary test configuration. Pages was later deleted through the GitHub API.

## Production URL

`https://a275618631.github.io/tw-stock-chip-radar/`

Deployment status before archive: `built`; the final public endpoint and published assets passed HTTP verification. Current deployment status: disabled.

## Personal / Family Use

The intended site is for personal and family non-commercial use only. The local Dashboard and static daily report remain available.

The family web deployment is archived. The local entry points remain the supported way to run the Dashboard.

## Runtime Verification

- Local HTTP Dashboard: PASS.
- GitHub Pages remote HTTP runtime before archive: PASS for `/`, `/script.js`, `/style.css`, `/broker_stats.html`, `/robots.txt`, daily JSON, stock catalog, and `2330`/`8069` timeseries.
- Chart.js CDN HTTP check: PASS (HTTP 200).
- Browser/UI click smoke: intentionally not run because the user instructed Codex not to open a browser; manual family testing is the remaining UI gate.
- Browser was not opened; this follows the user instruction.

## Data Freshness

The post-merge main Actions run completed successfully and updated `docs/data/daily_radar.json`, `docs/data/stock_catalog.json`, timeseries files, and the daily report.

## Interactive Features

- Stock selector: PASS; searchable catalog contains 2,465 generated Taiwan market instruments and supports direct valid-code input.
- Institutional chart: PASS by local contract and data-file smoke checks.
- Broker and macro sections: preserved.
- Pages asset/data runtime before archive: PASS; manual browser interaction was not run because Codex was instructed not to open a browser.

## Mobile Smoke

Existing responsive CSS and table overflow behavior are preserved. Remote 390px / 768px / desktop visual smoke is pending manual testing because Codex did not open a browser.

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
- Temporary-public privacy cleanup: [PR #9](https://github.com/a275618631/tw-stock-chip-radar/pull/9) — merged.
- Temporary family-test final report: [PR #10](https://github.com/a275618631/tw-stock-chip-radar/pull/10) — merged.
- Existing Node.js 20 deprecation annotation is non-blocking.

## PR / Merge

- Branch: `codex/github-pages-family-web`.
- Merge commit: `dac0886716b8600d0fb9ab2ae9b78aa38f46176c`.
- Pages was created after temporary Public conversion; no Pages-specific deployment workflow was added.
- Final test-status archive merge commit: `7ebceebe0936d73fe897001a23ce0b7624ec73d7`.

## Remaining Risks

- Repo is Private and Pages is disabled after the family test.
- Browser visual/mobile interaction is intentionally pending manual testing.
- Drive archival copy: to be updated in the existing `02_驗證報告` folder after this Repo commit.
- macOS runtime still needs a real Mac; launcher syntax and executable mode were previously validated.
