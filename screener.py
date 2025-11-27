#!/usr/bin/env python3
"""
Auto screener สำหรับ Mid-Cap และ Large-Cap จาก Yahoo Finance "Most Actives" screener

- เรียก endpoint predefined: MOST_ACTIVES  (25 ตัวที่เทรดเยอะสุดในวันนั้น)
- กรอง mid-cap (marketCap ~ 2–10B) หรือ large-cap (marketCap > 10B)
- สร้าง:
    - tickers_midcap.txt / tickers_largecap.txt
    - Experiment Details/Candidate_MidCaps.csv / Candidate_LargeCaps.csv

อ้างอิง endpoint:
https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?count=25&scrIds=most_actives

การใช้งาน:
    python screener.py              # screen ทั้ง mid-cap และ large-cap
    python screener.py --type midcap    # screen เฉพาะ mid-cap
    python screener.py --type largecap  # screen เฉพาะ large-cap
    python screener.py --type both      # screen ทั้งสอง (default)
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd  # type: ignore[import]
import requests  # type: ignore[import]


ROOT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = ROOT_DIR / "Experiment Details"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

OUT_TXT_MIDCAP = ROOT_DIR / "tickers_midcap.txt"
OUT_CSV_MIDCAP = EXPERIMENT_DIR / "Candidate_MidCaps.csv"

OUT_TXT_LARGECAP = ROOT_DIR / "tickers_largecap.txt"
OUT_CSV_LARGECAP = EXPERIMENT_DIR / "Candidate_LargeCaps.csv"

YH_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"


def fetch_most_actives(count: int = 25) -> List[Dict[str, Any]]:
    """ดึงรายการ Most Actives จาก Yahoo Finance screener."""
    params = {"count": count, "scrIds": "most_actives"}
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(YH_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    try:
        quotes = data["finance"]["result"][0]["quotes"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"Unexpected JSON structure from Yahoo screener: {exc}")

    return quotes or []


def screen_midcap_from_most_actives() -> pd.DataFrame:
    """คัด mid-cap จากลิสต์ Most Actives (ดึงไม่เยอะ แต่เน้นของที่เคลื่อนไหวแรงวันนี้)."""
    print("Fetching MOST_ACTIVES from Yahoo Finance screener …")
    quotes = fetch_most_actives(count=50)  # ขยายเป็น 50 ถ้า endpoint รองรับ
    if not quotes:
        print("No quotes returned from Yahoo.")
        return pd.DataFrame(columns=["Ticker"])

    rows: List[Dict[str, Any]] = []
    for q in quotes:
        sym = q.get("symbol")
        mc = q.get("marketCap")
        vol = q.get("regularMarketVolume") or q.get("dayvolume")
        exch = q.get("exchange")
        if not sym or mc is None:
            continue
        rows.append(
            {
                "Ticker": str(sym).upper(),
                "marketCap": mc,
                "volume": vol or 0,
                "exchange": exch or "",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        print("No usable data in Most Actives response.")
        return pd.DataFrame(columns=["Ticker"])

    # mid-cap filter: 2B–10B
    df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["marketCap"])

    df = df[df["marketCap"].between(2_000_000_000, 10_000_000_000)]

    # เงื่อนไขเสริม: volume > 5M (เผื่ออีกชั้น แม้ endpointมีกรอง dayvolume อยู่แล้ว)
    df = df[df["volume"] > 5_000_000]

    df = df.dropna(subset=["Ticker"])
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df = df.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)

    print(f"Passed mid-cap filters: {len(df)} tickers")
    return df[["Ticker"]]


def screen_largecap_from_most_actives() -> pd.DataFrame:
    """คัด large-cap จากลิสต์ Most Actives (marketCap > 10B)."""
    print("Fetching MOST_ACTIVES from Yahoo Finance screener …")
    quotes = fetch_most_actives(count=50)  # ขยายเป็น 50 ถ้า endpoint รองรับ
    if not quotes:
        print("No quotes returned from Yahoo.")
        return pd.DataFrame(columns=["Ticker"])

    rows: List[Dict[str, Any]] = []
    for q in quotes:
        sym = q.get("symbol")
        mc = q.get("marketCap")
        vol = q.get("regularMarketVolume") or q.get("dayvolume")
        exch = q.get("exchange")
        if not sym or mc is None:
            continue
        rows.append(
            {
                "Ticker": str(sym).upper(),
                "marketCap": mc,
                "volume": vol or 0,
                "exchange": exch or "",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        print("No usable data in Most Actives response.")
        return pd.DataFrame(columns=["Ticker"])

    # large-cap filter: > 10B
    df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["marketCap"])

    df = df[df["marketCap"] > 10_000_000_000]

    # เงื่อนไขเสริม: volume > 10M (large-cap ควรมี volume สูงกว่า)
    df = df[df["volume"] > 10_000_000]

    df = df.dropna(subset=["Ticker"])
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df = df.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)

    print(f"Passed large-cap filters: {len(df)} tickers")
    return df[["Ticker"]]


def save_midcap_results(df: pd.DataFrame) -> None:
    """บันทึกผล mid-cap ลงไฟล์ text + CSV."""
    if df.empty:
        print("No mid-cap tickers to save.")
        return

    tickers = df["Ticker"].tolist()

    # เขียนไฟล์ text
    OUT_TXT_MIDCAP.write_text("\n".join(tickers), encoding="utf-8")
    print(f"Saved {len(tickers)} mid-cap tickers to {OUT_TXT_MIDCAP}")

    # เขียนไฟล์ CSV
    df.to_csv(OUT_CSV_MIDCAP, index=False)
    print(f"Saved Candidate_MidCaps.csv to {OUT_CSV_MIDCAP}")


def save_largecap_results(df: pd.DataFrame) -> None:
    """บันทึกผล large-cap ลงไฟล์ text + CSV."""
    if df.empty:
        print("No large-cap tickers to save.")
        return

    tickers = df["Ticker"].tolist()

    # เขียนไฟล์ text
    OUT_TXT_LARGECAP.write_text("\n".join(tickers), encoding="utf-8")
    print(f"Saved {len(tickers)} large-cap tickers to {OUT_TXT_LARGECAP}")

    # เขียนไฟล์ CSV
    df.to_csv(OUT_CSV_LARGECAP, index=False)
    print(f"Saved Candidate_LargeCaps.csv to {OUT_CSV_LARGECAP}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Screen Mid-Cap และ Large-Cap stocks จาก Yahoo Finance Most Actives"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["midcap", "largecap", "both"],
        default="both",
        help="ประเภทหุ้นที่จะ screen (default: both)",
    )

    args = parser.parse_args()

    if args.type in ["midcap", "both"]:
        print("\n" + "=" * 50)
        print("Screening Mid-Cap Stocks...")
        print("=" * 50)
        df_midcap = screen_midcap_from_most_actives()
        save_midcap_results(df_midcap)

    if args.type in ["largecap", "both"]:
        print("\n" + "=" * 50)
        print("Screening Large-Cap Stocks...")
        print("=" * 50)
        df_largecap = screen_largecap_from_most_actives()
        save_largecap_results(df_largecap)

    print("\n✅ Screening completed!")


if __name__ == "__main__":
    main()
