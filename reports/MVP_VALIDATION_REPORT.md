# 台股籌碼雷達 MVP 驗證報告

## Environment

- OS：Windows 11（NT 10.0.26200），x64
- Python：3.12.14（Codex bundled runtime）
- Branch：`codex/tw-stock-chip-radar-mvp`
- Base HEAD：`3421269f12a16c9b9ec3e0329b6c9cbbe77e68df`
- 驗證時間：2026-09-15（Asia/Taipei）

## Upstream V3

| Gate | Command / evidence | Result |
|---|---|---|
| Fresh clone / install | canonical `voidful/tw-institutional-stocker`; requirements installed | PASS |
| Institutional update | `python update_all.py`；TWSE／TPEx flows、foreign holdings 與 5/10/20/30 日 exports 完成 | PASS |
| Institutional sample | 2330、2454 均有法人資料；TWSE／TPEx 最新共同交易日 `2026-09-14` | PASS |
| Broker 2330 | headless `fetch_broker_trading("2330")`；30 筆、非零、欄位齊全 | PASS |
| Broker 2454 | headless `fetch_broker_trading("2454")`；30 筆、非零、欄位齊全 | PASS |
| Broker update | `python update_broker.py --delay 0`；20 檔、600 筆、214 個分點 | PASS |
| Broker statistics | `python analyze_broker_stats.py`；30 個分點分析結果 | PASS |
| Broker correlation | `BROKER_CORR_OFFLINE=1 python analyze_broker_correlation.py`；輸出成功，但本地沒有價格 cache | PARTIAL |
| Broker profit | 3 檔 headless sample，`save_results=False`；取得 21 筆目標分點，但無價格資料可形成績效 | PARTIAL |

原版第一次執行因當日 TWSE T86 尚未發布而失敗；`update_all.py` 已以最小修改改為採用各市場共同最近交易日，並在 log 明確標示 fallback，修復後成功完成。

## Broker Source

- Source：Fubon e-Broker（`https://fubon-ebrokerdj.fbs.com.tw`）
- Playwright：headless Chromium runtime，2330／2454 與 20 檔更新均成功。
- Selector / parser：本次未修改；現有 `table.t01` parser 可用。
- Latest verified broker trade date：`2026-09-14`。
- 分點資料只能作為主力行為代理訊號，不代表已確認主力身分。

## Macro

Source：`yfinance` convenience provider；本次 6/6 成功，輸出日期以各 ticker 實際最新交易日為準。

| Key | Yahoo ticker | Latest date | Latest close | Result |
|---|---|---:|---:|---|
| TSM | `TSM` | 2026-09-14 | 418.010010 | PASS |
| SOX | `^SOX` | 2026-09-14 | 11131.280273 | PASS |
| USD/TWD | `TWD=X` | 2026-09-15 | 31.802000 | PASS |
| USD/JPY | `JPY=X` | 2026-09-15 | 154.830002 | PASS |
| Nikkei | `^N225` | 2026-09-15 | 63489.800781 | PASS |
| US10Y | `^TNX` | 2026-09-14 | 4.961000 | PASS |

環境 deterministic signal：`negative`，score `-3`，可用因素 `5`。單一 ticker 失敗時模組會保留 `missing`／`null` 並將整體標為 `partial`，不會填入假 0。

## Daily Report

- `reports/daily_market_report.md` 已生成。
- 法人與分點資料日期：`2026-09-14`。
- Macro payload 狀態：`ok`；包含 6 項 close、1D／5D 變化。
- watchlist：2330、2317、2454。
- 報告包含 freshness、global context、5D／20D 法人趨勢、買超／賣超分點與限制聲明。
- 不包含 AI 預測、買賣指令或自動交易功能。

## Tests

- `python -m unittest discover -s tests -v`
- 5 passed；0 failed。
- `python analyze_broker_correlation.py` 離線模式 exit code 0；因無價格 cache，相關性結果為非核心 PARTIAL。
- GitHub Actions：workflow 結構與本地 command path 已檢查；未對外 push，因此未執行 GitHub-hosted runner（PARTIAL）。

## Files Changed

### Source / workflow

- `.github/workflows/update.yml`
- `requirements.txt`
- `update_all.py`
- `macro_context.py`
- `generate_daily_report.py`
- `tests/test_mvp.py`

### Daily deliverables

- `reports/daily_market_report.md`
- `reports/MVP_VALIDATION_REPORT.md`
- `docs/data/macro_context.json`

### Refreshed upstream data

- `data/twse_flows.csv`
- `data/tpex_flows.csv`
- `data/twse_foreign.csv`
- `data/tpex_foreign.csv`
- `data/broker/broker_history.csv`
- `data/broker/broker_trades_2026-09-15.csv`
- `docs/data/broker_ranking.json`
- `docs/data/broker_stats.json`
- `docs/data/broker_trades_latest.json`
- `docs/data/broker_trends.json`
- `docs/data/target_broker_trades.json`
- `docs/data/broker_correlations.json`
- `docs/data/top_three_inst_{change,netbuy}_{5,10,20,30}_{up,down}.json`
- `docs/data/timeseries/*.json`（原專案各股票時序輸出，依最新法人資料刷新）

## Known Risks

- Fubon HTML／反爬機制或 DOM 改版可能使分點抓取失效；本次沒有繞過 CAPTCHA、登入或反濫用保護。
- `yfinance` 是第三方 convenience provider，不是 Yahoo 官方授權 API。
- 券商分點不等於已確認的主力身分。
- Macro proxy 不等於美國／日本國籍資金直接流入台股。
- 投信／自營商持股模型若無 baseline，仍屬淨買賣累計估算，不是官方即時持股。
- GitHub Actions 尚未在遠端 runner 實跑；本次未 push、未部署、未開 PR。

## Final Status

`READY_FOR_DAILY_USE`

法人、分點、macro 與每日報告的核心本地流程均可用；可選的 correlation／profit 因本地沒有價格 cache 保留 PARTIAL，不阻斷每日法人＋分點＋macro MVP。
