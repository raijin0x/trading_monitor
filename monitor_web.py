#!/usr/bin/env python3
"""
Monitor ราคาหุ้นและ Cryptocurrency ผ่าน Web Browser (localhost)
แสดงราคา, การเปลี่ยนแปลง, Volume, High, Low สำหรับ stocks และ crypto ใน tickers.json

การใช้งาน:
    python monitor_web.py              # รันที่ http://localhost:5000
    python monitor_web.py --port 8080  # รันที่ port อื่น
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd  # type: ignore[import]
import yfinance as yf  # type: ignore[import]

try:
    from flask import Flask, jsonify, render_template_string  # type: ignore[import]
except ImportError:
    print("Error: Flask is not installed. Please run: pip install flask")
    raise SystemExit(1)

ROOT_DIR = Path(__file__).resolve().parent
TICKERS_JSON = ROOT_DIR / "tickers.json"

app = Flask(__name__)


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


def load_largecap_from_json() -> list[str]:
    """อ่าน tickers.json แล้วคืนลิสต์ largecap เป็นตัวพิมพ์ใหญ่"""
    if not TICKERS_JSON.exists():
        return []

    with TICKERS_JSON.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    arr = data.get("largecap", [])
    if not isinstance(arr, list):
        return []

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


def load_crypto_from_json() -> list[str]:
    """อ่าน tickers.json แล้วคืนลิสต์ crypto เป็นตัวพิมพ์ใหญ่"""
    if not TICKERS_JSON.exists():
        return []

    with TICKERS_JSON.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    arr = data.get("crypto", [])
    if not isinstance(arr, list):
        return []

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


def load_forex_from_json() -> list[str]:
    """อ่าน tickers.json แล้วคืนลิสต์ forex เป็นตัวพิมพ์ใหญ่"""
    if not TICKERS_JSON.exists():
        return []

    with TICKERS_JSON.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    arr = data.get("forex", [])
    if not isinstance(arr, list):
        return []

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


def fetch_stock_data(tickers: list[str]) -> list[dict]:
    """ดึงข้อมูลหุ้นล่าสุด: Price, Change, %Change, Volume, High, Low"""
    if not tickers:
        return []

    results = []

    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # ดึงราคาปัจจุบัน
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or None
            prev_close = info.get("previousClose") or current_price

            # คำนวณ change
            if current_price is not None and prev_close is not None and pd.notna(current_price) and pd.notna(prev_close):
                change = float(current_price) - float(prev_close)
                change_pct = (change / float(prev_close) * 100) if prev_close != 0 else None
            else:
                change = None
                change_pct = None

            # ดึงข้อมูลอื่น ๆ
            volume = info.get("volume") or info.get("averageVolume") or None
            high = info.get("dayHigh") or info.get("regularMarketDayHigh") or None
            low = info.get("dayLow") or info.get("regularMarketDayLow") or None

            results.append({
                "ticker": ticker,
                "price": float(current_price) if current_price is not None and pd.notna(current_price) else None,
                "change": float(change) if change is not None else None,
                "change_pct": float(change_pct) if change_pct is not None else None,
                "volume": int(volume) if volume is not None and pd.notna(volume) else None,
                "high": float(high) if high is not None and pd.notna(high) else None,
                "low": float(low) if low is not None and pd.notna(low) else None,
            })

        except Exception:
            # ถ้า .info ไม่ได้ ให้ลองใช้ download
            try:
                df = yf.download(ticker, period="5d", interval="1d", progress=False, timeout=10)
                if not df.empty and len(df) > 0:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest

                    current_price = latest.get("Close", None)
                    prev_close = prev.get("Close", current_price)

                    if current_price is not None and prev_close is not None and pd.notna(current_price) and pd.notna(prev_close):
                        change = float(current_price) - float(prev_close)
                        change_pct = (change / float(prev_close) * 100) if prev_close != 0 else None
                    else:
                        change = None
                        change_pct = None

                    vol = latest.get("Volume", None)
                    h = latest.get("High", None)
                    l = latest.get("Low", None)

                    results.append({
                        "ticker": ticker,
                        "price": float(current_price) if current_price is not None and pd.notna(current_price) else None,
                        "change": float(change) if change is not None else None,
                        "change_pct": float(change_pct) if change_pct is not None else None,
                        "volume": int(vol) if vol is not None and pd.notna(vol) else None,
                        "high": float(h) if h is not None and pd.notna(h) else None,
                        "low": float(l) if l is not None and pd.notna(l) else None,
                    })
                else:
                    # ไม่มีข้อมูลเลย
                    results.append({
                        "ticker": ticker,
                        "price": None,
                        "change": None,
                        "change_pct": None,
                        "volume": None,
                        "high": None,
                        "low": None,
                    })
            except Exception:
                # ไม่สามารถดึงข้อมูลได้
                results.append({
                    "ticker": ticker,
                    "price": None,
                    "change": None,
                    "change_pct": None,
                    "volume": None,
                    "high": None,
                    "low": None,
                })

    return results


def fetch_crypto_data(tickers: list[str]) -> list[dict]:
    """ดึงข้อมูล crypto ล่าสุด: Price, Change, %Change, Volume, High, Low"""
    if not tickers:
        return []

    results = []

    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # ดึงราคาปัจจุบัน
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or None
            prev_close = info.get("previousClose") or current_price

            # คำนวณ change
            if current_price is not None and prev_close is not None and pd.notna(current_price) and pd.notna(prev_close):
                change = float(current_price) - float(prev_close)
                change_pct = (change / float(prev_close) * 100) if prev_close != 0 else None
            else:
                change = None
                change_pct = None

            # ดึงข้อมูลอื่น ๆ
            volume = info.get("volume") or info.get("averageVolume") or None
            high = info.get("dayHigh") or info.get("regularMarketDayHigh") or None
            low = info.get("dayLow") or info.get("regularMarketDayLow") or None

            results.append({
                "ticker": ticker,
                "price": float(current_price) if current_price is not None and pd.notna(current_price) else None,
                "change": float(change) if change is not None else None,
                "change_pct": float(change_pct) if change_pct is not None else None,
                "volume": int(volume) if volume is not None and pd.notna(volume) else None,
                "high": float(high) if high is not None and pd.notna(high) else None,
                "low": float(low) if low is not None and pd.notna(low) else None,
            })

        except Exception:
            # ถ้า .info ไม่ได้ ให้ลองใช้ download
            try:
                df = yf.download(ticker, period="5d", interval="1d", progress=False, timeout=10)
                if not df.empty and len(df) > 0:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest

                    current_price = latest.get("Close", None)
                    prev_close = prev.get("Close", current_price)

                    if current_price is not None and prev_close is not None and pd.notna(current_price) and pd.notna(prev_close):
                        change = float(current_price) - float(prev_close)
                        change_pct = (change / float(prev_close) * 100) if prev_close != 0 else None
                    else:
                        change = None
                        change_pct = None

                    vol = latest.get("Volume", None)
                    h = latest.get("High", None)
                    l = latest.get("Low", None)

                    results.append({
                        "ticker": ticker,
                        "price": float(current_price) if current_price is not None and pd.notna(current_price) else None,
                        "change": float(change) if change is not None else None,
                        "change_pct": float(change_pct) if change_pct is not None else None,
                        "volume": int(vol) if vol is not None and pd.notna(vol) else None,
                        "high": float(h) if h is not None and pd.notna(h) else None,
                        "low": float(l) if l is not None and pd.notna(l) else None,
                    })
                else:
                    # ไม่มีข้อมูลเลย
                    results.append({
                        "ticker": ticker,
                        "price": None,
                        "change": None,
                        "change_pct": None,
                        "volume": None,
                        "high": None,
                        "low": None,
                    })
            except Exception:
                # ไม่สามารถดึงข้อมูลได้
                results.append({
                    "ticker": ticker,
                    "price": None,
                    "change": None,
                    "change_pct": None,
                    "volume": None,
                    "high": None,
                    "low": None,
                })

    return results


def fetch_forex_data(tickers: list[str]) -> list[dict]:
    """ดึงข้อมูล Forex pairs ล่าสุด: Price, Change, %Change, High, Low"""
    if not tickers:
        return []

    results = []

    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # ดึงราคาปัจจุบัน
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or None
            prev_close = info.get("previousClose") or current_price

            # คำนวณ change
            if current_price is not None and prev_close is not None and pd.notna(current_price) and pd.notna(prev_close):
                change = float(current_price) - float(prev_close)
                change_pct = (change / float(prev_close) * 100) if prev_close != 0 else None
            else:
                change = None
                change_pct = None

            # ดึงข้อมูลอื่น ๆ
            high = info.get("dayHigh") or info.get("regularMarketDayHigh") or None
            low = info.get("dayLow") or info.get("regularMarketDayLow") or None

            # แปลง ticker name (EURUSD=X -> EURUSD)
            display_ticker = ticker.replace("=X", "")

            results.append({
                "ticker": display_ticker,
                "price": float(current_price) if current_price is not None and pd.notna(current_price) else None,
                "change": float(change) if change is not None else None,
                "change_pct": float(change_pct) if change_pct is not None else None,
                "volume": None,  # Forex ไม่มี volume
                "high": float(high) if high is not None and pd.notna(high) else None,
                "low": float(low) if low is not None and pd.notna(low) else None,
            })

        except Exception:
            # ถ้า .info ไม่ได้ ให้ลองใช้ download
            try:
                df = yf.download(ticker, period="5d", interval="1d", progress=False, timeout=10)
                if not df.empty and len(df) > 0:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest

                    current_price = latest.get("Close", None)
                    prev_close = prev.get("Close", current_price)

                    if current_price is not None and prev_close is not None and pd.notna(current_price) and pd.notna(prev_close):
                        change = float(current_price) - float(prev_close)
                        change_pct = (change / float(prev_close) * 100) if prev_close != 0 else None
                    else:
                        change = None
                        change_pct = None

                    h = latest.get("High", None)
                    l = latest.get("Low", None)

                    # แปลง ticker name
                    display_ticker = ticker.replace("=X", "")

                    results.append({
                        "ticker": display_ticker,
                        "price": float(current_price) if current_price is not None and pd.notna(current_price) else None,
                        "change": float(change) if change is not None else None,
                        "change_pct": float(change_pct) if change_pct is not None else None,
                        "volume": None,
                        "high": float(h) if h is not None and pd.notna(h) else None,
                        "low": float(l) if l is not None and pd.notna(l) else None,
                    })
                else:
                    # ไม่มีข้อมูลเลย
                    display_ticker = ticker.replace("=X", "")
                    results.append({
                        "ticker": display_ticker,
                        "price": None,
                        "change": None,
                        "change_pct": None,
                        "volume": None,
                        "high": None,
                        "low": None,
                    })
            except Exception:
                # ไม่สามารถดึงข้อมูลได้
                display_ticker = ticker.replace("=X", "")
                results.append({
                    "ticker": display_ticker,
                    "price": None,
                    "change": None,
                    "change_pct": None,
                    "volume": None,
                    "high": None,
                    "low": None,
                })

    return results


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        h1 {
            color: #333;
            font-size: 28px;
        }
        
        .timestamp {
            color: #666;
            font-size: 14px;
        }
        
        .refresh-info {
            color: #666;
            font-size: 12px;
        }
        
        .table-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-x: auto;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        thead {
            background: #667eea;
            color: white;
        }
        
        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
        }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        
        tbody tr:hover {
            background: #f5f5f5;
        }
        
        .ticker {
            font-weight: bold;
            color: #333;
            font-size: 16px;
        }
        
        .price {
            font-weight: 600;
            font-size: 16px;
            transition: background-color 0.3s ease;
        }
        
        .price-updated {
            background-color: #d1fae5;
            animation: flash-green 0.5s ease;
        }
        
        .price-downdated {
            background-color: #fee2e2;
            animation: flash-red 0.5s ease;
        }
        
        @keyframes flash-green {
            0% { background-color: #10b981; }
            50% { background-color: #d1fae5; }
            100% { background-color: transparent; }
        }
        
        @keyframes flash-red {
            0% { background-color: #ef4444; }
            50% { background-color: #fee2e2; }
            100% { background-color: transparent; }
        }
        
        .positive {
            color: #10b981;
            font-weight: 600;
        }
        
        .negative {
            color: #ef4444;
            font-weight: 600;
        }
        
        .neutral {
            color: #6b7280;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📈 Stock Monitor</h1>
                <div class="timestamp" id="timestamp">Loading...</div>
            </div>
            <div class="refresh-info">Auto-refresh: <span id="refresh-countdown">3</span>s (Real-time)</div>
        </div>
        
        <div class="table-container">
            <div class="section-title">📈 Stocks (Mid-Cap)</div>
            <div id="loading-stocks" class="loading">
                <div class="spinner"></div>
                <div>Loading stock data...</div>
            </div>
            <table id="stock-table" style="display: none;">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Change %</th>
                        <th>Volume</th>
                        <th>High</th>
                        <th>Low</th>
                    </tr>
                </thead>
                <tbody id="stock-tbody">
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <div class="section-title">🏢 Large-Cap Stocks</div>
            <div id="loading-largecap" class="loading">
                <div class="spinner"></div>
                <div>Loading large-cap data...</div>
            </div>
            <table id="largecap-table" style="display: none;">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Change %</th>
                        <th>Volume</th>
                        <th>High</th>
                        <th>Low</th>
                    </tr>
                </thead>
                <tbody id="largecap-tbody">
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <div class="section-title">₿ Cryptocurrencies</div>
            <div id="loading-crypto" class="loading">
                <div class="spinner"></div>
                <div>Loading crypto data...</div>
            </div>
            <table id="crypto-table" style="display: none;">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Change %</th>
                        <th>Volume</th>
                        <th>High</th>
                        <th>Low</th>
                    </tr>
                </thead>
                <tbody id="crypto-tbody">
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <div class="section-title">💱 Forex Pairs</div>
            <div id="loading-forex" class="loading">
                <div class="spinner"></div>
                <div>Loading forex data...</div>
            </div>
            <table id="forex-table" style="display: none;">
                <thead>
                    <tr>
                        <th>Pair</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Change %</th>
                        <th>High</th>
                        <th>Low</th>
                    </tr>
                </thead>
                <tbody id="forex-tbody">
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        let refreshInterval = 3; // seconds - real-time updates
        let countdown = refreshInterval;
        let previousPrices = {}; // Store previous prices for animation
        
        function formatNumber(num) {
            if (num === null || num === undefined) return 'N/A';
            return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        
        function formatVolume(num) {
            if (num === null || num === undefined) return 'N/A';
            if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(2) + 'K';
            return num.toLocaleString();
        }
        
        function getChangeClass(value) {
            if (value === null || value === undefined) return 'neutral';
            return value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
        }
        
        function formatChange(value) {
            if (value === null || value === undefined) return 'N/A';
            const sign = value >= 0 ? '+' : '';
            return sign + formatNumber(value);
        }
        
        function formatChangePct(value) {
            if (value === null || value === undefined) return 'N/A';
            const sign = value >= 0 ? '+' : '';
            return sign + value.toFixed(2) + '%';
        }
        
        function renderTable(data, tbodyId, loadingId, tableId) {
            const tbody = document.getElementById(tbodyId);
            const tableKey = tableId; // 'stock-table' or 'crypto-table'
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #666;">No data available</td></tr>';
                document.getElementById(loadingId).style.display = 'none';
                document.getElementById(tableId).style.display = 'table';
                return;
            }
            
            // Create a map of existing rows for comparison
            const existingRows = {};
            Array.from(tbody.children).forEach(row => {
                const ticker = row.querySelector('.ticker')?.textContent;
                if (ticker) {
                    existingRows[ticker] = row;
                }
            });
            
            // Clear and rebuild
            tbody.innerHTML = '';
            
            data.forEach(item => {
                const row = document.createElement('tr');
                const priceKey = `${tableKey}-${item.ticker}`;
                const prevPrice = previousPrices[priceKey];
                const currentPrice = item.price;
                
                // Determine if price changed
                let priceClass = 'price';
                if (prevPrice !== undefined && currentPrice !== null && prevPrice !== null) {
                    if (currentPrice > prevPrice) {
                        priceClass = 'price price-updated';
                    } else if (currentPrice < prevPrice) {
                        priceClass = 'price price-downdated';
                    }
                }
                
                // Store current price for next comparison
                previousPrices[priceKey] = currentPrice;
                
                const changeClass = getChangeClass(item.change);
                const changePctClass = getChangeClass(item.change_pct);
                
                row.innerHTML = `
                    <td class="ticker">${item.ticker}</td>
                    <td class="${priceClass}">${formatNumber(item.price)}</td>
                    <td class="${changeClass}">${formatChange(item.change)}</td>
                    <td class="${changePctClass}">${formatChangePct(item.change_pct)}</td>
                    <td>${formatVolume(item.volume)}</td>
                    <td>${formatNumber(item.high)}</td>
                    <td>${formatNumber(item.low)}</td>
                `;
                
                tbody.appendChild(row);
            });
            
            document.getElementById(loadingId).style.display = 'none';
            document.getElementById(tableId).style.display = 'table';
        }
        
        function renderForexTable(data, tbodyId, loadingId, tableId) {
            const tbody = document.getElementById(tbodyId);
            const tableKey = tableId;
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">No data available</td></tr>';
                document.getElementById(loadingId).style.display = 'none';
                document.getElementById(tableId).style.display = 'table';
                return;
            }
            
            // Create a map of existing rows for comparison
            const existingRows = {};
            Array.from(tbody.children).forEach(row => {
                const ticker = row.querySelector('.ticker')?.textContent;
                if (ticker) {
                    existingRows[ticker] = row;
                }
            });
            
            // Clear and rebuild
            tbody.innerHTML = '';
            
            data.forEach(item => {
                const row = document.createElement('tr');
                const priceKey = `${tableKey}-${item.ticker}`;
                const prevPrice = previousPrices[priceKey];
                const currentPrice = item.price;
                
                // Determine if price changed
                let priceClass = 'price';
                if (prevPrice !== undefined && currentPrice !== null && prevPrice !== null) {
                    if (currentPrice > prevPrice) {
                        priceClass = 'price price-updated';
                    } else if (currentPrice < prevPrice) {
                        priceClass = 'price price-downdated';
                    }
                }
                
                // Store current price for next comparison
                previousPrices[priceKey] = currentPrice;
                
                const changeClass = getChangeClass(item.change);
                const changePctClass = getChangeClass(item.change_pct);
                
                row.innerHTML = `
                    <td class="ticker">${item.ticker}</td>
                    <td class="${priceClass}">${formatNumber(item.price)}</td>
                    <td class="${changeClass}">${formatChange(item.change)}</td>
                    <td class="${changePctClass}">${formatChangePct(item.change_pct)}</td>
                    <td>${formatNumber(item.high)}</td>
                    <td>${formatNumber(item.low)}</td>
                `;
                
                tbody.appendChild(row);
            });
            
            document.getElementById(loadingId).style.display = 'none';
            document.getElementById(tableId).style.display = 'table';
        }
        
        async function fetchData() {
            try {
                // Fetch stocks (mid-cap)
                const stocksResponse = await fetch('/api/data');
                const stocksData = await stocksResponse.json();
                renderTable(stocksData, 'stock-tbody', 'loading-stocks', 'stock-table');
                
                // Fetch large-cap
                const largecapResponse = await fetch('/api/largecap');
                const largecapData = await largecapResponse.json();
                renderTable(largecapData, 'largecap-tbody', 'loading-largecap', 'largecap-table');
                
                // Fetch crypto
                const cryptoResponse = await fetch('/api/crypto');
                const cryptoData = await cryptoResponse.json();
                renderTable(cryptoData, 'crypto-tbody', 'loading-crypto', 'crypto-table');
                
                // Fetch forex
                const forexResponse = await fetch('/api/forex');
                const forexData = await forexResponse.json();
                renderForexTable(forexData, 'forex-tbody', 'loading-forex', 'forex-table');
                
                document.getElementById('timestamp').textContent = 
                    'Last updated: ' + new Date().toLocaleString('th-TH');
                
            } catch (error) {
                console.error('Error fetching data:', error);
                document.getElementById('loading-stocks').innerHTML = 
                    '<div style="color: #ef4444;">Error loading data. Please refresh the page.</div>';
                document.getElementById('loading-largecap').innerHTML = 
                    '<div style="color: #ef4444;">Error loading data. Please refresh the page.</div>';
                document.getElementById('loading-crypto').innerHTML = 
                    '<div style="color: #ef4444;">Error loading data. Please refresh the page.</div>';
                document.getElementById('loading-forex').innerHTML = 
                    '<div style="color: #ef4444;">Error loading data. Please refresh the page.</div>';
            }
        }
        
        function updateCountdown() {
            countdown--;
            document.getElementById('refresh-countdown').textContent = countdown;
            
            if (countdown <= 0) {
                countdown = refreshInterval;
                fetchData();
            }
        }
        
        // Initial load
        fetchData();
        
        // Auto-refresh
        setInterval(updateCountdown, 1000);
        setInterval(fetchData, refreshInterval * 1000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """หน้าแรกแสดงตารางหุ้น"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/data")
def api_data():
    """API endpoint สำหรับดึงข้อมูลหุ้น"""
    tickers = load_benchmarks_from_json()
    data = fetch_stock_data(tickers)
    return jsonify(data)


@app.route("/api/largecap")
def api_largecap():
    """API endpoint สำหรับดึงข้อมูล large-cap stocks"""
    tickers = load_largecap_from_json()
    data = fetch_stock_data(tickers)
    return jsonify(data)


@app.route("/api/crypto")
def api_crypto():
    """API endpoint สำหรับดึงข้อมูล crypto"""
    tickers = load_crypto_from_json()
    data = fetch_crypto_data(tickers)
    return jsonify(data)


@app.route("/api/forex")
def api_forex():
    """API endpoint สำหรับดึงข้อมูล Forex pairs"""
    tickers = load_forex_from_json()
    data = fetch_forex_data(tickers)
    return jsonify(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor ราคาหุ้นผ่าน Web Browser")
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port number (default: 5000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    print(f"\n🚀 Starting Stock, Crypto & Forex Monitor Web Server...")
    print(f"📊 Open your browser and go to: http://{args.host}:{args.port}")
    print(f"📈 Monitoring: Mid-Cap Stocks, Large-Cap Stocks, Cryptocurrencies & Forex Pairs")
    print(f"⏹️  Press Ctrl+C to stop the server\n")

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()

