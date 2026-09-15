# -*- coding: utf-8 -*-
"""Generate a dated, static Markdown Taiwan chip-radar report."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from macro_context import classify_stock_chip_status


WATCHLIST = [("2330", "台積電"), ("2317", "鴻海"), ("2454", "聯發科")]
FLOW_FILES = [Path("data/twse_flows.csv"), Path("data/tpex_flows.csv")]
BROKER_PATH = Path("docs/data/broker_trades_latest.json")
MACRO_PATH = Path("docs/data/macro_context.json")
REPORT_PATH = Path("reports/daily_market_report.md")


def _norm_code(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def _load_flows(paths=FLOW_FILES) -> pd.DataFrame:
    frames = []
    for path in paths:
        if path.exists():
            try:
                frames.append(pd.read_csv(path))
            except (OSError, ValueError):
                continue
    if not frames:
        return pd.DataFrame(columns=["date", "code", "foreign_net", "trust_net", "dealer_net", "market"])
    out = pd.concat(frames, ignore_index=True)
    out["code"] = _norm_code(out["code"])
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    for col in ("foreign_net", "trust_net", "dealer_net"):
        out[col] = pd.to_numeric(out.get(col), errors="coerce")
    return out.dropna(subset=["date", "code"])


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _summarize_stock(flows: pd.DataFrame, brokers: pd.DataFrame, code: str) -> dict:
    stock = flows[flows["code"] == code].copy()
    if stock.empty:
        return {"code": code, "latest_date": None, "metrics": {}, "status": "insufficient_data", "buys": [], "sells": []}
    by_day = stock.groupby("date")[["foreign_net", "trust_net", "dealer_net"]].sum().sort_index()
    latest = by_day.index.max()
    metrics = {}
    for actor in ("foreign_net", "trust_net", "dealer_net"):
        metrics[f"{actor[:-4]}_1d"] = float(by_day.loc[latest, actor])
        metrics[f"{actor[:-4]}_5d"] = float(by_day.tail(5)[actor].sum())
        metrics[f"{actor[:-4]}_20d"] = float(by_day.tail(20)[actor].sum())

    latest_brokers = brokers[brokers["stock_code"] == code].copy() if not brokers.empty else pd.DataFrame()
    if not latest_brokers.empty:
        latest_brokers["net_vol"] = pd.to_numeric(latest_brokers["net_vol"], errors="coerce").fillna(0)
        buys = latest_brokers.sort_values("net_vol", ascending=False).head(3)
        sells = latest_brokers.sort_values("net_vol", ascending=True).head(3)
        buy_records = buys[["broker_name", "net_vol"]].to_dict("records")
        sell_records = sells[["broker_name", "net_vol"]].to_dict("records")
    else:
        buy_records, sell_records = [], []
    status = classify_stock_chip_status(
        {"foreign_5d": metrics.get("foreign_5d"), "trust_5d": metrics.get("trust_5d"), "foreign_20d": metrics.get("foreign_20d"), "trust_20d": metrics.get("trust_20d")}
    )
    return {"code": code, "latest_date": latest.date().isoformat(), "metrics": metrics, "status": status, "buys": buy_records, "sells": sell_records}


def _fmt_institutional_flow(value) -> str:
    """Format institutional flow, whose raw TWSE/TPEx unit is shares."""
    if value is None or pd.isna(value):
        return "—"
    lots = float(value) / 1000.0
    if lots.is_integer():
        return f"{lots:+,.0f} 張"
    # Keep the exact share remainder visible; do not silently truncate to lots.
    return f"{lots:+,.3f} 張"


def _fmt_broker_volume(value) -> str:
    """Format broker volume, whose raw Fubon unit is lots (張)."""
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):+,.0f} 張"


def _fmt_brokers(records) -> str:
    if not records:
        return "—"
    return "、".join(f"{item['broker_name']} ({_fmt_broker_volume(item['net_vol'])})" for item in records)


def generate_report(flow_paths=FLOW_FILES, broker_path=BROKER_PATH, macro_path=MACRO_PATH, output_path=REPORT_PATH) -> Path:
    flows = _load_flows(flow_paths)
    broker_payload = _load_json(Path(broker_path), {})
    broker_rows = broker_payload.get("data", []) if isinstance(broker_payload, dict) else []
    brokers = pd.DataFrame(broker_rows)
    if not brokers.empty:
        brokers["stock_code"] = _norm_code(brokers["stock_code"])
    macro = _load_json(Path(macro_path), {"status": "missing", "data": {}, "environment": {"label": "insufficient_data", "risk_flags": []}})
    stock_summaries = [_summarize_stock(flows, brokers, code) for code, _ in WATCHLIST]
    dates = [item["latest_date"] for item in stock_summaries if item["latest_date"]]
    broker_dates = []
    if not brokers.empty and "trade_date" in brokers:
        broker_dates = pd.to_datetime(brokers["trade_date"], errors="coerce").dropna().dt.date.astype(str).tolist()
    institutional_date = max(dates) if dates else None
    broker_date = max(broker_dates) if broker_dates else None
    macro_date = macro.get("as_of")
    freshness = "ok"
    if not institutional_date or not broker_date or macro.get("status") in ("partial", "failed", "missing"):
        freshness = "partial"

    env = macro.get("environment", {})
    lines = [
        f"# 台股籌碼雷達｜{institutional_date or macro_date or datetime.now().date().isoformat()}",
        "",
        "## Data Freshness",
        "",
        f"- 狀態：`{freshness}`",
        f"- 法人資料日期：{institutional_date or 'missing'}",
        f"- 分點資料日期：{broker_date or 'missing'}",
        f"- Macro 資料日期：{macro_date or 'missing'}（來源狀態：`{macro.get('status', 'missing')}`）",
        "- 單位語意：三大法人原始資料為股，日報以 1,000 股換算為張；券商分點原始資料為張。",
        "",
        "## Global Context",
        "",
    ]
    for key, item in macro.get("data", {}).items():
        lines.append(f"- {item.get('name', key)}（{item.get('ticker', '—')}）：close `{item.get('close', '—')}`，1D `{item.get('change_1d_pct', '—')}%`，5D `{item.get('change_5d_pct', '—')}%`，`{item.get('status', 'missing')}`")
    lines.extend([f"- 環境標籤：`{env.get('label', 'insufficient_data')}`（score={env.get('score', '—')}）"])
    for flag in env.get("risk_flags", []):
        lines.append(f"- Risk flag：{flag}")

    lines.extend(["", "## Watchlist", ""])
    for (code, name), summary in zip(WATCHLIST, stock_summaries):
        m = summary["metrics"]
        lines.extend([
            f"### {code} {name}",
            "",
            f"- 資料日期：{summary['latest_date'] or 'missing'}",
            f"- 外資：當日 {_fmt_institutional_flow(m.get('foreign_1d'))}；5D {_fmt_institutional_flow(m.get('foreign_5d'))}；20D {_fmt_institutional_flow(m.get('foreign_20d'))}",
            f"- 投信：當日 {_fmt_institutional_flow(m.get('trust_1d'))}；5D {_fmt_institutional_flow(m.get('trust_5d'))}；20D {_fmt_institutional_flow(m.get('trust_20d'))}",
            f"- 自營商：當日 {_fmt_institutional_flow(m.get('dealer_1d'))}；5D {_fmt_institutional_flow(m.get('dealer_5d'))}；20D {_fmt_institutional_flow(m.get('dealer_20d'))}",
            f"- 主要買超分點：{_fmt_brokers(summary['buys'])}",
            f"- 主要賣超分點：{_fmt_brokers(summary['sells'])}",
            f"- 籌碼狀態：`{summary['status']}`",
            "- 資料限制：券商分點為主力行為代理訊號；若資料日期或欄位缺失，本段不做方向性推論。",
            "",
        ])

    lines.extend([
        "## Important Disclaimer",
        "",
        "- 券商分點不等於已確認主力身分。",
        "- yfinance 指標是市場環境代理，不是美日資金直接流入台股數據。",
        "- 本工具僅供研究參考，不產生交易指令。",
        "",
    ])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the daily Taiwan chip radar Markdown report")
    parser.add_argument("--output", default=str(REPORT_PATH))
    args = parser.parse_args()
    path = generate_report(output_path=Path(args.output))
    print(f"daily report -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
