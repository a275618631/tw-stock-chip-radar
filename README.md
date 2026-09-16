# tw_institutional_stocker

台股三大法人持股比重追蹤（上市 + 上櫃），自動每日更新並提供 private local UI。

## 新版重點

- 支援多個變化視窗：`WINDOWS = [5, 20, 60, 120]`
  - 產出：
    - `docs/data/top_three_inst_change_5_up.json` / `..._down.json`
    - `docs/data/top_three_inst_change_20_up.json` / ...
    - `docs/data/top_three_inst_change_60_up.json` / ...
    - `docs/data/top_three_inst_change_120_up.json` / ...
  - 前端可透過下拉選單切換視窗。

- 三大法人模型升級：
  - 外資：仍採官方 `foreign_ratio`。
  - 投信 / 自營商：支援「基準點校正」：
    - 準備 `data/inst_baseline.csv`，格式：
      ```csv
      date,code,trust_shares_base,dealer_shares_base
      2025-01-31,2330,100000000,20000000
      2025-01-31,0050,50000000,0
      ```
    - 模型在每檔股票內以日期排序，若遇到 baseline：
      - 設 `trust_shares_est = baseline_trust + sum(trust_net since baseline)`
      - 設 `dealer_shares_est = baseline_dealer + sum(dealer_net since baseline)`
    - 若完全沒有 baseline，則退化為純 cumsum 模型：
      - `trust_shares_est = cumsum(trust_net)`
      - `dealer_shares_est = cumsum(dealer_net)`

## 結構概覽

- `update_all.py`
  - 從 TWSE / TPEX 抓取：
    - 三大法人每日買賣超（上市 T86 + 上櫃 3itrade_hedge_result）
    - 外資持股統計（上市 MI_QFIIS + 上櫃 QFII）
  - 以 `inst_baseline.csv` 為基準點，搭配日淨買超推估投信 / 自營商持股。
  - 計算三大法人持股比重與多個視窗的變化值。
  - 匯出：
    - `docs/data/timeseries/{code}.json`
    - `docs/data/top_three_inst_change_{w}_up.json` / `..._down.json`

- `docs/`
  - 靜態前端（index.html + script.js + style.css）
  - 提供：
    - 隨輸入代碼動態載入該股三法人持股時序。
    - 以 5 / 20 / 60 / 120 日變化排序的排名表，可點擊列載入該股圖。
    - 市場過濾（全部 / TWSE / TPEX）與 log scale 切換。

- `.github/workflows/update.yml`
  - 每天 00:10 UTC 由 GitHub Actions 執行 `python update_all.py`
  - 若 `data/` 或 `docs/data/` 有變動，會自動 commit + push 回 main 分支。

## 本地開發

```bash
pip install -r requirements.txt
python update_all.py
```

執行完後，`docs/data/` 底下會長出 json 檔，直接用 `python -m http.server` 或 VSCode Live Server 打開 `docs/index.html` 即可預覽。

若要啟用「基準點校正」：
1. 從投信 / 自營商的財報或官方持股統計整理出某幾個日期的「實際持股股數」。
2. 填入 `data/inst_baseline.csv`。
3. 重新跑 `python update_all.py`。之後 GitHub Actions 自動更新也會沿用這些 baseline。

## 台股籌碼雷達 MVP

本 Repo 產生每日台股法人、券商分點與全球市場代理資訊，報告位於
`reports/daily_market_report.md`。GitHub Actions 會依排程更新資料並產生報告；也可在本地依序執行：

```bash
python update_all.py
python update_broker.py
python analyze_broker_stats.py
python macro_context.py
python generate_daily_report.py
```

資料來源包含 TWSE／TPEx 公開資料、Fubon e-Broker 分點頁面，以及
`yfinance` 第三方 convenience provider。券商分點是主力行為代理，不是已確認的主力身分；
macro 指標不是美日資金直接流入台股數據；本工具僅供研究參考，不產生交易指令。

## 每天怎麼使用

### 方法 A｜互動 Dashboard

Windows 使用者雙擊 `start_dashboard.cmd`，會在工作區更新最新 main、啟動 local static server，並開啟 `http://127.0.0.1:8765/`（若該 port 被占用會自動往後尋找）。

### 方法 B｜今天的 HTML 報告

雙擊 `open_daily_report.cmd`，即可開啟 self-contained 的 [每日 HTML 報告](reports/daily_market_report.html)。報告不依賴 Python server 或 JSON fetch。

### 自動更新

GitHub Actions 每日約台灣 19:10 更新市場資料；平常不需要手動執行 Python。

正式 Watchlist 設定在 `config/watchlist.json`；`positive / neutral / negative` 是研究排序訊號，不是交易指令。

目前 Dashboard 為 private local UI，不啟用 GitHub Pages 或其他公開部署。

Based on / derived from `voidful/tw-institutional-stocker`.

本 Repo 維持 Private；上游目前未宣告授權，本專案不宣稱 MIT、Apache 或 GPL。
