from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import time
import os
from datetime import datetime, timedelta

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

def calculate_signal(ltp, sma, env_pct, touch_pct):
    if not ltp or not sma or sma == 0:
        return "HOLD"
    
    lower_band = sma * (1 - env_pct/100)
    upper_band = sma * (1 + env_pct/100)
    band_width = upper_band - lower_band
    
    if band_width <= 0:
        return "HOLD"
    
    touch_amount = band_width * (touch_pct / 100)
    
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
                # Get historical data for SMA calculation
                hist = ticker.history(period="1y")
                
                if len(hist) >= 200:
                    # Calculate 200-day SMA from closing prices
                    sma = hist['Close'].tail(200).mean()
                else:
                    # Fallback: if not enough data, use estimate
                    sma = ltp * 0.94
                
                signal = calculate_signal(ltp, sma, ENV_PERCENT, TOUCH_ZONE)
                lower_band = sma * (1 - ENV_PERCENT/100)
                upper_band = sma * (1 + ENV_PERCENT/100)
                
                results.append({
                    "symbol": symbol.replace('.NS', ''),
                    "ltp": round(float(ltp), 2),
                    "sma200": round(float(sma), 2),
                    "lower_band": round(float(lower_band), 2),
                    "upper_band": round(float(upper_band), 2),
                    "signal": signal
                })
            
            # Rate limiting
            time.sleep(0.2)
            
        except Exception as e:
            print(f"Error with {symbol}: {e}")
            continue
    
    # Sort: BUY first, then EXIT, then HOLD
    results.sort(key=lambda x: 0 if x['signal'] == 'BUY' else (1 if x['signal'] == 'EXIT' else 2))
    
    return jsonify({
        "success": True,
        "data": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
