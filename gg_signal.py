#!/usr/bin/env python3
"""
Bird Theory Signal Generator
สแกนหาสัญญาณจาก benchmarks, largecap, และ crypto จาก tickers.json
"""

import yfinance as yf  # type: ignore[import]
import pandas as pd  # type: ignore[import]
import numpy as np  # type: ignore[import]
from datetime import datetime, timedelta
import json
import warnings
import os

warnings.filterwarnings('ignore')

class BirdSignal:
    def __init__(self, symbol, period="6mo", interval="1d"):
        self.symbol = symbol
        self.period = period
        self.interval = interval
        self.df = None

    def fetch_data(self):
        """ดึงข้อมูลจาก Yahoo Finance (รองรับ .BK สำหรับหุ้นไทย)"""
        try:
            ticker = yf.Ticker(self.symbol)
            self.df = ticker.history(period=self.period, interval=self.interval)
            if self.df.empty:
                raise ValueError(f"No data for {self.symbol}")
            self.df.reset_index(inplace=True)
            # แปลง Date column เป็น timezone-naive ถ้ามี timezone
            if 'Date' in self.df.columns and hasattr(self.df['Date'].dtype, 'tz'):
                self.df['Date'] = pd.to_datetime(self.df['Date']).dt.tz_localize(None)
            elif 'Date' in self.df.columns:
                self.df['Date'] = pd.to_datetime(self.df['Date'])
                if self.df['Date'].dt.tz is not None:
                    self.df['Date'] = self.df['Date'].dt.tz_localize(None)
            return True
        except Exception as e:
            print(f"[ERROR] Error fetching {self.symbol}: {e}")
            return False

    def add_indicators(self):
        """เพิ่ม MA25 และ Volume SMA10"""
        df = self.df.copy()
        df['MA25'] = df['Close'].rolling(25).mean()
        df['Vol_SMA10'] = df['Volume'].rolling(10).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_SMA10']
        self.df = df

    def detect_hammer(self):
        """Hammer: ไส้ล่างยาว, ตัวเล็ก, ไส้บนสั้น/ไม่มี"""
        df = self.df
        body = abs(df['Open'] - df['Close'])
        lower_wick = df['Low'] - df[['Open', 'Close']].min(axis=1)
        upper_wick = df[['Open', 'Close']].max(axis=1) - df['High']
        
        # เงื่อนไข Hammer (แบบ Bird-friendly)
        hammer = (
            (body <= 0.3 * (df['High'] - df['Low'])) &  # ตัวเล็ก
            (lower_wick >= 2 * body) &                 # ไส้ล่างยาว
            (upper_wick <= 0.5 * body) &                # ไส้บนสั้น
            (df['Close'] > df['Open'])                  # เป็นเขียว (ไม่บังคับ แต่ดีกว่า)
        )
        return hammer

    def detect_bullish_engulfing(self):
        """Bullish Engulfing: แท่งเขียววันนี้กลืนแท่งแดงเมื่อวาน"""
        df = self.df
        condition = (
            (df['Close'].shift(1) < df['Open'].shift(1)) &  # วันก่อนแดง
            (df['Close'] > df['Open']) &                   # วันนี้เขียว
            (df['Open'] < df['Close'].shift(1)) &         # เปิดต่ำกว่าปิดเมื่อวาน
            (df['Close'] > df['Open'].shift(1))            # ปิดสูงกว่าเปิดเมื่อวาน
        )
        return condition

    def generate_signals(self):
        """สร้างสัญญาณตาม Bird Theory"""
        if self.df is None or len(self.df) < 30:
            return pd.DataFrame()
        self.add_indicators()
        df = self.df.copy()
        
        # สัญญาณพื้นฐาน
        df['Hammer'] = self.detect_hammer()
        df['Engulfing'] = self.detect_bullish_engulfing()
        
        # Volume Confirmation: Volume >= 1.5x SMA10
        df['Vol_Confirmed'] = df['Vol_Ratio'] >= 1.5
        
        # MA25 Filter: ราคาปิด > MA25 (หรือใกล้เคียง)
        df['MA_Filter'] = df['Close'] >= (df['MA25'] * 0.99)  # ให้เลื่อนได้เล็กน้อย
        
        # สัญญาณรวม
        df['Signal'] = (
            (df['Hammer'] | df['Engulfing']) &
            df['Vol_Confirmed'] &
            df['MA_Filter']
        )
        
        # เก็บเฉพาะแถวที่มีสัญญาณ
        signals = df[df['Signal']].copy()
        if signals.empty:
            return pd.DataFrame()
        
        signals['Entry_Price'] = signals['High'] * 1.002  # เข้าที่ High + 0.2%
        signals['Stop_Loss'] = signals['Low'] * 0.99
        signals['TP1'] = signals['Close'] + 1.5 * (signals['Close'] - signals['Stop_Loss'])
        
        return signals[['Date', 'Close', 'Volume', 'Vol_Ratio', 'Entry_Price', 'Stop_Loss', 'TP1']]

    def run(self):
        if not self.fetch_data():
            return None
        signals = self.generate_signals()
        return signals


def load_symbols_from_json(json_path="tickers.json"):
    """โหลด symbols จาก tickers.json"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'benchmarks': data.get('benchmarks', []),
            'largecap': data.get('largecap', []),
            'crypto': data.get('crypto', []),
            'forex': data.get('forex', [])
        }
    except FileNotFoundError:
        print(f"[ERROR] File not found: {json_path}")
        return {'benchmarks': [], 'largecap': [], 'crypto': [], 'forex': []}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error parsing JSON: {e}")
        return {'benchmarks': [], 'largecap': [], 'crypto': [], 'forex': []}


def scan_symbols(symbols, category_name, period="6mo", interval="1d"):
    """สแกน symbols และหาสัญญาณ"""
    all_signals = []
    
    print(f"\n{'='*70}")
    print(f"[SCAN] Scanning {category_name} ({len(symbols)} symbols)...")
    print(f"{'='*70}")
    
    for sym in symbols:
        print(f"  [SCAN] {sym}...", end=" ", flush=True)
        bot = BirdSignal(sym, period=period, interval=interval)
        sig = bot.run()
        
        if sig is not None and not sig.empty:
            sig['Symbol'] = sym
            sig['Category'] = category_name
            all_signals.append(sig)
            print("[OK] Signal found!")
        else:
            print("[SKIP] No signal")
    
    return all_signals


def main():
    """ฟังก์ชันหลัก"""
    print("="*70)
    print("BIRD THEORY SIGNAL GENERATOR")
    print("="*70)
    
    # โหลด symbols จาก tickers.json
    symbols_dict = load_symbols_from_json()
    
    if not any(symbols_dict.values()):
        print("[ERROR] No symbols found in tickers.json")
        return
    
    all_results = []
    
    # สแกน benchmarks
    if symbols_dict['benchmarks']:
        benchmarks_signals = scan_symbols(
            symbols_dict['benchmarks'], 
            'Benchmarks',
            period="6mo",
            interval="1d"
        )
        all_results.extend(benchmarks_signals)
    
    # สแกน largecap
    if symbols_dict['largecap']:
        largecap_signals = scan_symbols(
            symbols_dict['largecap'],
            'Large-Cap',
            period="6mo",
            interval="1d"
        )
        all_results.extend(largecap_signals)
    
    # สแกน crypto
    if symbols_dict['crypto']:
        crypto_signals = scan_symbols(
            symbols_dict['crypto'],
            'Crypto',
            period="6mo",
            interval="1d"
        )
        all_results.extend(crypto_signals)
    
    # สแกน forex
    if symbols_dict['forex']:
        forex_signals = scan_symbols(
            symbols_dict['forex'],
            'Forex',
            period="6mo",
            interval="1d"
        )
        all_results.extend(forex_signals)
    
    # รวมผลลัพธ์
    if all_results:
        result_df = pd.concat(all_results, ignore_index=True)
        
        # แปลง Date column เป็น timezone-naive ถ้ายังไม่ได้แปลง
        if 'Date' in result_df.columns:
            result_df['Date'] = pd.to_datetime(result_df['Date'])
            if result_df['Date'].dt.tz is not None:
                result_df['Date'] = result_df['Date'].dt.tz_localize(None)
        
        result_df = result_df.sort_values('Date', ascending=False)
        
        # กรองเฉพาะสัญญาณในช่วง 7 วันที่ผ่านมา
        cutoff_date = pd.Timestamp.now().normalize() - timedelta(days=7)
        recent_signals = result_df[result_df['Date'] >= cutoff_date].copy()
        
        print("\n" + "="*70)
        print("BIRD THEORY SIGNALS (Last 7 Days)")
        print("="*70)
        
        if not recent_signals.empty:
            # แสดงผลแยกตาม Category
            for category in ['Benchmarks', 'Large-Cap', 'Crypto', 'Forex']:
                cat_signals = recent_signals[recent_signals['Category'] == category]
                if not cat_signals.empty:
                    print(f"\n[{category}] Signals:")
                    print("-" * 70)
                    display_cols = ['Symbol', 'Date', 'Close', 'Vol_Ratio', 'Entry_Price', 'Stop_Loss', 'TP1']
                    print(cat_signals[display_cols].to_string(index=False))
            
            # บันทึกเป็น CSV
            filename = f"bird_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            recent_signals.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n[SAVED] Saved to {filename}")
            print(f"[INFO] Total signals found: {len(recent_signals)}")
        else:
            print("[INFO] No signals in the last 7 days.")
            
            # แสดงสัญญาณทั้งหมด (ไม่จำกัด 7 วัน)
            if not result_df.empty:
                print("\n[ALL SIGNALS] All Time:")
                print("-" * 70)
                for category in ['Benchmarks', 'Large-Cap', 'Crypto', 'Forex']:
                    cat_signals = result_df[result_df['Category'] == category]
                    if not cat_signals.empty:
                        print(f"\n[{category}] Signals:")
                        display_cols = ['Symbol', 'Date', 'Close', 'Vol_Ratio', 'Entry_Price', 'Stop_Loss', 'TP1']
                        print(cat_signals[display_cols].head(10).to_string(index=False))
                
                filename_all = f"bird_signals_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                result_df.to_csv(filename_all, index=False, encoding='utf-8-sig')
                print(f"\n[SAVED] All signals saved to {filename_all}")
    else:
        print("\n[INFO] No signals found for any symbols.")


if __name__ == "__main__":
    main()

