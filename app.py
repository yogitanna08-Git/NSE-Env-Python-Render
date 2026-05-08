from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

ENV_PERCENT = float(os.environ.get('ENV_PERCENT', 14))
TOUCH_ZONE = float(os.environ.get('TOUCH_ZONE', 1))

# Nifty 50 symbols
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

def calculate_signal(ltp, sma200, env_percent, touch_zone):
    if not ltp or not sma200 or sma200 == 0:
        return "HOLD"
    lower_band = sma200 * (1 - env_percent/100)
    upper_band = sma200 * (1 + env_percent/100)
    band_width = upper_band - lower_band
    touch_amount = band_width * (touch_zone / 100)
    
    if ltp <= lower_band + touch_amount:
        return "BUY"
    elif ltp >= upper_band - touch_amount:
        return "EXIT"
    else:
        return "HOLD"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    results = []
    
    for symbol in NIFTY_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current price
            info = ticker.info
            ltp = info.get('regularMarketPrice', info.get('currentPrice', 0))
            
            if ltp and ltp > 0:
                # Get historical data for SMA-200
                hist = ticker.history(period="1y")
                if len(hist) >= 200:
                    sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
                else:
                    sma200 = ltp * 0.94  # Estimate if not enough data
                
                signal = calculate_signal(ltp, sma200, ENV_PERCENT, TOUCH_ZONE)
                lower_band = sma200 * (1 - ENV_PERCENT/100)
                upper_band = sma200 * (1 + ENV_PERCENT/100)
                
                results.append({
                    "symbol": symbol.replace('.NS', ''),
                    "ltp": round(ltp, 2),
                    "sma200": round(sma200, 2),
                    "lower_band": round(lower_band, 2),
                    "upper_band": round(upper_band, 2),
                    "signal": signal
                })
        except Exception as e:
            pass
        
        time.sleep(0.3)  # Rate limiting
    
    return jsonify({
        "success": True, 
        "data": results, 
        "count": len(results),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
