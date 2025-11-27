#!/usr/bin/env python3
"""
Monitor ราคาหุ้นแบบ Real-time
แสดงราคา, การเปลี่ยนแปลง, Volume, High, Low สำหรับ tickers ใน tickers.json

การใช้งาน:
    python monitor.py              # แสดงครั้งเดียว
    python monitor.py --refresh 30  # อัปเดตทุก 30 วินาที
    python monitor.py --watch      # อัปเดตทุก 10 วินาที (default)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
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


def fetch_stock_data(tickers: list[str]) -> pd.DataFrame:
    """ดึงข้อมูลหุ้นล่าสุด: Price, Change, %Change, Volume, High, Low"""
    if not tickers:
        return pd.DataFrame()

    results = []

    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # ดึงราคาปัจจุบัน
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or float("nan")
            prev_close = info.get("previousClose") or current_price

            # คำนวณ change
            if pd.notna(current_price) and pd.notna(prev_close):
                change = current_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close != 0 else float("nan")
            else:
                change = float("nan")
                change_pct = float("nan")

            # ดึงข้อมูลอื่น ๆ
            volume = info.get("volume") or info.get("averageVolume") or float("nan")
            high = info.get("dayHigh") or info.get("regularMarketDayHigh") or float("nan")
            low = info.get("dayLow") or info.get("regularMarketDayLow") or float("nan")

            results.append({
                "Ticker": ticker,
                "Price": current_price,
                "Change": change,
                "Change %": change_pct,
                "Volume": volume,
                "High": high,
                "Low": low,
            })

        except Exception as e:
            # ถ้า .info ไม่ได้ ให้ลองใช้ download
            try:
                df = yf.download(ticker, period="5d", interval="1d", progress=False, timeout=10)
                if not df.empty and len(df) > 0:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest

                    current_price = latest.get("Close", float("nan"))
                    prev_close = prev.get("Close", current_price)

                    if pd.notna(current_price) and pd.notna(prev_close):
                        change = current_price - prev_close
                        change_pct = (change / prev_close * 100) if prev_close != 0 else float("nan")
                    else:
                        change = float("nan")
                        change_pct = float("nan")

                    results.append({
                        "Ticker": ticker,
                        "Price": current_price,
                        "Change": change,
                        "Change %": change_pct,
                        "Volume": latest.get("Volume", float("nan")),
                        "High": latest.get("High", float("nan")),
                        "Low": latest.get("Low", float("nan")),
                    })
                else:
                    # ไม่มีข้อมูลเลย
                    results.append({
                        "Ticker": ticker,
                        "Price": float("nan"),
                        "Change": float("nan"),
                        "Change %": float("nan"),
                        "Volume": float("nan"),
                        "High": float("nan"),
                        "Low": float("nan"),
                    })
            except Exception:
                # ไม่สามารถดึงข้อมูลได้
                results.append({
                    "Ticker": ticker,
                    "Price": float("nan"),
                    "Change": float("nan"),
                    "Change %": float("nan"),
                    "Volume": float("nan"),
                    "High": float("nan"),
                    "Low": float("nan"),
                })

    return pd.DataFrame(results)


def format_price(value: float | None) -> str:
    """จัดรูปแบบราคา"""
    if pd.isna(value) or value is None:
        return "N/A"
    return f"{value:,.2f}"


def format_change(value: float | None) -> str:
    """จัดรูปแบบการเปลี่ยนแปลง พร้อมสี"""
    if pd.isna(value) or value is None:
        return "N/A"

    sign = "+" if value >= 0 else ""
    color_code = ""
    reset_code = ""

    # ใช้ ANSI color codes ถ้า terminal รองรับ
    try:
        if sys.stdout.isatty():
            if value > 0:
                color_code = "\033[92m"  # เขียว
            elif value < 0:
                color_code = "\033[91m"  # แดง
            reset_code = "\033[0m"
    except Exception:
        pass

    return f"{color_code}{sign}{value:,.2f}{reset_code}"


def format_change_pct(value: float | None) -> str:
    """จัดรูปแบบเปอร์เซ็นต์การเปลี่ยนแปลง"""
    if pd.isna(value) or value is None:
        return "N/A"

    sign = "+" if value >= 0 else ""
    color_code = ""
    reset_code = ""

    try:
        if sys.stdout.isatty():
            if value > 0:
                color_code = "\033[92m"  # เขียว
            elif value < 0:
                color_code = "\033[91m"  # แดง
            reset_code = "\033[0m"
    except Exception:
        pass

    return f"{color_code}{sign}{value:.2f}%{reset_code}"


def format_volume(value: float | None) -> str:
    """จัดรูปแบบ volume"""
    if pd.isna(value) or value is None:
        return "N/A"

    v = int(value)
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    elif v >= 1_000:
        return f"{v/1_000:.2f}K"
    return f"{v:,}"


def display_table(df: pd.DataFrame) -> None:
    """แสดงตารางข้อมูลหุ้น"""
    if df.empty:
        print("No data available.")
        return

    # Header
    print("\n" + "=" * 100)
    print(f"Stock Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    print(f"{'Ticker':<8} {'Price':>10} {'Change':>12} {'Change %':>10} {'Volume':>12} {'High':>10} {'Low':>10}")
    print("-" * 100)

    # Data rows
    for _, row in df.iterrows():
        ticker = str(row["Ticker"])
        price = format_price(row["Price"])
        change = format_change(row["Change"])
        change_pct = format_change_pct(row["Change %"])
        volume = format_volume(row["Volume"])
        high = format_price(row["High"])
        low = format_price(row["Low"])

        print(f"{ticker:<8} {price:>10} {change:>12} {change_pct:>10} {volume:>12} {high:>10} {low:>10}")

    print("=" * 100)


def clear_screen() -> None:
    """ล้างหน้าจอ"""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor ราคาหุ้นแบบ Real-time")
    parser.add_argument(
        "--refresh",
        type=int,
        metavar="SECONDS",
        help="อัปเดตข้อมูลทุก N วินาที (default: 10)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="เปิดโหมด watch (อัปเดตทุก 10 วินาที)",
    )

    args = parser.parse_args()

    tickers = load_benchmarks_from_json()
    if not tickers:
        print("No tickers found in tickers.json", file=sys.stderr)
        return

    refresh_interval = args.refresh if args.refresh else (10 if args.watch else None)

    try:
        while True:
            df = fetch_stock_data(tickers)
            display_table(df)

            if refresh_interval is None:
                break

            print(f"\nRefreshing in {refresh_interval} seconds... (Press Ctrl+C to stop)")
            time.sleep(refresh_interval)
            clear_screen()

    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user.")


if __name__ == "__main__":
    main()
