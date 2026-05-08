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
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}`;
        const response = await axios.get(url, {
            headers: { 'User-Agent': 'Mozilla/5.0' },
            timeout: 10000
        });
        
        const result = response.data.chart.result[0];
        const ltp = result.meta.regularMarketPrice;
        const closes = result.indicators.quote[0].close.filter(c => c !== null);
        
        let sma = ltp * 0.94;
        if (closes.length >= 200) {
            const recentCloses = closes.slice(-200);
            sma = recentCloses.reduce((a, b) => a + b, 0) / 200;
        }
        
        return {
            symbol: symbol.replace('.NS', ''),
            ltp: parseFloat(ltp.toFixed(2)),
            sma200: parseFloat(sma.toFixed(2))
        };
    } catch (error) {
        console.error(`Error: ${symbol}`, error.message);
        return null;
    }
}

app.get('/api/stocks', async (req, res) => {
    const results = [];
    
    for (let i = 0; i < NIFTY_SYMBOLS.length; i++) {
        const data = await fetchStockData(NIFTY_SYMBOLS[i]);
        if (data) results.push(data);
        await new Promise(r => setTimeout(r, 500));
    }
    
    for (const stock of results) {
        const ltp = stock.ltp;
        const sma = stock.sma200;
        const lower = sma * (1 - ENV_PERCENT/100);
        const upper = sma * (1 + ENV_PERCENT/100);
        const touch = (upper - lower) * (TOUCH_ZONE / 100);
        
        stock.signal = ltp <= lower + touch ? "BUY" : (ltp >= upper - touch ? "EXIT" : "HOLD");
        stock.lower_band = parseFloat(lower.toFixed(2));
        stock.upper_band = parseFloat(upper.toFixed(2));
    }
    
    res.json({ success: true, data: results, count: results.length });
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
