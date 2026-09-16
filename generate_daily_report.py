# -*- coding: utf-8 -*-
"""Build the shared daily-radar payload and its Markdown/HTML outputs."""

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from macro_context import TICKER_MAP, classify_stock_chip_status


DEFAULT_WATCHLIST = [
    {"code": "2330", "name": "台積電", "enabled": True},
    {"code": "2317", "name": "鴻海", "enabled": True},
    {"code": "2454", "name": "聯發科", "enabled": True},
]
WATCHLIST_PATH = Path("config/watchlist.json")
FLOW_FILES = [Path("data/twse_flows.csv"), Path("data/tpex_flows.csv")]
BROKER_PATH = Path("docs/data/broker_trades_latest.json")
MACRO_PATH = Path("docs/data/macro_context.json")
REPORT_PATH = Path("reports/daily_market_report.md")
HTML_REPORT_PATH = Path("reports/daily_market_report.html")
RADAR_PATH = Path("docs/data/daily_radar.json")
COMMON_LIMITATIONS = [
    "券商分點是主力行為代理，不等於已確認主力身分。",
    "yfinance 指標是市場環境代理，不是美日資金直接流入台股數據。",
    "本工具僅供研究參考，不產生交易指令。",
]


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


def load_watchlist(path: Path = WATCHLIST_PATH) -> list[dict]:
    """Load enabled stocks from the single Daily Radar source of truth."""
    payload = _load_json(path, {"stocks": DEFAULT_WATCHLIST})
    stocks = payload.get("stocks", []) if isinstance(payload, dict) else []
    valid = []
    for item in stocks:
        if not isinstance(item, dict) or not item.get("enabled", True):
            continue
        code = str(item.get("code", "")).strip()
        name = str(item.get("name", "")).strip()
        if code and name:
            valid.append({"code": code, "name": name, "enabled": True})
    return valid or DEFAULT_WATCHLIST.copy()


def _summarize_stock(flows: pd.DataFrame, brokers: pd.DataFrame, code: str, name: str) -> dict:
    stock = flows[flows["code"] == code].copy()
    if stock.empty:
        return {"code": code, "name": name, "latest_date": None, "metrics": {}, "status": "insufficient_data", "buys": [], "sells": [], "broker_available": False}
    by_day = stock.groupby("date")[["foreign_net", "trust_net", "dealer_net"]].sum().sort_index()
    latest = by_day.index.max()
    metrics = {}
    for actor in ("foreign_net", "trust_net", "dealer_net"):
        metrics[f"{actor[:-4]}_1d"] = float(by_day.loc[latest, actor])
        metrics[f"{actor[:-4]}_5d"] = float(by_day.tail(5)[actor].sum())
        metrics[f"{actor[:-4]}_20d"] = float(by_day.tail(20)[actor].sum())

    latest_brokers = brokers[brokers["stock_code"] == code].copy() if not brokers.empty else pd.DataFrame()
    if not latest_brokers.empty:
        latest_brokers["net_vol"] = pd.to_numeric(latest_brokers["net_vol"], errors="coerce")
        latest_brokers = latest_brokers.dropna(subset=["net_vol"])
        buys = latest_brokers[latest_brokers["net_vol"] > 0].sort_values("net_vol", ascending=False).head(3)
        sells = latest_brokers[latest_brokers["net_vol"] < 0].sort_values("net_vol").head(3)
        buy_records = buys[["broker_name", "net_vol"]].to_dict("records")
        sell_records = sells[["broker_name", "net_vol"]].to_dict("records")
    else:
        buy_records, sell_records = [], []
    status = classify_stock_chip_status({"foreign_5d": metrics.get("foreign_5d"), "trust_5d": metrics.get("trust_5d"), "foreign_20d": metrics.get("foreign_20d"), "trust_20d": metrics.get("trust_20d")})
    return {"code": code, "name": name, "latest_date": latest.date().isoformat(), "metrics": metrics, "status": status, "buys": buy_records, "sells": sell_records, "broker_available": bool(buy_records or sell_records)}


def _shares_to_lots(value):
    if value is None or pd.isna(value):
        return None
    return round(float(value) / 1000.0, 6)


def _fmt_lots(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    lots = float(value)
    if lots.is_integer():
        return f"{lots:+,.0f} 張"
    return f"{lots:+,.3f} 張"


def _fmt_institutional_flow(value) -> str:
    """Backward-compatible formatter for raw institutional shares."""
    return _fmt_lots(_shares_to_lots(value))


def _fmt_broker_volume(value) -> str:
    """Format broker volume, whose raw Fubon unit is lots (張)."""
    return _fmt_lots(value)


def _fmt_brokers(records) -> str:
    if not records:
        return "—"
    return "、".join(f"{item['broker_name']} ({_fmt_broker_volume(item['net_vol'])})" for item in records)


def build_report_payload(flow_paths=FLOW_FILES, broker_path=BROKER_PATH, macro_path=MACRO_PATH, watchlist_path=WATCHLIST_PATH) -> dict:
    flows = _load_flows(flow_paths)
    broker_payload = _load_json(Path(broker_path), {})
    broker_rows = broker_payload.get("data", []) if isinstance(broker_payload, dict) else []
    brokers = pd.DataFrame(broker_rows)
    if not brokers.empty and "stock_code" in brokers:
        brokers["stock_code"] = _norm_code(brokers["stock_code"])
    macro = _load_json(Path(macro_path), {"status": "missing", "data": {}, "environment": {"label": "insufficient_data", "score": None, "risk_flags": []}})
    watchlist = load_watchlist(Path(watchlist_path))
    summaries = [_summarize_stock(flows, brokers, item["code"], item["name"]) for item in watchlist]

    institutional_date = flows["date"].max().date().isoformat() if not flows.empty else None
    broker_dates = []
    if not brokers.empty and "trade_date" in brokers:
        broker_dates = pd.to_datetime(brokers["trade_date"], errors="coerce").dropna().dt.date.astype(str).tolist()
    broker_date = max(broker_dates) if broker_dates else None
    macro_date = macro.get("as_of")
    freshness_values = [institutional_date, broker_date, macro_date]
    if not any(freshness_values):
        freshness_status = "missing"
    elif all(freshness_values) and len(set(freshness_values)) == 1 and macro.get("status") == "ok":
        freshness_status = "ok"
    else:
        freshness_status = "partial"

    macro_items = []
    for key, config in TICKER_MAP.items():
        item = macro.get("data", {}).get(key, {})
        macro_items.append({"key": key, "ticker": item.get("ticker", config["ticker"]), "name": item.get("name", config["name"]), "status": item.get("status", "missing"), "latest_date": item.get("latest_date"), "close": item.get("close"), "change_1d_pct": item.get("change_1d_pct"), "change_5d_pct": item.get("change_5d_pct")})

    radar_stocks = []
    for summary in summaries:
        metrics = summary["metrics"]
        institutional = {key: _shares_to_lots(metrics.get(key)) for key in ("foreign_1d", "foreign_5d", "foreign_20d", "trust_1d", "trust_5d", "trust_20d", "dealer_1d", "dealer_5d", "dealer_20d")}
        institutional.update({"unit": "lots", "source_unit": "shares", "scale": 1000})
        radar_stocks.append({
            "code": summary["code"], "name": summary["name"], "date": summary["latest_date"], "status": summary["status"], "institutional": institutional,
            "brokers": {"available": summary["broker_available"], "as_of": broker_date if summary["broker_available"] else None, "unit": "lots", "top_buys": summary["buys"], "top_sells": summary["sells"]},
        })

    generated_at = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    return {"status": freshness_status, "generated_at": generated_at, "freshness": {"institutional": institutional_date, "broker": broker_date, "macro": macro_date}, "environment": macro.get("environment", {"label": "insufficient_data", "score": None, "risk_flags": []}), "macro": macro_items, "watchlist": radar_stocks, "limitations": COMMON_LIMITATIONS + list(macro.get("limitations", []))}


def render_markdown(payload: dict) -> str:
    freshness = payload["freshness"]
    environment = payload.get("environment", {})
    report_date = freshness.get("institutional") or freshness.get("macro") or datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()
    lines = [f"# 台股籌碼雷達｜{report_date}", "", "## Data Freshness", "", f"- 狀態：`{payload.get('status', 'missing')}`", f"- 法人資料日期：{freshness.get('institutional') or 'missing'}", f"- 分點資料日期：{freshness.get('broker') or 'missing'}", f"- Macro 資料日期：{freshness.get('macro') or 'missing'}", "- 單位語意：三大法人原始資料為股，日報以 1,000 股換算為張；券商分點原始資料為張。", "", "## Global Context", ""]
    for item in payload.get("macro", []):
        lines.append(f"- {item['name']}（{item['ticker']}）：close `{item.get('close', '—')}`，1D `{item.get('change_1d_pct', '—')}%`，5D `{item.get('change_5d_pct', '—')}%`，`{item.get('status', 'missing')}`")
    lines.append(f"- 環境標籤：`{environment.get('label', 'insufficient_data')}`（score={environment.get('score', '—')}）")
    lines.extend(f"- Risk flag：{flag}" for flag in environment.get("risk_flags", []))
    lines.extend(["", "## Watchlist", ""])
    for stock in payload.get("watchlist", []):
        m = stock["institutional"]
        brokers = stock["brokers"]
        lines.extend([f"### {stock['code']} {stock['name']}", "", f"- 資料日期：{stock.get('date') or 'missing'}", f"- 外資：當日 {_fmt_lots(m.get('foreign_1d'))}；5D {_fmt_lots(m.get('foreign_5d'))}；20D {_fmt_lots(m.get('foreign_20d'))}", f"- 投信：當日 {_fmt_lots(m.get('trust_1d'))}；5D {_fmt_lots(m.get('trust_5d'))}；20D {_fmt_lots(m.get('trust_20d'))}", f"- 自營商：當日 {_fmt_lots(m.get('dealer_1d'))}；5D {_fmt_lots(m.get('dealer_5d'))}；20D {_fmt_lots(m.get('dealer_20d'))}", f"- 主要買超分點：{_fmt_brokers(brokers.get('top_buys', [])) if brokers.get('available') else '未追蹤'}", f"- 主要賣超分點：{_fmt_brokers(brokers.get('top_sells', [])) if brokers.get('available') else '未追蹤'}", f"- 籌碼狀態：`{stock.get('status', 'insufficient_data')}`", "- 資料限制：券商分點為主力行為代理訊號；若資料日期或欄位缺失，本段不做方向性推論。", ""])
    lines.extend(["## Important Disclaimer", ""])
    lines.extend(f"- {item}" for item in COMMON_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


HTML_STYLE = """
:root { color-scheme: light; --ink:#172033; --muted:#64748b; --line:#dbe3ef; --panel:#fff; --bg:#f4f7fb; --positive:#087f5b; --neutral:#9a6700; --negative:#c92a2a; --missing:#64748b; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft JhengHei",sans-serif; line-height:1.55; }
main { width:min(1120px,100% - 32px); margin:0 auto; padding:32px 0 56px; }
header { background:linear-gradient(135deg,#16213e,#2d4a7b); color:#fff; padding:28px; border-radius:20px; margin-bottom:18px; }
h1,h2,h3,p { margin-top:0; } h1 { margin-bottom:4px; font-size:clamp(1.7rem,4vw,2.5rem); } h2 { margin:0 0 12px; font-size:1.25rem; } h3 { margin-bottom:4px; }
.eyebrow { color:#cbd5e1; font-size:.85rem; letter-spacing:.08em; text-transform:uppercase; } .muted { color:var(--muted); }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:20px; margin-bottom:16px; box-shadow:0 8px 24px rgba(23,32,51,.05); }
.status-row,.macro-grid,.watch-grid,.metric-grid { display:grid; gap:12px; } .status-row { grid-template-columns:repeat(4,minmax(0,1fr)); } .macro-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } .watch-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
.status-card,.macro-card { border:1px solid var(--line); border-radius:12px; padding:13px; background:#fbfdff; } .status-label,.metric-label { color:var(--muted); font-size:.78rem; } .status-value { font-weight:700; margin-top:4px; }
.metric-grid { grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:14px; } .metric { border-top:1px solid var(--line); padding-top:9px; } .metric-value { font-variant-numeric:tabular-nums; white-space:nowrap; }
.signal { display:inline-flex; align-items:center; gap:6px; font-weight:700; } .signal::before { content:""; width:9px; height:9px; border-radius:50%; background:currentColor; } .positive { color:var(--positive); } .neutral { color:var(--neutral); } .negative { color:var(--negative); } .missing,.insufficient_data { color:var(--missing); }
.broker-columns { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:14px; } .broker-list { margin:0; padding-left:20px; } .broker-list li { margin:3px 0; }
table { width:100%; border-collapse:collapse; } th,td { text-align:left; padding:9px 8px; border-bottom:1px solid var(--line); } th { color:var(--muted); font-size:.8rem; } td.num { text-align:right; font-variant-numeric:tabular-nums; }
footer { color:var(--muted); font-size:.85rem; } .tag { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:2px 8px; font-size:.75rem; color:var(--muted); }
@media (max-width:768px) { main { width:min(100% - 20px,1120px); padding-top:16px; } header,.panel { padding:16px; border-radius:14px; } .status-row,.macro-grid,.watch-grid { grid-template-columns:1fr; } .metric-grid { grid-template-columns:repeat(3,minmax(130px,1fr)); overflow-x:auto; } .broker-columns { grid-template-columns:1fr; } .table-scroll { overflow-x:auto; } table { min-width:620px; } }
"""


def _html_signal(label: str) -> str:
    labels = {"positive": "Positive", "neutral": "Neutral", "negative": "Negative", "insufficient_data": "Insufficient"}
    safe = label if label in labels else "missing"
    return f'<span class="signal {html.escape(safe)}">{html.escape(labels.get(safe, "Missing"))}</span>'


def render_html(payload: dict) -> str:
    e = html.escape
    env = payload.get("environment", {})
    freshness = payload.get("freshness", {})
    status_label = payload.get("status", "missing")
    report_date = freshness.get("institutional") or freshness.get("macro") or "未定"
    generated_at = payload.get("generated_at", "未定")
    freshness_cards = "".join(f'<div class="status-card"><div class="status-label">{e(label)}</div><div class="status-value">{e(str(generated_at if key == "generated_at" else freshness.get(key) or "missing"))}</div></div>' for key, label in (("institutional", "法人"), ("broker", "分點"), ("macro", "Macro"), ("generated_at", "最後更新")))
    macro_cards = []
    for item in payload.get("macro", []):
        macro_cards.append(f'<div class="macro-card"><h3>{e(item["name"])}</h3><div class="muted">{e(item["ticker"])} · {e(item.get("latest_date") or "missing")}</div><p><strong>{e(str(item.get("close") if item.get("close") is not None else "—"))}</strong></p><div class="muted">1D {e(str(item.get("change_1d_pct") if item.get("change_1d_pct") is not None else "—"))}% · 5D {e(str(item.get("change_5d_pct") if item.get("change_5d_pct") is not None else "—"))}%</div></div>')
    watch_cards = []
    for stock in payload.get("watchlist", []):
        m = stock.get("institutional", {})
        broker = stock.get("brokers", {})
        def broker_list(items, empty):
            if not broker.get("available"):
                return f'<p class="muted">{empty}</p>'
            if not items:
                return '<p class="muted">無資料</p>'
            return '<ul class="broker-list">' + ''.join(f'<li>{e(str(item.get("broker_name", "未命名")))} <strong>{e(_fmt_lots(item.get("net_vol")))}</strong></li>' for item in items) + '</ul>'
        watch_cards.append(f'<article class="panel"><div style="display:flex;justify-content:space-between;gap:8px;align-items:start"><div><div class="eyebrow">{e(stock.get("date") or "missing")}</div><h2>{e(stock["code"])} {e(stock["name"])}</h2></div>{_html_signal(stock.get("status", "insufficient_data"))}</div><div class="metric-grid"><div class="metric"><div class="metric-label">外資 1D / 5D / 20D（張）</div><div class="metric-value">{e(_fmt_lots(m.get("foreign_1d")))} / {e(_fmt_lots(m.get("foreign_5d")))} / {e(_fmt_lots(m.get("foreign_20d")))}</div></div><div class="metric"><div class="metric-label">投信 1D / 5D / 20D（張）</div><div class="metric-value">{e(_fmt_lots(m.get("trust_1d")))} / {e(_fmt_lots(m.get("trust_5d")))} / {e(_fmt_lots(m.get("trust_20d")))}</div></div><div class="metric"><div class="metric-label">自營商 1D / 5D / 20D（張）</div><div class="metric-value">{e(_fmt_lots(m.get("dealer_1d")))} / {e(_fmt_lots(m.get("dealer_5d")))} / {e(_fmt_lots(m.get("dealer_20d")))}</div></div></div><div class="broker-columns"><div><h3>Top Broker Buys</h3>{broker_list(broker.get("top_buys", []), "分點：未追蹤")}</div><div><h3>Top Broker Sells</h3>{broker_list(broker.get("top_sells", []), "分點：未追蹤")}</div></div></article>')
    limitations = ''.join(f'<li>{e(item)}</li>' for item in dict.fromkeys(payload.get("limitations", [])))
    return f'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>台股籌碼雷達｜{e(report_date)}</title><style>{HTML_STYLE}</style></head>
<body><main><header><div class="eyebrow">Daily Chip Radar</div><h1>台股籌碼雷達</h1><p>{e(str(report_date))} · 最後更新 {e(str(generated_at))}</p></header>
<section class="panel"><h2>今日結論</h2><p>今日環境：{_html_signal(env.get("label", "insufficient_data"))} <span class="tag">資料：{e(status_label)}</span></p><p class="muted">研究排序訊號僅供參考，不產生交易指令。</p></section>
<section class="panel"><h2>Data Freshness</h2><div class="status-row">{freshness_cards}</div></section>
<section class="panel"><h2>Global Context</h2><div class="macro-grid">{"".join(macro_cards)}</div></section>
<section><h2>我的追蹤股票</h2><div class="watch-grid">{"".join(watch_cards)}</div></section>
<section class="panel"><h2>Data Limitations</h2><ul>{limitations}</ul></section>
<footer>券商分點 ≠ confirmed beneficial owner · yfinance = market proxy · 本工具僅供研究參考。</footer></main></body></html>
'''


def write_dashboard_json(payload: dict, output_path: Path = RADAR_PATH) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def generate_outputs(flow_paths=FLOW_FILES, broker_path=BROKER_PATH, macro_path=MACRO_PATH, watchlist_path=WATCHLIST_PATH, report_path=REPORT_PATH, html_path=HTML_REPORT_PATH, radar_path=RADAR_PATH) -> dict:
    payload = build_report_payload(flow_paths, broker_path, macro_path, watchlist_path)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path = Path(html_path)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_html(payload), encoding="utf-8")
    write_dashboard_json(payload, Path(radar_path))
    return payload


def generate_report(flow_paths=FLOW_FILES, broker_path=BROKER_PATH, macro_path=MACRO_PATH, output_path=REPORT_PATH) -> Path:
    """Compatibility wrapper used by existing tests and callers."""
    payload = build_report_payload(flow_paths, broker_path, macro_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(payload), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the shared daily Taiwan chip-radar outputs")
    parser.add_argument("--output", default=str(REPORT_PATH), help="Markdown output path")
    parser.add_argument("--html-output", default=str(HTML_REPORT_PATH), help="Self-contained HTML output path")
    parser.add_argument("--radar-output", default=str(RADAR_PATH), help="Dashboard JSON output path")
    args = parser.parse_args()
    payload = generate_outputs(report_path=Path(args.output), html_path=Path(args.html_output), radar_path=Path(args.radar_output))
    print(f"daily outputs -> {args.output}, {args.html_output}, {args.radar_output} ({payload['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
