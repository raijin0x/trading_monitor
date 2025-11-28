#!/usr/bin/env python3
"""
Auto screener สำหรับ Mid-Cap, Large-Cap และ Forex จาก Yahoo Finance

- Mid-Cap/Large-Cap: เรียก endpoint predefined: MOST_ACTIVES
- Forex: ใช้ yfinance ดึงข้อมูล Forex pairs และกรองตาม volume/volatility
- สร้าง:
    - tickers_midcap.txt / tickers_largecap.txt / tickers_forex.txt
    - Experiment Details/Candidate_MidCaps.csv / Candidate_LargeCaps.csv / Candidate_Forex.csv

อ้างอิง endpoint:
https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?count=25&scrIds=most_actives

การใช้งาน:
    python screener.py              # screen ทั้ง mid-cap และ large-cap
    python screener.py --type midcap    # screen เฉพาะ mid-cap
    python screener.py --type largecap  # screen เฉพาะ large-cap
    python screener.py --type forex     # screen เฉพาะ forex
    python screener.py --type both      # screen ทั้งสอง (default)
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd  # type: ignore[import]
import requests  # type: ignore[import]
import yfinance as yf  # type: ignore[import]


ROOT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = ROOT_DIR / "Experiment Details"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

OUT_TXT_MIDCAP = ROOT_DIR / "tickers_midcap.txt"
OUT_CSV_MIDCAP = EXPERIMENT_DIR / "Candidate_MidCaps.csv"

OUT_TXT_LARGECAP = ROOT_DIR / "tickers_largecap.txt"
OUT_CSV_LARGECAP = EXPERIMENT_DIR / "Candidate_LargeCaps.csv"

OUT_TXT_FOREX = ROOT_DIR / "tickers_forex.txt"
OUT_CSV_FOREX = EXPERIMENT_DIR / "Candidate_Forex.csv"

YH_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"

# Major Forex Pairs (Yahoo Finance format: EURUSD=X)
MAJOR_FOREX_PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURGBP=X",
    "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "EURAUD=X",
    "EURCAD=X", "GBPAUD=X", "GBPCAD=X", "AUDCAD=X",
    "AUDNZD=X", "CADJPY=X", "CHFJPY=X", "EURCHF=X"
]


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


def screen_forex_pairs() -> pd.DataFrame:
    """สแกน Forex pairs และกรองตาม volatility."""
    print("Fetching Forex data from Yahoo Finance...")
    
    rows: List[Dict[str, Any]] = []
    
    for pair in MAJOR_FOREX_PAIRS:
        try:
            ticker = yf.Ticker(pair)
            hist = ticker.history(period="5d", interval="1d")
            
            if hist.empty or len(hist) < 2:
                print(f"  [SKIP] {pair}: No data")
                continue
            
            # คำนวณ metrics
            current_price = hist['Close'].iloc[-1]
            # Forex ไม่มี volume แบบหุ้น แต่ yfinance อาจมีค่าเป็น 0 หรือ NaN
            avg_volume = hist['Volume'].mean() if 'Volume' in hist.columns and not hist['Volume'].isna().all() else 0
            
            # คำนวณ volatility (ATR-like: average true range)
            high_low = (hist['High'] - hist['Low']).mean()
            volatility_pct = (high_low / current_price) * 100 if current_price > 0 else 0
            
            # คำนวณ price change (5-day)
            price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            
            # แปลง pair name (EURUSD=X -> EURUSD)
            pair_name = pair.replace("=X", "")
            
            rows.append({
                "Ticker": pair_name,
                "Yahoo_Symbol": pair,
                "Current_Price": round(current_price, 5),
                "Avg_Volume": int(avg_volume) if avg_volume and not pd.isna(avg_volume) else 0,
                "Volatility_%": round(volatility_pct, 3),
                "Price_Change_5d_%": round(price_change, 2)
            })
            print(f"  [OK] {pair_name}: Price={current_price:.5f}, Volatility={volatility_pct:.3f}%")
            
        except Exception as e:
            print(f"  [ERROR] {pair}: {str(e)}")
            continue
    
    df = pd.DataFrame(rows)
    if df.empty:
        print("No Forex data retrieved.")
        return pd.DataFrame(columns=["Ticker", "Yahoo_Symbol"])
    
    # กรองตามเงื่อนไข:
    # 1. Volatility >= 0.1% (Forex มี volatility ต่ำกว่า stocks)
    # 2. ไม่กรอง Volume เพราะ Forex ไม่มี volume แบบหุ้น
    df = df[df["Volatility_%"] >= 0.1]
    
    # เรียงตาม volatility (สูงสุดก่อน)
    df = df.sort_values("Volatility_%", ascending=False)
    df = df.reset_index(drop=True)
    
    print(f"Passed Forex filters: {len(df)} pairs")
    return df


def save_forex_results(df: pd.DataFrame) -> None:
    """บันทึกผล Forex ลงไฟล์ text + CSV."""
    if df.empty:
        print("No Forex pairs to save.")
        return
    
    # ใช้ Yahoo_Symbol สำหรับ tickers_forex.txt (พร้อม =X)
    tickers = df["Yahoo_Symbol"].tolist()
    
    # เขียนไฟล์ text
    OUT_TXT_FOREX.write_text("\n".join(tickers), encoding="utf-8")
    print(f"Saved {len(tickers)} Forex pairs to {OUT_TXT_FOREX}")
    
    # เขียนไฟล์ CSV (มีข้อมูลเพิ่มเติม)
    df.to_csv(OUT_CSV_FOREX, index=False)
    print(f"Saved Candidate_Forex.csv to {OUT_CSV_FOREX}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Screen Mid-Cap, Large-Cap stocks และ Forex pairs จาก Yahoo Finance"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["midcap", "largecap", "forex", "both"],
        default="both",
        help="ประเภทที่จะ screen (default: both)",
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
    
    if args.type == "forex":
        print("\n" + "=" * 50)
        print("Screening Forex Pairs...")
        print("=" * 50)
        df_forex = screen_forex_pairs()
        save_forex_results(df_forex)

    print("\n[OK] Screening completed!")


if __name__ == "__main__":
    main()
