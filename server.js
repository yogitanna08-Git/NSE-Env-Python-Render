const express = require('express');
const cors = require('cors');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const ENV_PERCENT = 14;
const TOUCH_ZONE = 1;

const NIFTY_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "HINDUNILVR.NS", "AXISBANK.NS"
];

async function fetchStockData(symbol) {
    try {
        // Fetch 1 year of daily data for accurate SMA calculation
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1y`;
        const response = await axios.get(url, {
            headers: { 'User-Agent': 'Mozilla/5.0' },
            timeout: 15000
        });
        
        const result = response.data.chart.result[0];
        const ltp = result.meta.regularMarketPrice;
        
        // Get ALL closing prices for accurate SMA calculation
        const closes = result.indicators.quote[0].close.filter(c => c !== null);
        
        // Calculate 200-day SMA properly
        let sma = null;
        if (closes.length >= 200) {
            const last200Closes = closes.slice(-200);
            sma = last200Closes.reduce((a, b) => a + b, 0) / 200;
        } else if (closes.length >= 100) {
            // Fallback to available data
            sma = closes.reduce((a, b) => a + b, 0) / closes.length;
        } else {
            // Last resort estimate
            sma = ltp * 0.94;
        }
        
        return {
            symbol: symbol.replace('.NS', ''),
            ltp: parseFloat(ltp.toFixed(2)),
            sma200: parseFloat(sma.toFixed(2))
        };
    } catch (error) {
        console.error(`Error fetching ${symbol}:`, error.message);
        return null;
    }
}

app.get('/api/stocks', async (req, res) => {
    const results = [];
    
    console.log("Fetching live NSE data with 200-day SMA...");
    
    for (let i = 0; i < NIFTY_SYMBOLS.length; i++) {
        console.log(`Fetching ${NIFTY_SYMBOLS[i]} (${i+1}/${NIFTY_SYMBOLS.length})`);
        const data = await fetchStockData(NIFTY_SYMBOLS[i]);
        if (data) {
            results.push(data);
        }
        // Rate limiting to avoid being blocked
        await new Promise(r => setTimeout(r, 1000));
    }
    
    // Calculate envelope signals
    for (const stock of results) {
        const ltp = stock.ltp;
        const sma = stock.sma200;
        const lower = sma * (1 - ENV_PERCENT/100);
        const upper = sma * (1 + ENV_PERCENT/100);
        const bandWidth = upper - lower;
        const touchAmount = bandWidth * (TOUCH_ZONE / 100);
        
        if (ltp <= lower + touchAmount) {
            stock.signal = "BUY";
        } else if (ltp >= upper - touchAmount) {
            stock.signal = "EXIT";
        } else {
            stock.signal = "HOLD";
        }
        
        stock.lower_band = parseFloat(lower.toFixed(2));
        stock.upper_band = parseFloat(upper.toFixed(2));
    }
    
    // Sort: BUY first
    results.sort((a, b) => {
        if (a.signal === "BUY") return -1;
        if (b.signal === "BUY") return 1;
        if (a.signal === "EXIT") return -1;
        if (b.signal === "EXIT") return 1;
        return 0;
    });
    
    console.log(`Successfully fetched ${results.length} stocks`);
    
    res.json({
        success: true,
        data: results,
        count: results.length,
        timestamp: new Date().toISOString()
    });
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
