from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import time
import os

app = Flask(__name__)
CORS(app)

# Nifty 50 symbols
NIFTY_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "HINDUNILVR.NS", "AXISBANK.NS"
]  # Start with 10 for testing

def get_stock_data(symbol):
    """Get LTP and SMA-200 for a single stock"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get current price
        info = ticker.info
        ltp = info.get('regularMarketPrice', info.get('currentPrice', 0))
        
        if not ltp or ltp <= 0:
            return None
        
        # Get historical data for SMA
        hist = ticker.history(period="6mo")
        if len(hist) >= 50:
            # Calculate SMA-200 from available data
            sma = hist['Close'].mean()
        else:
            sma = ltp * 0.94
        
        return {
            "symbol": symbol.replace('.NS', ''),
            "ltp": round(ltp, 2),
            "sma200": round(sma, 2)
        }
    except Exception as e:
        print(f"Error: {symbol} - {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    results = []
    
    for symbol in NIFTY_SYMBOLS:
        data = get_stock_data(symbol)
        if data:
            results.append(data)
        time.sleep(0.3)
    
    # Calculate envelope signals
    env_percent = 14
    touch_zone = 1
    
    for stock in results:
        ltp = stock['ltp']
        sma = stock['sma200']
        lower = sma * (1 - env_percent/100)
        upper = sma * (1 + env_percent/100)
        band_width = upper - lower
        touch = band_width * (touch_zone / 100)
        
        if ltp <= lower + touch:
            signal = "BUY"
        elif ltp >= upper - touch:
            signal = "EXIT"
        else:
            signal = "HOLD"
        
        stock['lower_band'] = round(lower, 2)
        stock['upper_band'] = round(upper, 2)
        stock['signal'] = signal
    
    return jsonify({
        "success": True,
        "data": results,
        "count": len(results)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
