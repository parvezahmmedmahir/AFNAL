# 🚀 How to Deploy Your Broker API Prototype

This guide explains how to publish your system as a professional website and API on your own domain.

---

## 🏛️ Deployment Strategy

To run a professional API that collects real-time data 24/7, you need a platform that supports **Background Workers** and **WebSockets**.

### 1. **Vercel (Frontend Only)**
- **Use for**: `index.html`, `api_demo.html`.
- **Pros**: Fast, free, professional domain (e.g., `yourbrand.vercel.app`).
- **Cons**: Cannot run the Python/Node collectors (Backend).

### 2. **Render.com / Railway.app (Recommended Backend)**
- **Use for**: API Server, Dashboard Server, Harvester, Collectors.
- **Pros**: Supports Python/Node together, can run 24/7, handles WebSockets.
- **Cons**: Paid tier needed for 24/7 reliability ($7/mo).

---

## 🛠️ Step-by-Step Deployment (Render.com)

I have created a `render.yaml` file in your root folder. This is a **Blueprint** that sets up everything automatically.

1. **Push your code to GitHub**.
2. **Open Render.com** and connect your GitHub.
3. **Create a "Blueprint"**: Select your repository.
4. Render will automatically see `render.yaml` and create:
   - ✅ **API Hub (Port 8001)**: Your REST API.
   - ✅ **WS Server (Port 8000)**: Your WebSocket stream.
   - ✅ **Harvester**: The engine connecting to Quotex.
   - ✅ **Collectors**: The system saving candle data.

---

## 🌍 How to Present as "Your Own Domain"

1. **Buy a domain** (e.g., `mahir-api.com`).
2. **Point it to Render**: In Render settings, add your Custom Domain.
3. **Branded API Endpoints**:
   - `https://api.mahir-api.com/api/price/BTCUSD_otc`
   - `https://api.mahir-api.com/api/recent/EURUSD_otc?limit=200`

---

## 🔧 Fixes Included in this Prototype

I have updated your code to fix the issues you mentioned:

### ✅ **Fix: "Cannot read properties of undefined (reading 'update')"**
- I updated `index.html`. It now safely checks if the chart and data are ready before updating.
- The chart will no longer crash if history is slow to load.

### ✅ **Fix: "History: 0 candles"**
- I updated `dashboard_server.py`. 
- **New Logic**: If the Broker returns 0 candles, the system now automatically falls back to our own **Local Data Collection**. 
- You will always see data if the collector is running!

### ✅ **Real-time 1S Snapshot**
- Added a `live_snapshot.json` mechanism.
- The API now returns the **Actual Live Candle** being formed right now, updated every 2 seconds.

---

## 🎨 Branding Your Prototype

To make it look like a unique prototype:
1. Edit `index.html` header text (currently "PyQuotex Pro").
2. Change the theme color in Tailwind (e.g., change `blue-600` to `purple-600`).
3. Your API responses now include `"source": "live_streaming"` so users know it's real-time.

---

## 📦 Next Steps

1. **Install Git** (if you haven't).
2. `git init`
3. `git add .`
4. `git commit -m "Initialize Professional Broker API"`
5. Create a private GitHub Repo and push.
6. Connect to **Render.com**.

**Your system is now a ready-to-deploy commercial prototype! 🚀**
