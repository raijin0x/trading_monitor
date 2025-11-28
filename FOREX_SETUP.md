# Forex Signal Generator Setup Guide

## การติดตั้ง

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

**หมายเหตุ:** `python-dotenv` จะถูกติดตั้งอัตโนมัติเพื่ออ่านไฟล์ `.env`

### 2. ติดตั้ง MetaTrader 5

1. ดาวน์โหลดและติดตั้ง MetaTrader 5 จาก broker ของคุณ
2. เปิด MT5 และ login เข้า account
3. ตรวจสอบว่า MT5 กำลังทำงานอยู่

### 3. ตั้งค่า Telegram Bot (Optional)

#### สร้าง Telegram Bot:

1. เปิด Telegram และค้นหา `@BotFather`
2. ส่งคำสั่ง `/newbot` และทำตามคำแนะนำ
3. เก็บ `Bot Token` ที่ได้

#### หา Chat ID:

1. เปิด Telegram และค้นหา `@userinfobot`
2. ส่งข้อความใดๆ และจะได้ `Chat ID` กลับมา

#### ตั้งค่า Environment Variables:

**วิธีที่ 1: ใช้ไฟล์ `.env` (แนะนำ)**

1. สร้างไฟล์ `.env` ในโฟลเดอร์โปรเจค:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

2. Script จะอ่านค่าจาก `.env` อัตโนมัติ (ต้องติดตั้ง `python-dotenv`)

**วิธีที่ 2: ตั้งค่า Environment Variables โดยตรง:**

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
```

**Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token
set TELEGRAM_CHAT_ID=your_chat_id
```

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 4. ตั้งค่า MT5 Login (Optional)

ถ้าต้องการ login อัตโนมัติ:

**Windows (PowerShell):**
```powershell
$env:MT5_LOGIN="your_login"
$env:MT5_PASSWORD="your_password"
$env:MT5_SERVER="your_broker_server"
```

**Linux/Mac:**
```bash
export MT5_LOGIN="your_login"
export MT5_PASSWORD="your_password"
export MT5_SERVER="your_broker_server"
```

## การใช้งาน

### รัน Signal Generator:

```bash
python gg_signal_forex.py
```

### Auto Trading (ใช้ด้วยความระมัดระวัง!):

```bash
# Windows
$env:AUTO_TRADE="true"
$env:TRADE_VOLUME="0.01"
python gg_signal_forex.py

# Linux/Mac
export AUTO_TRADE="true"
export TRADE_VOLUME="0.01"
python gg_signal_forex.py
```

## Forex Pairs ใน tickers.json

ไฟล์ `tickers.json` มี Forex 20 คู่หลัก:

**Major Pairs:**
- EURUSD, GBPUSD, USDJPY, AUDUSD
- USDCAD, USDCHF, NZDUSD

**Cross Pairs:**
- EURGBP, EURJPY, GBPJPY
- AUDJPY, EURAUD, EURCAD
- GBPAUD, GBPCAD, AUDCAD
- AUDNZD, CADJPY, CHFJPY, EURCHF

## หมายเหตุ

1. **MT5 ต้องเปิดอยู่** - Script จะเชื่อมต่อกับ MT5 ที่กำลังทำงาน
2. **Volume จริง** - MT5 ให้ Volume จริง (tick volume หรือ real volume)
3. **Auto Trading** - เปิดใช้งานด้วยความระมัดระวัง! ทดสอบใน demo account ก่อน
4. **Telegram** - แจ้งเตือนอัตโนมัติเมื่อพบสัญญาณ

## Troubleshooting

### MT5 Connection Failed:
- ตรวจสอบว่า MT5 เปิดอยู่
- ตรวจสอบว่า MT5 terminal อนุญาตให้ Python API เชื่อมต่อได้

### Telegram Not Working:
- ตรวจสอบ Bot Token และ Chat ID
- ตรวจสอบว่า Bot ยัง active อยู่
- ลองส่งข้อความไปหา Bot ก่อน

### No Signals Found:
- เงื่อนไขอาจเข้มเกินไป
- ลองปรับ threshold ใน `generate_signals()` method

