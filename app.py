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

# Complete Nifty 50 symbols
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

def fetch_ltp_and_history(symbol):
    """Fetch LTP and historical closing prices"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            result = data['chart']['result'][0]
            
            # Get current price
            ltp = result['meta']['regularMarketPrice']
            
            # Get historical closing prices
            closes = result['indicators']['quote'][0]['close']
            # Filter out None values
            closes = [c for c in closes if c is not None]
            
            return ltp, closes
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None, None

def calculate_sma_from_history(closes, period=200):
    """Calculate SMA from historical closing prices"""
    if not closes or len(closes) < period:
        return None
    # Use the last 'period' number of closes
    recent_closes = closes[-period:]
    return sum(recent_closes) / period

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
    total = len(NIFTY_SYMBOLS)
    
    for i, symbol in enumerate(NIFTY_SYMBOLS):
        clean_symbol = symbol.replace('.NS', '')
        
        ltp, closes = fetch_ltp_and_history(symbol)
        
        if ltp and closes:
            # Calculate SMA from historical data
            sma = calculate_sma_from_history(closes, 200)
            
            if not sma:
                # Fallback: use LTP * 0.95 if insufficient history
                sma = ltp * 0.95
            
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
        
        # Progress update (optional, for debugging)
        if (i + 1) % 10 == 0:
            print(f"Processed {i+1}/{total} stocks")
        
        # Rate limiting to avoid being blocked
        time.sleep(0.3)
    
    # Sort: BUY first
    results.sort(key=lambda x: 0 if x['signal'] == 'BUY' else (1 if x['signal'] == 'EXIT' else 2))
    
    return jsonify({
        "success": True, 
        "data": results, 
        "count": len(results),
        "total_symbols": total,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
