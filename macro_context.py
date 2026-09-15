# -*- coding: utf-8 -*-
"""Fetch and classify a small set of global market context proxies.

The module deliberately treats yfinance as a convenience provider.  It does
not infer country-of-origin flows or generate trading instructions.
"""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

import pandas as pd


OUTPUT_PATH = Path("docs/data/macro_context.json")
TICKER_MAP = {
    "TSM": {"ticker": "TSM", "name": "台積電 ADR", "direction": 1},
    "SOX": {"ticker": "^SOX", "name": "費城半導體", "direction": 1},
    "USD_TWD": {"ticker": "TWD=X", "name": "USD/TWD", "direction": -1},
    "USD_JPY": {"ticker": "JPY=X", "name": "USD/JPY", "direction": 0},
    "NIKKEI": {"ticker": "^N225", "name": "日經 225", "direction": 1},
    "US10Y": {"ticker": "^TNX", "name": "美國 10Y", "direction": -1},
}
LIMITATIONS = [
    "yfinance is a third-party convenience provider",
    "macro indicators are proxies, not direct country-of-origin Taiwan stock flows",
]


def calculate_percentage_changes(closes: Sequence[float]) -> dict[str, float | None]:
    """Calculate one-day and five-trading-observation changes without fake zeros."""
    values = []
    for value in closes:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number != 0:
            values.append(number)

    def change(old: float, new: float) -> float:
        return round((new / old - 1.0) * 100.0, 4)

    if len(values) < 2:
        return {"change_1d_pct": None, "change_5d_pct": None}
    return {
        "change_1d_pct": change(values[-2], values[-1]),
        "change_5d_pct": change(values[0], values[-1]),
    }


def classify_global_environment(data: Mapping[str, Mapping]) -> dict:
    """Apply a transparent sign-count rule to available one-day changes."""
    score = 0
    available = 0
    for key, config in TICKER_MAP.items():
        if config["direction"] == 0:
            continue
        item = data.get(key, {})
        value = item.get("change_1d_pct")
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value == 0:
            continue
        available += 1
        score += config["direction"] * (1 if value > 0 else -1)

    if available < 3:
        label = "insufficient_data"
    elif score >= 2:
        label = "positive"
    elif score <= -2:
        label = "negative"
    else:
        label = "neutral"

    risk_flags = []
    jpy = data.get("USD_JPY", {})
    try:
        jpy_1d = abs(float(jpy.get("change_1d_pct")))
        jpy_5d = abs(float(jpy.get("change_5d_pct")))
        if jpy_1d >= 1.0 or jpy_5d >= 2.0:
            risk_flags.append("USD/JPY 劇烈波動，carry trade 風險需留意")
    except (TypeError, ValueError):
        pass

    return {"label": label, "score": score, "available_factors": available, "risk_flags": risk_flags}


def classify_stock_chip_status(metrics: Mapping[str, float | None]) -> str:
    """Classify stock chip direction from four deterministic flow aggregates."""
    values = []
    for key in ("foreign_5d", "trust_5d", "foreign_20d", "trust_20d"):
        value = metrics.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number != 0:
            values.append(1 if number > 0 else -1)
    if len(values) < 2:
        return "insufficient_data"
    score = sum(values)
    if score >= 2:
        return "positive"
    if score <= -2:
        return "negative"
    return "neutral"


def _download_history(download: Callable, ticker: str, period: str = "5d") -> pd.Series:
    frame = download(ticker, period=period, interval="1d", auto_adjust=False, progress=False, threads=False)
    if frame is None or frame.empty:
        return pd.Series(dtype="float64")
    close = frame["Close"] if "Close" in frame.columns else frame.iloc[:, -1]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return pd.to_numeric(close, errors="coerce").dropna().tail(5)


def fetch_macro_context(period: str = "5d", downloader: Callable | None = None) -> dict:
    """Fetch every ticker independently so one outage becomes a partial result."""
    if downloader is None:
        try:
            import yfinance as yf
        except ImportError as exc:
            error = f"yfinance unavailable: {exc}"
            return {
                "as_of": datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat(),
                "source": "yfinance",
                "status": "failed",
                "data": {key: {"ticker": value["ticker"], "name": value["name"], "status": "missing", "error": error} for key, value in TICKER_MAP.items()},
                "limitations": LIMITATIONS,
            }
        downloader = yf.download

    result = {}
    dates = []
    for key, config in TICKER_MAP.items():
        try:
            series = _download_history(downloader, config["ticker"], period)
            if len(series) < 1:
                raise ValueError("no close observations")
            changes = calculate_percentage_changes(series.tolist())
            latest_date = pd.Timestamp(series.index[-1]).date().isoformat()
            dates.append(latest_date)
            result[key] = {
                "ticker": config["ticker"],
                "name": config["name"],
                "status": "ok",
                "latest_date": latest_date,
                "close": round(float(series.iloc[-1]), 6),
                **changes,
            }
        except Exception as exc:  # one provider failure must not erase other proxies
            result[key] = {
                "ticker": config["ticker"],
                "name": config["name"],
                "status": "missing",
                "latest_date": None,
                "close": None,
                "change_1d_pct": None,
                "change_5d_pct": None,
                "error": str(exc),
            }

    ok_count = sum(item["status"] == "ok" for item in result.values())
    status = "ok" if ok_count == len(TICKER_MAP) else "partial" if ok_count else "failed"
    payload = {
        "as_of": max(dates) if dates else datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat(),
        "source": "yfinance",
        "status": status,
        "successful_tickers": ok_count,
        "total_tickers": len(TICKER_MAP),
        "data": result,
        "environment": classify_global_environment(result),
        "limitations": LIMITATIONS,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch market context proxies for the daily report")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--period", default="5d")
    args = parser.parse_args()
    payload = fetch_macro_context(args.period)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"macro_context: {payload['status']} ({payload['successful_tickers']}/{payload['total_tickers']}) -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
