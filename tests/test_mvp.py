# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from pathlib import Path

from generate_daily_report import (
    _fmt_broker_volume,
    _fmt_institutional_flow,
    generate_report,
)
from macro_context import (
    TICKER_MAP,
    calculate_percentage_changes,
    classify_global_environment,
    classify_stock_chip_status,
)


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


if __name__ == "__main__":
    unittest.main()
