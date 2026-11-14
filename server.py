#!/usr/bin/env python3
"""
KPOINT COF // 2026 WHITE & BLACK MACRO NEWS TRADING TERMINAL
Live TradingView Scanner API + ForexFactory + Yahoo Finance Backend Server (No API Keys)
"""

import os
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

PORT = 8080
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

TV_TICKERS = [
    "OANDA:XAUUSD", "BITSTAMP:BTCUSD", "FX:USDJPY", "FX:EURUSD", "FX:GBPUSD",
    "NASDAQ:NDX", "SP:SPX", "OANDA:US30USD", "NYMEX:CL1!", "TVC:SILVER",
    "BITSTAMP:ETHUSD", "FX:AUDUSD", "FX:USDCAD", "OANDA:DE30EUR",
    "NASDAQ:META", "NASDAQ:NVDA", "AMEX:SPY", "NASDAQ:QQQ", "NASDAQ:MSFT",
    "NASDAQ:AMZN", "NASDAQ:TSLA", "NASDAQ:NFLX", "AMEX:GLD", "NASDAQ:AAPL",
    "NASDAQ:AMD", "NASDAQ:TLT", "NASDAQ:INTC", "NYSE:BA",
    "CME_MINI:ES1!", "CME_MINI:NQ1!", "COMEX:GC1!", "CBOT_MINI:YM1!",
    "CME_MINI:RTY1!", "COMEX:SI1!", "NYMEX:NG1!", "CBOT:ZN1!", "CBOT:ZB1!",
    "CME:6J1!", "CME:6E1!", "CME:BTC1!", "COMEX:HG1!"
]

CACHE = {
    "quotes": {"data": None, "time": 0},
    "news": {"data": None, "time": 0},
    "calendar": {"data": None, "time": 0}
}


def fetch_tradingview_live():
    now = time.time()
    if CACHE["quotes"]["data"] and (now - CACHE["quotes"]["time"]) < 3.5:
        return CACHE["quotes"]["data"]

    url = "https://scanner.tradingview.com/global/scan"
    payload = json.dumps({
        "symbols": {"tickers": TV_TICKERS, "query": {"types": []}},
        "columns": ["close", "change", "change_abs", "high", "low"]
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "text/plain;charset=UTF-8"
            }
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            out = {}
            for row in data.get("data", []):
                sym = row.get("s")
                d = row.get("d", [])
                if sym and len(d) >= 5:
                    out[sym] = {
                        "price": d[0],
                        "changePercent": d[1],
                        "changeAbs": d[2],
                        "high": d[3],
                        "low": d[4]
                    }
            if out:
                CACHE["quotes"]["data"] = out
                CACHE["quotes"]["time"] = now
            return out
    except Exception:
        return CACHE["quotes"]["data"] or {}


def fetch_yahoo_news():
    now = time.time()
    if CACHE["news"]["data"] and (now - CACHE["news"]["time"]) < 50.0:
        return CACHE["news"]["data"]

    url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^IXIC,META,NVDA,SPY,QQQ,MSFT,AMZN,TSLA,AAPL,INTC,AMD,GC=F,CL=F,BTC-USD&region=US&lang=en-US"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=7) as resp:
            root = ET.fromstring(resp.read())
            items = []
            for it in root.findall(".//item")[:20]:
                t = it.find("title")
                l = it.find("link")
                p = it.find("pubDate")
                d = it.find("description")
                items.append({
                    "title": t.text if t is not None else "",
                    "link": l.text if l is not None else "",
                    "pubDate": p.text if p is not None else "",
                    "snippet": d.text if d is not None else "",
                    "source": "Yahoo Finance Wire"
                })
            if items:
                CACHE["news"]["data"] = items
                CACHE["news"]["time"] = now
            return items
    except Exception:
        return CACHE["news"]["data"] or []


def fetch_forexfactory_calendar():
    now = time.time()
    if CACHE["calendar"]["data"] and (now - CACHE["calendar"]["time"]) < 180.0:
        return CACHE["calendar"]["data"]

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list):
                CACHE["calendar"]["data"] = data
                CACHE["calendar"]["time"] = now
                return data
    except Exception:
        pass
    return CACHE["calendar"]["data"] or []


class KpointCofHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WORKSPACE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/quotes":
            self.send_json({
                "status": "ONLINE",
                "source": "TradingView Live Scanner API",
                "quotes": fetch_tradingview_live(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            return
        elif parsed.path == "/api/news":
            self.send_json({
                "status": "ONLINE",
                "source": "Yahoo Finance Real-Time RSS Feed",
                "news": fetch_yahoo_news(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            return
        elif parsed.path == "/api/calendar":
            self.send_json({
                "status": "ONLINE",
                "source": "ForexFactory Calendar API",
                "calendar": fetch_forexfactory_calendar(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            return
        elif parsed.path == "/api/all":
            self.send_json({
                "status": "ONLINE",
                "quotes": fetch_tradingview_live(),
                "news": fetch_yahoo_news(),
                "calendar": fetch_forexfactory_calendar(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            return
        super().do_GET()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server():
    httpd = HTTPServer(("", PORT), KpointCofHandler)
    print("=" * 74)
    print("  KPOINT COF // LIVE TRADINGVIEW + MACRO NEWS TERMINAL")
    print(f"  Local URL: http://localhost:{PORT}")
    print("  Live Price Feed: https://scanner.tradingview.com/global/scan")
    print("=" * 74)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
