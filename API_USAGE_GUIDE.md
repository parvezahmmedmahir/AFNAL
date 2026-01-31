# OTC Market Data API - Usage Examples

## Your API is Now Live! 🚀

**Base URL**: `http://127.0.0.1:8001`  
**Interactive Docs**: `http://127.0.0.1:8001/docs`

---

## Quick Start

### 1. View Interactive Documentation
Open your browser and go to:
```
http://127.0.0.1:8001/docs
```

This gives you a **Swagger UI** where you can test all endpoints directly in your browser!

---

## API Endpoints

### 📋 Get All Available Assets
```http
GET /api/assets
```

**Example Response:**
```json
{
  "total": 50,
  "assets": [
    {
      "symbol": "BTCUSD_otc",
      "data_available": true,
      "file_size": 253
    },
    ...
  ]
}
```

---

### 📊 Get Recent Data (Last 600 Candles)
```http
GET /api/recent/{asset}?limit=10
```

**Example:**
```
GET http://127.0.0.1:8001/api/recent/BTCUSD_otc?limit=10
```

**Response:**
```json
{
  "asset": "BTCUSD_otc",
  "timeframe": "1m",
  "count": 10,
  "candles": [
    {
      "time": 1769852220,
      "open": 87688.86,
      "high": 87698.43,
      "low": 87677.53,
      "close": 87680.23
    },
    ...
  ]
}
```

---

### 💰 Get Latest Price
```http
GET /api/price/{asset}
```

**Example:**
```
GET http://127.0.0.1:8001/api/price/BTCUSD_otc
```

**Response:**
```json
{
  "asset": "BTCUSD_otc",
  "price": 87680.23,
  "timestamp": 1769852220,
  "candle": {
    "time": 1769852220,
    "open": 87688.86,
    "high": 87698.43,
    "low": 87677.53,
    "close": 87680.23
  }
}
```

---

### 📈 Get OHLC Data
```http
GET /api/ohlc/{asset}?period=5
```

**Example:**
```
GET http://127.0.0.1:8001/api/ohlc/BTCUSD_otc?period=5
```

**Response:**
```json
{
  "asset": "BTCUSD_otc",
  "period": 5,
  "ohlc": {
    "open": 87688.86,
    "high": 87698.43,
    "low": 87677.53,
    "close": 87680.23,
    "start_time": 1769852100,
    "end_time": 1769852220
  }
}
```

---

### 📅 Get Daily Data
```http
GET /api/daily/{asset}?date=2026-01-31
```

**Example:**
```
GET http://127.0.0.1:8001/api/daily/BTCUSD_otc?date=2026-01-31
```

---

### 📆 Get Monthly Archive
```http
GET /api/monthly/{asset}?limit=100
```

**Example:**
```
GET http://127.0.0.1:8001/api/monthly/BTCUSD_otc?limit=100
```

---

## Code Examples

### Python Example

```python
import requests

# Base URL
API_URL = "http://127.0.0.1:8001"

# 1. Get all assets
response = requests.get(f"{API_URL}/api/assets")
assets = response.json()
print(f"Total assets: {assets['total']}")

# 2. Get latest price for Bitcoin
response = requests.get(f"{API_URL}/api/price/BTCUSD_otc")
data = response.json()
print(f"BTC Price: ${data['price']}")

# 3. Get last 50 candles
response = requests.get(f"{API_URL}/api/recent/BTCUSD_otc?limit=50")
candles = response.json()['candles']
print(f"Received {len(candles)} candles")

# 4. Get OHLC for last 10 minutes
response = requests.get(f"{API_URL}/api/ohlc/EURUSD_otc?period=10")
ohlc = response.json()['ohlc']
print(f"EUR/USD - O: {ohlc['open']}, H: {ohlc['high']}, L: {ohlc['low']}, C: {ohlc['close']}")
```

---

### JavaScript Example (Node.js)

```javascript
const axios = require('axios');

const API_URL = 'http://127.0.0.1:8001';

// 1. Get all assets
async function getAssets() {
  const response = await axios.get(`${API_URL}/api/assets`);
  console.log(`Total assets: ${response.data.total}`);
  return response.data.assets;
}

// 2. Get latest price
async function getPrice(asset) {
  const response = await axios.get(`${API_URL}/api/price/${asset}`);
  console.log(`${asset} Price: $${response.data.price}`);
  return response.data;
}

// 3. Get recent candles
async function getCandles(asset, limit = 50) {
  const response = await axios.get(`${API_URL}/api/recent/${asset}?limit=${limit}`);
  return response.data.candles;
}

// Usage
(async () => {
  await getAssets();
  await getPrice('BTCUSD_otc');
  const candles = await getCandles('EURUSD_otc', 100);
  console.log(`Received ${candles.length} candles`);
})();
```

---

### JavaScript Example (Browser / Fetch API)

```javascript
const API_URL = 'http://127.0.0.1:8001';

// Get latest price
fetch(`${API_URL}/api/price/BTCUSD_otc`)
  .then(response => response.json())
  .then(data => {
    console.log(`BTC Price: $${data.price}`);
  });

// Get recent candles
fetch(`${API_URL}/api/recent/EURUSD_otc?limit=50`)
  .then(response => response.json())
  .then(data => {
    console.log(`Received ${data.count} candles`);
    data.candles.forEach(candle => {
      console.log(`Time: ${candle.time}, Close: ${candle.close}`);
    });
  });
```

---

### cURL Examples

```bash
# Get all assets
curl http://127.0.0.1:8001/api/assets

# Get latest BTC price
curl http://127.0.0.1:8001/api/price/BTCUSD_otc

# Get last 10 candles
curl "http://127.0.0.1:8001/api/recent/BTCUSD_otc?limit=10"

# Get OHLC for last 5 candles
curl "http://127.0.0.1:8001/api/ohlc/EURUSD_otc?period=5"

# Health check
curl http://127.0.0.1:8001/api/health
```

---

## Making Your API Public (Optional)

### Option 1: Local Network Access
Your API is already accessible on your local network at:
```
http://YOUR_LOCAL_IP:8001
```

Find your IP:
```bash
# Windows
ipconfig

# Look for "IPv4 Address" (e.g., 192.168.1.100)
```

Then access from other devices:
```
http://192.168.1.100:8001/api/price/BTCUSD_otc
```

---

### Option 2: Deploy to Cloud (Render, Heroku, etc.)

Your API is already structured for deployment. Just:

1. Push to GitHub
2. Connect to Render/Heroku
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python api_server.py`

---

## WebSocket API (Already Available!)

For **real-time streaming**, use the existing WebSocket server:

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'tick') {
    console.log(`${msg.asset}: $${msg.data.price}`);
  }
};

// Subscribe to all assets
ws.send(JSON.stringify({ type: 'subscribe_all' }));
```

---

## API Features Summary

✅ **RESTful API** - Standard HTTP endpoints  
✅ **Real-time WebSocket** - Live price streaming  
✅ **Auto-generated docs** - Interactive Swagger UI  
✅ **CORS enabled** - Access from any domain  
✅ **Multiple timeframes** - Recent, Daily, Monthly  
✅ **Flexible queries** - Limit, date filters  
✅ **Health monitoring** - Status endpoints  

---

## Running the Full System

```bash
# Terminal 1: Data Collection Server
python dashboard_server.py

# Terminal 2: REST API Server
python api_server.py

# Terminal 3-5: Data Collectors
node collectors/1_recent_history.js
node collectors/2_daily_cycle.js
node collectors/3_monthly_archive.js
```

Or use the launcher:
```bash
start_collectors.bat
```

Then separately:
```bash
python api_server.py
```

---

## Your API is Production-Ready! 🎉

You now have a **professional-grade market data API** that:
- Streams live data from Quotex
- Stores historical data automatically
- Provides REST and WebSocket access
- Works exactly like commercial APIs (Binance, Coinbase, etc.)

**Access it anywhere in your code, from any language, just like a real API!**
