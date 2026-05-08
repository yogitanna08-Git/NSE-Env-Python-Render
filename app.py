from flask import Flask, jsonify, render_template
from flask_cors import CORS
import niftyterminal as nt
import pandas as pd
import time
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Configuration
ENV_PERCENT = float(os.environ.get('ENV_PERCENT', 14))
TOUCH_ZONE = float(os.environ.get('TOUCH_ZONE', 1))
MA_PERIOD = int(os.environ.get('MA_PERIOD', 200))
REFRESH_INTERVAL = int(os.environ.get('REFRESH_INTERVAL', 300))

# Initialize NSE session
nse = nt.Nse()

# Cache for stock data
stock_cache = {}
last_fetch_time = None

def get_nifty50_stocks():
    """Get list of Nifty 50 stocks"""
    try:
        indices = nse.get_index_quote("NIFTY 50")
        if indices and 'data' in indices:
            return [stock['symbol'] for stock in indices['data'] if stock['symbol'] != 'NIFTY 50']
    except:
        pass
    
    # Fallback list if API fails
    return [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "ITC", "SBIN",
        "HINDUNILVR", "AXISBANK", "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT",
        "BAJAJ-AUTO", "BAJFINANCE", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB",
        "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCLIFE", "HEROMOTOCO", "HINDALCO",
        "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
        "POWERGRID", "SBILIFE", "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN",
        "ULTRACEMCO", "UPL", "WIPRO"
    ]

def calculate_sma_200(symbol):
    """Calculate 200-day SMA for a stock"""
    try:
        # Get historical data
        hist_data = nse.get_history(symbol, start=datetime.now().replace(year=datetime.now().year-1))
        if hist_data and len(hist_data) >= 200:
            df = pd.DataFrame(hist_data)
            sma = df['close'].rolling(window=200).mean().iloc[-1]
            return round(sma, 2)
    except:
        pass
    return None

def get_live_price(symbol):
    """Get current LTP for a stock"""
    try:
        quote = nse.get_quote(symbol)
        if quote and 'lastPrice' in quote:
            return quote['lastPrice']
    except:
        pass
    return None

def calculate_signal(ltp, sma200, env_percent, touch_zone):
    """Calculate BUY/HOLD/EXIT signal based on envelope strategy"""
    if not ltp or not sma200 or sma200 == 0:
        return "HOLD", 0
    
    lower_band = sma200 * (1 - env_percent/100)
    upper_band = sma200 * (1 + env_percent/100)
    band_width = upper_band - lower_band
    touch_amount = band_width * (touch_zone / 100)
    
    if ltp <= lower_band + touch_amount:
        percent_from_lower = ((ltp - lower_band) / band_width) * 100
        return "BUY", round(percent_from_lower)
    elif ltp >= upper_band - touch_amount:
        percent_from_upper = ((upper_band - ltp) / band_width) * 100
        return "EXIT", round(percent_from_upper)
    else:
        percent_from_lower = ((ltp - lower_band) / band_width) * 100
        return "HOLD", round(percent_from_lower)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    global stock_cache, last_fetch_time
    
    # Check if cache is still valid (within refresh interval)
    if last_fetch_time and (datetime.now() - last_fetch_time).seconds < REFRESH_INTERVAL:
        return jsonify({
            "success": True,
            "data": stock_cache,
            "cached": True,
            "last_update": last_fetch_time.isoformat()
        })
    
    try:
        symbols = get_nifty50_stocks()
        results = []
        
        for symbol in symbols[:50]:  # Start with 50 stocks
            ltp = get_live_price(symbol)
            sma200 = calculate_sma_200(symbol)
            
            if ltp and ltp > 0:
                signal, position = calculate_signal(ltp, sma200, ENV_PERCENT, TOUCH_ZONE)
                lower_band = sma200 * (1 - ENV_PERCENT/100) if sma200 else 0
                upper_band = sma200 * (1 + ENV_PERCENT/100) if sma200 else 0
                
                results.append({
                    "symbol": symbol,
                    "ltp": ltp,
                    "sma200": sma200 if sma200 else 0,
                    "lower_band": round(lower_band, 2),
                    "upper_band": round(upper_band, 2),
                    "signal": signal,
                    "position_percent": position
                })
            
            # Rate limiting
            time.sleep(0.5)
        
        stock_cache = results
        last_fetch_time = datetime.now()
        
        return jsonify({
            "success": True,
            "data": results,
            "cached": False,
            "count": len(results),
            "last_update": last_fetch_time.isoformat(),
            "settings": {
                "env_percent": ENV_PERCENT,
                "touch_zone": TOUCH_ZONE,
                "ma_period": MA_PERIOD
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "data": stock_cache if stock_cache else []
        })

@app.route('/api/settings')
def get_settings():
    return jsonify({
        "env_percent": ENV_PERCENT,
        "touch_zone": TOUCH_ZONE,
        "ma_period": MA_PERIOD,
        "refresh_interval": REFRESH_INTERVAL
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))