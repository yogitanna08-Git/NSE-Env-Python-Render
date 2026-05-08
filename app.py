from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os
import json
import urllib.request
import time

app = Flask(__name__)
CORS(app)

ENV_PERCENT = float(os.environ.get('ENV_PERCENT', 14))
TOUCH_ZONE = float(os.environ.get('TOUCH_ZONE', 1))

# Nifty 50 symbols with .NS suffix
NIFTY_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "HINDUNILVR.NS", "AXISBANK.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "NESTLEIND.NS", "NTPC.NS", "ONGC.NS",
    "POWERGRID.NS", "SBILIFE.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS", "WIPRO.NS"
]

def fetch_price(symbol):
    """Fetch current price from Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return price
    except:
        return None

def fetch_sma(symbol):
    """Fetch 200-day SMA from Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            closes = [c for c in data['chart']['result'][0]['indicators']['quote'][0]['close'] if c]
            if len(closes) >= 200:
                sma = sum(closes[-200:]) / 200
                return sma
    except:
        return None
    return None

def calculate_signal(ltp, sma, env_pct, touch_pct):
    if not ltp or not sma:
        return "HOLD"
    lower = sma * (1 - env_pct/100)
    upper = sma * (1 + env_pct/100)
    band_width = upper - lower
    touch_amt = band_width * (touch_pct / 100)
    
    if ltp <= lower + touch_amt:
        return "BUY"
    elif ltp >= upper - touch_amt:
        return "EXIT"
    return "HOLD"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    results = []
    
    for symbol in NIFTY_SYMBOLS[:20]:  # Start with 20 for speed
        clean_symbol = symbol.replace('.NS', '')
        ltp = fetch_price(symbol)
        
        if ltp:
            sma = fetch_sma(symbol)
            if not sma:
                sma = ltp * 0.94  # Estimate if SMA fetch fails
            
            signal = calculate_signal(ltp, sma, ENV_PERCENT, TOUCH_ZONE)
            lower = sma * (1 - ENV_PERCENT/100)
            upper = sma * (1 + ENV_PERCENT/100)
            
            results.append({
                "symbol": clean_symbol,
                "ltp": round(ltp, 2),
                "sma200": round(sma, 2),
                "lower_band": round(lower, 2),
                "upper_band": round(upper, 2),
                "signal": signal
            })
        
        time.sleep(0.5)  # Rate limiting
    
    return jsonify({"success": True, "data": results, "count": len(results)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)