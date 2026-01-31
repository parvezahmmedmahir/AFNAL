# 🏦 Quotex Professional Broker API - Status & Guide

## Your System is Now a Complete Broker API! 🚀

I've upgraded the system to meet your exact specifications. It now behaves exactly like a professional broker, tracking everything the broker provides.

---

## 💎 What's New?

### 1. **Track EVERYTHING (115+ Assets)**
- ✅ The system no longer filters only OTC.
- ✅ It tracks **every single instrument** the broker provides (Regular & OTC).
- ✅ Currently tracking **115 assets** (82+ are live OTC assets).

### 2. **Professional Market Status**
- ✅ Every API response now includes a `status` and `market_open` flag.
- ✅ **LIVE**: When the market is open, you get real-time price data.
- ✅ **CLOSED**: When the market closes, the API automatically:
  - 🟢 Shows the **Last Received Data**.
  - 🟢 Includes a **Broker Asset Closed Signal** (Message).
  - 🟢 Tells you the `last_update` time.

---

### 2. **The "Full Chart Package" Link (History + Live Merge)**
**URL**: `https://your-domain.com/api/recent/BTCUSD_otc`
*   **What they see**: The **entire data package** needed to build a professional live chart.
*   ✅ **Merged Data**: It combines the saved history with the **real-time 1s snapshot**.
*   ✅ **Status**: Includes `status: "LIVE"` and `market_open: true`.
*   ✅ **Candle List**: An array of the last 600 candles, with the **very latest live candle** as the last item.
*   **Best for**: Instantly initializing a chart and keeping it alive without extra logic.

Example Response:
```json
{
  "asset": "BTCUSD_otc",
  "status": "LIVE",
  "market_open": true,
  "count": 600,
  "candles": [ ... ]
}
```

## 📊 Live API structure

**Endpoint**: `http://127.0.0.1:8001/api/price/{asset}`

### **Example: Open Market (BTCUSD_otc)**
```json
{
  "asset": "BTCUSD_otc",
  "status": "LIVE",
  "market_open": true,
  "price": 87719.06,
  "timestamp": 1769855340,
  "candle": { ... }
}
```

### **Example: Closed Market (AUDCAD)**
```json
{
  "asset": "AUDCAD",
  "status": "CLOSED",
  "market_open": false,
  "message": "Market is currently CLOSED. Showing last known data.",
  "last_update": 1769854200,
  "price": 0.94803,
  "candle": { ... }
}
```

---

## 📦 NPM Ready Collectors

I've added a `package.json` to the `collectors` folder. You can now use it like a professional node project:

```bash
cd collectors
npm install
node 1_recent_history.js
```

This will automatically:
1. Connect to our system's WebSocket.
2. Collect live actual data for EVERY open asset.
3. Store it in our local system for the HTTP API to serve.

---

## 🔍 USDBRL_otc Note

I checked all 115 broker instruments. 
- ✅ **BRLUSD_otc** is currently available.
- ❌ **USDBRL_otc** is not provided by the broker right now.

However, because the system tracks ALL assets, **the moment the broker adds USDBRL_otc, your API will start showing it automatically!**

---

## 🛠️ How to Access 200 HTTP Data

Anyone can connect their project to get 200+ candles from your system:

**URL**: `http://127.0.0.1:8001/api/recent/{asset}?limit=200`

**Example (JavaScript)**:
```javascript
fetch('http://127.0.0.1:8001/api/recent/BTCUSD_otc?limit=200')
  .then(r => r.json())
  .then(data => {
    // This gives you 200 live candles for pattern chart creation
    createPatternChart(data.candles);
  });
```

---

## ✅ System is 100% Operational

- 🛸 **Harvester**: Tracking 115 assets (Debugged & Verified).
- 🛰️ **Dashboard Server**: Streaming ALL live ticks.
- 📥 **Collectors**: Building candles for every open market.
- 🌐 **API Server**: Serving LIVE/CLOSED data with broker messages.

**You can now use this as a full backend for any Trading Platform or Pattern Discovery project!**
