#!/usr/bin/env python3
"""
ดึงราคาและปริมาณการซื้อขาย (Close, Volume) สำหรับ tickers ใน tickers.json

การใช้งาน:
    python fetch_prices.py

สคริปต์จะ:
- อ่านไฟล์ tickers.json → ดึงรายการ "benchmarks"
- ใช้ yfinance ดาวน์โหลดราคาวันล่าสุด
- แสดงตาราง: Ticker, Close, Volume
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd  # type: ignore[import]
import yfinance as yf  # type: ignore[import]


ROOT_DIR = Path(__file__).resolve().parent
TICKERS_JSON = ROOT_DIR / "tickers.json"


def load_benchmarks_from_json() -> list[str]:
    """อ่าน tickers.json แล้วคืนลิสต์ benchmarks เป็นตัวพิมพ์ใหญ่"""
    if not TICKERS_JSON.exists():
        raise SystemExit(f"tickers.json not found at {TICKERS_JSON}")

    with TICKERS_JSON.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    arr = data.get("benchmarks")
    if not isinstance(arr, list):
        raise SystemExit("tickers.json: 'benchmarks' ต้องเป็นลิสต์ของ ticker")

    seen: set[str] = set()
    out: list[str] = []
    for t in arr:
        if not isinstance(t, str):
            continue
        up = t.strip().upper()
        if not up or up in seen:
            continue
        seen.add(up)
        out.append(up)
    return out


def fetch_latest_close_volume(tickers: list[str]) -> pd.DataFrame:
    """ใช้ yfinance ดึง Close/Volume ล่าสุดของ ticker ในลิสต์"""
    if not tickers:
        return pd.DataFrame(columns=["Ticker", "Close", "Volume"])

    print(f"Downloading latest prices for: {', '.join(tickers)}")
    df = yf.download(" ".join(tickers), period="1d", interval="1d", progress=False)
    if df.empty:
        print("No data returned from yfinance.")
        return pd.DataFrame(columns=["Ticker", "Close", "Volume"])

    # จัดการกรณี MultiIndex columns (หลาย ticker)
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"].iloc[-1]
        volume = df["Volume"].iloc[-1]
        out = pd.DataFrame(
            {
                "Ticker": close.index.astype(str),
                "Close": close.values,
                "Volume": volume.values,
            }
        )
    else:
        # single ticker case
        last = df.iloc[-1]
        out = pd.DataFrame(
            {
                "Ticker": [tickers[0]],
                "Close": [last.get("Close", float("nan"))],
                "Volume": [last.get("Volume", float("nan"))],
            }
        )

    out["Close"] = pd.to_numeric(out["Close"], errors="coerce")
    out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
    return out.sort_values("Ticker").reset_index(drop=True)


def main() -> None:
    benchmarks = load_benchmarks_from_json()
    df = fetch_latest_close_volume(benchmarks)
    if df.empty:
        return

    # แสดงผลแบบสวย ๆ
    print("\nTicker   Close        Volume")
    print("-" * 32)
    for _, row in df.iterrows():
        t = str(row["Ticker"])
        c = row["Close"]
        v = row["Volume"]
        close_str = f"{c:,.2f}" if pd.notna(c) else "N/A"
        vol_str = f"{int(v):,}" if pd.notna(v) else "N/A"
        print(f"{t:<6}  {close_str:>10}  {vol_str:>12}")


if __name__ == "__main__":
    main()


