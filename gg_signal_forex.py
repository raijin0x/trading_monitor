#!/usr/bin/env python3
"""
Bird Theory Signal Generator สำหรับ Forex
ใช้ MT5 API สำหรับข้อมูลจริง + Volume จริง + ส่ง Order ได้
พร้อม Telegram Notifications
"""

import pandas as pd  # type: ignore[import]
import numpy as np  # type: ignore[import]
from datetime import datetime, timedelta
import json
import warnings
import os

warnings.filterwarnings('ignore')

# Load .env file if available
try:
    from dotenv import load_dotenv  # type: ignore[import]
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use environment variables directly

# MT5 imports
try:
    import MetaTrader5 as mt5  # type: ignore[import]
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARN] MetaTrader5 not installed. Install with: pip install MetaTrader5")

# Telegram imports
try:
    import requests  # type: ignore[import]
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[WARN] requests not installed. Install with: pip install requests")


class TelegramNotifier:
    """ส่งแจ้งเตือนผ่าน Telegram"""
    
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled and TELEGRAM_AVAILABLE:
            print("[INFO] Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    
    def send_message(self, message):
        """ส่งข้อความผ่าน Telegram"""
        if not self.enabled or not TELEGRAM_AVAILABLE:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[WARN] Telegram send failed: {e}")
            return False
    
    def send_signal(self, signal_data):
        """ส่งสัญญาณ Forex ผ่าน Telegram"""
        if not self.enabled:
            return False
        
        pair = signal_data.get('Pair', 'N/A')
        entry = signal_data.get('Entry', 0)
        sl = signal_data.get('SL', 0)
        rr1 = signal_data.get('RR1', 0)
        rr2 = signal_data.get('RR2', 0)
        date = signal_data.get('Date', 'N/A')
        
        message = f"""
<b>🎯 FOREX SIGNAL DETECTED</b>

<b>Pair:</b> {pair}
<b>Time:</b> {date}
<b>Entry:</b> {entry:.5f}
<b>Stop Loss:</b> {sl:.5f}
<b>Take Profit 1:</b> {rr1:.5f} (1.5R)
<b>Take Profit 2:</b> {rr2:.5f} (3.0R)

<i>Bird Theory Signal Generator</i>
        """.strip()
        
        return self.send_message(message)


class MT5DataFetcher:
    """ดึงข้อมูลจาก MT5"""
    
    def __init__(self, login=None, password=None, server=None):
        self.connected = False
        if not MT5_AVAILABLE:
            return
        
        # พยายามเชื่อมต่อ MT5
        if not mt5.initialize():
            print(f"[ERROR] MT5 initialization failed: {mt5.last_error()}")
            return
        
        # Login ถ้ามีข้อมูล
        if login and password and server:
            authorized = mt5.login(login, password=password, server=server)
            if not authorized:
                print(f"[ERROR] MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return
        
        self.connected = True
        print("[OK] MT5 connected successfully")
    
    def fetch_data(self, symbol, timeframe=mt5.TIMEFRAME_H1, count=2000):
        """ดึงข้อมูล OHLCV จาก MT5"""
        if not self.connected:
            return None
        
        try:
            # ดึงข้อมูล
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            
            if rates is None or len(rates) == 0:
                return None
            
            # แปลงเป็น DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={
                'time': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'tick_volume': 'Volume',
                'real_volume': 'Real_Volume'
            }, inplace=True)
            
            # ใช้ real_volume ถ้ามี ไม่เช่นนั้นใช้ tick_volume
            if 'Real_Volume' in df.columns:
                df['Volume'] = df['Real_Volume'].fillna(df['Volume'])
            
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        except Exception as e:
            print(f"[ERROR] MT5 fetch error for {symbol}: {e}")
            return None
    
    def get_symbol_info(self, symbol):
        """ดึงข้อมูล symbol info (spread, point, etc.)"""
        if not self.connected:
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return None
            return {
                'spread': symbol_info.spread,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'trade_mode': symbol_info.trade_mode
            }
        except:
            return None
    
    def place_order(self, symbol, order_type, volume, price=None, sl=None, tp=None, comment="Bird Signal"):
        """ส่ง Order ผ่าน MT5"""
        if not self.connected:
            print("[ERROR] MT5 not connected")
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(f"[ERROR] Symbol {symbol} not found")
                return None
            
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    print(f"[ERROR] Failed to select {symbol}")
                    return None
            
            # กำหนด request
            if order_type == "BUY":
                trade_type = mt5.ORDER_TYPE_BUY
                if price is None:
                    price = mt5.symbol_info_tick(symbol).ask
            elif order_type == "SELL":
                trade_type = mt5.ORDER_TYPE_SELL
                if price is None:
                    price = mt5.symbol_info_tick(symbol).bid
            else:
                print(f"[ERROR] Invalid order type: {order_type}")
                return None
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": trade_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_fill": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"[ERROR] Order failed: {result.retcode} - {result.comment}")
                return None
            
            print(f"[OK] Order placed: {order_type} {volume} {symbol} at {price}")
            return result
        
        except Exception as e:
            print(f"[ERROR] Order error: {e}")
            return None
    
    def shutdown(self):
        """ปิดการเชื่อมต่อ MT5"""
        if self.connected and MT5_AVAILABLE:
            mt5.shutdown()
            self.connected = False


class BirdSignalForex:
    def __init__(self, symbol, mt5_fetcher=None, period_days=60, interval="1h"):
        self.symbol = symbol  # MT5 symbol format: "EURUSD"
        self.mt5_fetcher = mt5_fetcher
        self.period_days = period_days
        self.interval = interval
        self.df = None
        
        # แปลง interval เป็น MT5 timeframe
        self.mt5_timeframe = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
        }.get(interval, mt5.TIMEFRAME_H1)

    def fetch_data(self):
        """ดึงข้อมูล Forex จาก MT5"""
        if not self.mt5_fetcher or not self.mt5_fetcher.connected:
            print(f"  [WARN] MT5 not connected, skipping {self.symbol}")
            return False
        
        try:
            # คำนวณจำนวน bars ที่ต้องการ (ประมาณ)
            bars_per_day = {
                "1m": 1440, "5m": 288, "15m": 96, "30m": 48,
                "1h": 24, "4h": 6, "1d": 1
            }.get(self.interval, 24)
            
            count = int(bars_per_day * self.period_days)
            count = min(count, 2000)  # MT5 limit
            
            self.df = self.mt5_fetcher.fetch_data(self.symbol, self.mt5_timeframe, count)
            
            if self.df is None or self.df.empty or len(self.df) < 50:
                return False
            
            return True
        
        except Exception as e:
            print(f"  [WARN] Error fetching {self.symbol}: {e}")
            return False

    def add_indicators(self):
        """เพิ่ม indicators สำหรับ Forex"""
        df = self.df.copy()
        
        # ใช้ EMA21 (นิยมใน Forex + ใกล้กับแนวคิด Bird)
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # Volume indicators (MT5 มี Volume จริง)
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        # หลีกเลี่ยงการหารด้วย 0
        df['Vol_Ratio'] = df['Volume'] / df['Vol_SMA20'].replace(0, np.nan)
        df['Vol_Ratio'] = df['Vol_Ratio'].fillna(1.0)  # ถ้าไม่มี volume ให้ใช้ 1.0
        
        self.df = df

    def detect_price_action_signals(self):
        """ตรวจจับ price action patterns สำหรับ Forex"""
        df = self.df.copy()
        
        # 1. Bullish Pin Bar (แทน Hammer — ใช้บ่อยใน Forex)
        body = abs(df['Open'] - df['Close'])
        lower_wick = df['Low'] - df[['Open', 'Close']].min(axis=1)
        upper_wick = df[['Open', 'Close']].max(axis=1) - df['High']
        
        pin_bar = (
            (body <= 0.3 * (df['High'] - df['Low'])) &
            (lower_wick >= 2 * body) &
            (upper_wick <= 0.5 * body)
        )
        
        # 2. Bullish Break of Structure (BOS)
        # ราคา Break High ของ Swing 3 แท่งก่อนหน้า
        df['Prev_High_3'] = df['High'].rolling(4).max().shift(1)
        bos = df['High'] > df['Prev_High_3']
        
        # 3. Demand Zone Re-test (ราคาดีดตัวจากโซนเดิม)
        df['Low_5'] = df['Low'].rolling(5).min()
        demand_retest = (
            (df['Low'] <= df['Low_5'].shift(1) * 1.002) &  # แตะโซน
            (df['Close'] > df['Open'])                      # ปิดเขียว
        )
        
        df['PinBar'] = pin_bar
        df['BOS'] = bos
        df['Demand_Retest'] = demand_retest
        
        return df

    def generate_signals(self):
        """สร้างสัญญาณตาม Bird Theory สำหรับ Forex"""
        if not self.fetch_data():
            return pd.DataFrame()
        
        self.add_indicators()
        df = self.detect_price_action_signals()
        
        # ✅ เงื่อนไข Bird Style สำหรับ Forex:
        signal = (
            (df['PinBar'] | df['BOS'] | df['Demand_Retest']) &
            (df['Vol_Ratio'] >= 1.3) &          # Volume 1.3x ขึ้นไป
            (df['Close'] > df['EMA21']) &       # ราคาอยู่เหนือ EMA21
            (df['Close'] > df['Open'])          # แท่งเขียว (เพิ่มความน่าเชื่อถือ)
        )
        
        signals = df[signal].copy()
        if signals.empty:
            return pd.DataFrame()
        
        # ดึง symbol info สำหรับคำนวณ pip
        symbol_info = self.mt5_fetcher.get_symbol_info(self.symbol) if self.mt5_fetcher else None
        point = symbol_info['point'] if symbol_info else 0.0001
        
        # จุดเข้า: กรณี Pin Bar → เข้าที่ High + spread
        # กรณี BOS → เข้าทันทีเมื่อ Break
        if point > 0:
            signals['Entry'] = np.where(
                signals['PinBar'], 
                signals['High'] + (point * 5),   # + 5 pips
                signals['High'] + (point * 2)   # + 2 pips
            )
            signals['SL'] = signals['Low'] - (point * 5)  # - 5 pips
        else:
            # Fallback สำหรับ symbol ที่ไม่มี point info
            signals['Entry'] = np.where(
                signals['PinBar'], 
                signals['High'] * 1.0005,
                signals['High'] * 1.0002
            )
            signals['SL'] = signals['Low'] * 0.9995
        
        signals['RR1'] = signals['Entry'] + 1.5 * (signals['Entry'] - signals['SL'])
        signals['RR2'] = signals['Entry'] + 3.0 * (signals['Entry'] - signals['SL'])
        
        # ใช้ Date column
        result_cols = ['Date', 'Close', 'Volume', 'Vol_Ratio', 'Entry', 'SL', 'RR1', 'RR2']
        available_cols = [col for col in result_cols if col in signals.columns]
        
        return signals[available_cols]

    def run(self):
        """รันการสแกนและคืนค่าสัญญาณ"""
        signals = self.generate_signals()
        return signals


def load_forex_from_json(json_path="tickers.json"):
    """โหลด Forex symbols จาก tickers.json"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('forex', [])
    except FileNotFoundError:
        print(f"[ERROR] File not found: {json_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error parsing JSON: {e}")
        return []


def scan_forex_symbols(symbols, mt5_fetcher, telegram_notifier=None, period_days=60, interval="1h", auto_trade=False, trade_volume=0.01):
    """สแกน Forex symbols และหาสัญญาณ"""
    all_signals = []
    
    print(f"\n{'='*70}")
    print(f"Scanning Forex Pairs ({len(symbols)} pairs)...")
    print(f"{'='*70}")
    
    for sym in symbols:
        # แปลง symbol format (EURUSD=X -> EURUSD)
        mt5_symbol = sym.replace("=X", "")
        
        print(f"  {mt5_symbol}...", end=" ", flush=True)
        bot = BirdSignalForex(mt5_symbol, mt5_fetcher=mt5_fetcher, period_days=period_days, interval=interval)
        sig = bot.run()
        
        if not sig.empty:
            sig['Symbol'] = sym
            sig['Pair'] = mt5_symbol
            all_signals.append(sig)
            print("[OK] Signal found!")
            
            # ส่งแจ้งเตือน Telegram
            if telegram_notifier:
                latest_signal = sig.iloc[-1].to_dict()
                latest_signal['Date'] = str(latest_signal.get('Date', ''))
                telegram_notifier.send_signal(latest_signal)
            
            # ส่ง Order อัตโนมัติ (ถ้าเปิดใช้งาน)
            if auto_trade and mt5_fetcher:
                latest_signal = sig.iloc[-1]
                entry = latest_signal['Entry']
                sl = latest_signal['SL']
                tp = latest_signal['RR1']  # ใช้ TP1 เป็นเป้าหมายแรก
                
                mt5_fetcher.place_order(
                    symbol=mt5_symbol,
                    order_type="BUY",
                    volume=trade_volume,
                    price=entry,
                    sl=sl,
                    tp=tp,
                    comment="Bird Signal Auto"
                )
        else:
            print("[SKIP] No signal")
    
    return all_signals


def main():
    """ฟังก์ชันหลัก"""
    try:
        import sys
        import io
        # ตั้งค่า encoding สำหรับ Windows console
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except:
        pass
    
    print("="*70)
    print("BIRD THEORY FOREX SIGNAL GENERATOR (MT5)")
    print("="*70)
    
    # เชื่อมต่อ MT5
    mt5_login = os.getenv('MT5_LOGIN')
    mt5_password = os.getenv('MT5_PASSWORD')
    mt5_server = os.getenv('MT5_SERVER')
    
    mt5_fetcher = MT5DataFetcher(
        login=mt5_login,
        password=mt5_password,
        server=mt5_server
    )
    
    if not mt5_fetcher.connected:
        print("[ERROR] Failed to connect to MT5")
        print("[INFO] Make sure MT5 is installed and running")
        print("[INFO] Optional: Set MT5_LOGIN, MT5_PASSWORD, MT5_SERVER environment variables")
        return
    
    # ตั้งค่า Telegram
    telegram_notifier = TelegramNotifier()
    
    # โหลด Forex symbols จาก tickers.json
    forex_symbols = load_forex_from_json()
    
    if not forex_symbols:
        print("[ERROR] No Forex symbols found in tickers.json")
        print("[INFO] Add 'forex' section to tickers.json")
        mt5_fetcher.shutdown()
        return
    
    # ตั้งค่า auto-trade (ปิดไว้เป็นค่าเริ่มต้น)
    auto_trade = os.getenv('AUTO_TRADE', 'false').lower() == 'true'
    trade_volume = float(os.getenv('TRADE_VOLUME', '0.01'))
    
    # สแกน Forex pairs
    all_signals = scan_forex_symbols(
        forex_symbols,
        mt5_fetcher=mt5_fetcher,
        telegram_notifier=telegram_notifier,
        period_days=60,
        interval="1h",
        auto_trade=auto_trade,
        trade_volume=trade_volume
    )
    
    # รวมผลลัพธ์
    if all_signals:
        result_df = pd.concat(all_signals, ignore_index=True)
        
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
        print("FOREX SIGNALS (Last 7 Days)")
        print("="*70)
        
        if not recent_signals.empty:
            # แสดงผล
            print("\nRecent Forex Signals:")
            print("-" * 70)
            display_cols = ['Pair', 'Date', 'Close', 'Vol_Ratio', 'Entry', 'SL', 'RR1', 'RR2']
            available_display = [col for col in display_cols if col in recent_signals.columns]
            print(recent_signals[available_display].to_string(index=False))
            
            # บันทึกเป็น CSV
            filename = f"forex_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            recent_signals.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\nSaved to {filename}")
            print(f"Total signals found: {len(recent_signals)}")
        else:
            print("No signals in the last 7 days.")
            
            # แสดงสัญญาณทั้งหมด (ไม่จำกัด 7 วัน)
            if not result_df.empty:
                print("\nAll Signals (All Time):")
                print("-" * 70)
                display_cols = ['Pair', 'Date', 'Close', 'Vol_Ratio', 'Entry', 'SL', 'RR1', 'RR2']
                available_display = [col for col in display_cols if col in result_df.columns]
                print(result_df[available_display].head(20).to_string(index=False))
                
                filename_all = f"forex_signals_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                result_df.to_csv(filename_all, index=False, encoding='utf-8-sig')
                print(f"\nAll signals saved to {filename_all}")
    else:
        print("\nNo signals found for any Forex pairs.")
    
    # ปิดการเชื่อมต่อ MT5
    mt5_fetcher.shutdown()


if __name__ == "__main__":
    main()
