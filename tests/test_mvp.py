# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from generate_daily_report import (
    _fmt_broker_volume,
    _fmt_institutional_flow,
    build_report_payload,
    generate_outputs,
    generate_report,
    load_watchlist,
)
from macro_context import (
    TICKER_MAP,
    calculate_percentage_changes,
    classify_global_environment,
    classify_stock_chip_status,
)
from update_all import FLOW_COLUMNS, export_stock_catalog, validate_flow_history


class MvpRulesTest(unittest.TestCase):
    def test_ticker_mapping(self):
        self.assertEqual(TICKER_MAP["TSM"]["ticker"], "TSM")
        self.assertEqual(TICKER_MAP["USD_TWD"]["ticker"], "TWD=X")
        self.assertEqual(set(TICKER_MAP), {"TSM", "SOX", "USD_TWD", "USD_JPY", "NIKKEI", "US10Y"})

    def test_percentage_calculation(self):
        self.assertEqual(calculate_percentage_changes([100, 110, 121, 132, 120]), {"change_1d_pct": -9.0909, "change_5d_pct": 20.0})
        self.assertEqual(calculate_percentage_changes([100]), {"change_1d_pct": None, "change_5d_pct": None})

    def test_missing_values_are_not_directional(self):
        self.assertEqual(classify_global_environment({"TSM": {}, "SOX": {}, "USD_TWD": {}})["label"], "insufficient_data")
        self.assertEqual(classify_stock_chip_status({"foreign_5d": None, "trust_5d": None}), "insufficient_data")

    def test_deterministic_signals(self):
        data = {key: {"change_1d_pct": 1.0} for key in TICKER_MAP}
        data["USD_TWD"]["change_1d_pct"] = -1.0
        data["US10Y"]["change_1d_pct"] = -1.0
        self.assertEqual(classify_global_environment(data)["label"], "positive")
        self.assertEqual(classify_stock_chip_status({"foreign_5d": 10, "trust_5d": 1, "foreign_20d": 2, "trust_20d": -1}), "positive")

    def test_unit_specific_formatters(self):
        self.assertEqual(_fmt_institutional_flow(1_000_000), "+1,000 張")
        self.assertEqual(_fmt_institutional_flow(-11_191_022), "-11,191.022 張")
        self.assertEqual(_fmt_broker_volume(709), "+709 張")
        self.assertEqual(_fmt_institutional_flow(None), "—")
        self.assertEqual(_fmt_broker_volume(None), "—")

    def test_flow_validation_allows_later_market_data(self):
        rows = [
            {"date": date(2026, 9, 14), "code": "2330", "name": "台積電", "foreign_net": 1, "trust_net": 2, "dealer_net": 3, "market": "TEST"},
            {"date": date(2026, 9, 15), "code": "2330", "name": "台積電", "foreign_net": 4, "trust_net": 5, "dealer_net": 6, "market": "TEST"},
        ]
        validate_flow_history(pd.DataFrame(rows, columns=FLOW_COLUMNS), "TEST", date(2026, 9, 14))

    def test_report_generation_with_partial_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / "flows.csv"
            flow.write_text("date,code,name,foreign_net,trust_net,dealer_net,market\n2026-09-14,2330,台積電,100,50,-10,TWSE\n2026-09-13,2330,台積電,20,10,0,TWSE\n", encoding="utf-8")
            broker = root / "broker.json"
            broker.write_text(json.dumps({"data": [{"trade_date": "2026-09-14", "stock_code": "2330", "broker_name": "測試分點", "net_vol": 10}]}, ensure_ascii=False), encoding="utf-8")
            macro = root / "macro.json"
            macro.write_text(json.dumps({"as_of": "2026-09-14", "status": "partial", "data": {"TSM": {"name": "TSM", "ticker": "TSM", "status": "ok", "close": 1, "change_1d_pct": 1, "change_5d_pct": 1}}, "environment": {"label": "insufficient_data", "risk_flags": []}}, ensure_ascii=False), encoding="utf-8")
            output = root / "report.md"
            generate_report([flow], broker, macro, output)
            text = output.read_text(encoding="utf-8")
            self.assertIn("2330", text)
            self.assertIn("partial", text)
            self.assertIn("+0.100 張", text)
            self.assertIn("+10 張", text)
            self.assertIn("資料限制", text)
            self.assertIn("不產生交易指令", text)

    def test_daily_radar_payload_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flow = root / "flows.csv"
            flow.write_text("date,code,name,foreign_net,trust_net,dealer_net,market\n2026-09-15,2330,台積電,100,50,-10,TWSE\n2026-09-14,2330,台積電,20,10,0,TWSE\n", encoding="utf-8")
            broker = root / "broker.json"
            broker.write_text(json.dumps({"data": []}, ensure_ascii=False), encoding="utf-8")
            macro_data = {
                key: {"ticker": config["ticker"], "name": config["name"], "status": "ok", "latest_date": "2026-09-15", "close": 1, "change_1d_pct": 1, "change_5d_pct": 1}
                for key, config in TICKER_MAP.items()
            }
            macro = root / "macro.json"
            macro.write_text(json.dumps({"as_of": "2026-09-15", "status": "ok", "data": macro_data, "environment": {"label": "positive", "score": 3, "risk_flags": []}}, ensure_ascii=False), encoding="utf-8")
            watchlist = root / "watchlist.json"
            watchlist.write_text(json.dumps({"version": 1, "stocks": [{"code": "2330", "name": "台積電", "enabled": True}, {"code": "2454", "name": "聯發科", "enabled": False}]}, ensure_ascii=False), encoding="utf-8")
            report = root / "report.md"
            html = root / "report.html"
            radar = root / "daily_radar.json"

            payload = build_report_payload([flow], broker, macro, watchlist)
            self.assertEqual([item["code"] for item in load_watchlist(watchlist)], ["2330"])
            self.assertEqual(payload["status"], "partial")
            self.assertEqual(payload["freshness"]["institutional"], "2026-09-15")
            stock = payload["watchlist"][0]
            self.assertEqual(stock["institutional"]["unit"], "lots")
            self.assertEqual(stock["institutional"]["source_unit"], "shares")
            self.assertEqual(stock["institutional"]["foreign_5d"], 0.12)
            self.assertEqual(stock["status"], "positive")
            self.assertFalse(stock["brokers"]["available"])
            self.assertEqual(stock["brokers"]["top_buys"], [])

            generate_outputs([flow], broker, macro, watchlist, report, html, radar)
            html_text = html.read_text(encoding="utf-8")
            json_payload = json.loads(radar.read_text(encoding="utf-8"))
            self.assertTrue(html.exists())
            self.assertIn("2330 台積電", html_text)
            self.assertIn("Global Context", html_text)
            self.assertIn("Data Freshness", html_text)
            self.assertIn("不產生交易指令", html_text)
            self.assertIn("分點：未追蹤", html_text)
            self.assertEqual(len(json_payload["macro"]), 6)
            self.assertEqual(json_payload["watchlist"][0]["institutional"]["unit"], "lots")

    def test_direct_file_open_has_safe_ux_guard(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "docs" / "index.html").read_text(encoding="utf-8")
        script = (root / "docs" / "script.js").read_text(encoding="utf-8")
        self.assertIn('id="directFileNotice"', html)
        self.assertIn("START_HERE.cmd", html)
        self.assertIn('../reports/daily_market_report.html', html)
        self.assertIn('window.location.protocol === "file:"', script)
        self.assertIn("showDirectFileNotice();", script)
        self.assertNotIn("今日雷達載入失敗：Failed to fetch", script)

    def test_portability_and_snapshot_contract(self):
        root = Path(__file__).resolve().parents[1]
        start_ps1 = (root / "scripts" / "start_dashboard.ps1").read_text(encoding="utf-8-sig")
        share_ps1 = (root / "scripts" / "export_share_snapshot.ps1").read_text(encoding="utf-8-sig")
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn("[switch]$NoBrowser", start_ps1)
        self.assertIn("[switch]$SkipPull", start_ps1)
        self.assertIn("Test-DashboardHealth", start_ps1)
        self.assertIn("ConvertFrom-Json", start_ps1)
        self.assertIn("台股籌碼雷達｜Demo Snapshot", share_ps1)
        self.assertIn("Find-PrivacyIssue", share_ps1)
        self.assertIn("START_HERE.cmd", readme)
        self.assertIn("export_share_snapshot.cmd", readme)

    def test_stock_catalog_and_switch_contract(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "docs" / "index.html").read_text(encoding="utf-8")
        script = (root / "docs" / "script.js").read_text(encoding="utf-8")
        self.assertIn('list="stockCatalog"', html)
        self.assertIn('id="stockCatalog"', html)
        self.assertIn('data/stock_catalog.json', script)
        self.assertIn("encodeURIComponent(code)", script)
        self.assertIn("isValidStockCode", script)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "stock_catalog.json"
            frame = pd.DataFrame([
                {"code": "2330", "name": "台積電", "market": "TWSE", "date": date(2026, 9, 15)},
                {"code": "8069", "name": "元太", "market": "TPEX", "date": date(2026, 9, 15)},
            ])
            export_stock_catalog(frame, output)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([item["code"] for item in payload["stocks"]], ["2330", "8069"])
            self.assertEqual(payload["stocks"][1]["market"], "TPEX")

    def test_github_pages_contract(self):
        root = Path(__file__).resolve().parents[1]
        index = (root / "docs" / "index.html").read_text(encoding="utf-8")
        broker = (root / "docs" / "broker_stats.html").read_text(encoding="utf-8")
        robots = (root / "docs" / "robots.txt").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">', index)
        self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">', broker)
        self.assertIn("Personal &amp; Family Non-commercial Use", index)
        self.assertIn("User-agent: *", robots)
        self.assertIn("Disallow: /", robots)
        for path in (root / "docs").rglob("*"):
            if path.is_file() and path.suffix.lower() in {".html", ".js", ".css", ".json", ".txt"}:
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"C:\\\\Users\\|/Users/")
                self.assertNotRegex(text, r"(?:ghp_|github_pat_|sk-[A-Za-z0-9_-]{12,})")
                self.assertNotIn("github.com/a275618631/tw-stock-chip-radar", text)


if __name__ == "__main__":
    unittest.main()
