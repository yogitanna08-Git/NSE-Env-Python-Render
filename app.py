from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
import json
import time
import os

app = Flask(__name__)
CORS(app)

ENV_PERCENT = float(os.environ.get('ENV_PERCENT', 14))
TOUCH_ZONE = float(os.environ.get('TOUCH_ZONE', 1))

# Nifty 50 symbols (without .NS for this API)
NIFTY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "BHARTIARTL", "ITC", "SBIN", "HINDUNILVR", "AXISBANK"
]

def fetch_from_yfinance_proxy(symbol):
    """Fetch stock data using a public CORS proxy"""
    try:
        # Using Yahoo Finance via free CORS proxy
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
        proxy_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(url)}"
        
        response = requests.get(proxy_url, timeout=15)
        data = response.json()
        
        if data and 'chart' in data and data['chart']['result']:
            result = data['chart']['result'][0]
            ltp = result['meta']['regularMarketPrice']
            
            # Get closing prices for SMA calculation
            closes = result['indicators']['quote'][0]['close']
            closes = [c for c in closes if c is not None]
            
            if len(closes) >= 200:
                sma = sum(closes[-200:]) / 200
            else:
                sma = ltp * 0.94
            
            return {"symbol": symbol, "ltp": ltp, "sma200": sma}
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    results = []
    
    for symbol in NIFTY_SYMBOLS:
        data = fetch_from_yfinance_proxy(symbol)
        if data:
            results.append(data)
        time.sleep(0.5)
    
    # Calculate envelope signals
    for stock in results:
        ltp = stock['ltp']
        sma = stock['sma200']
        lower = sma * (1 - ENV_PERCENT/100)
        upper = sma * (1 + ENV_PERCENT/100)
        band_width = upper - lower
        touch = band_width * (TOUCH_ZONE / 100)
        
        if ltp <= lower + touch:
            signal = "BUY"
        elif ltp >= upper - touch:
            signal = "EXIT"
        else:
            signal = "HOLD"
        
        stock['lower_band'] = round(lower, 2)
        stock['upper_band'] = round(upper, 2)
        stock['signal'] = signal
        stock['ltp'] = round(ltp, 2)
        stock['sma200'] = round(sma, 2)
    
    return jsonify({
        "success": True,
        "data": results,
        "count": len(results),
        "source": "live"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
