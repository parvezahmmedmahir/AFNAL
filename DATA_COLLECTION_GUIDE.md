# Data Collection System - User Guide

## Overview
You now have a complete, automated data collection system that streams live OTC market data from Quotex and saves it in multiple formats for different use cases.

## System Components

### 1. Dashboard Server (`dashboard_server.py`)
- **Purpose**: Core WebSocket server that connects to Quotex and streams live data
- **Port**: http://127.0.0.1:8000
- **Features**:
  - Connects to your Quotex account
  - Streams live tick data for all open OTC assets
  - Provides historical candle data (up to 600 candles)
  - Auto-refreshes market status every 30 seconds

### 2. Data Collectors (JavaScript)

#### Collector 1: Recent History (`1_recent_history.js`)
- **Purpose**: Maintains the last 600 candles for all assets
- **Storage**: `data/recent/`
- **Format**: One JSON file per asset (e.g., `BTCUSD_otc.json`)
- **Update Frequency**: Saves every 10 seconds
- **Use Case**: Quick access to recent market data for analysis

#### Collector 2: Daily Cycle (`2_daily_cycle.js`)
- **Purpose**: Collects full 24-hour candle data
- **Storage**: `data/24h/`
- **Format**: Daily files (e.g., `BTCUSD_otc_2026-01-31.json`)
- **Rotation**: Automatically deletes old files, keeps only today's data
- **Update Frequency**: Flushes every 30 seconds
- **Use Case**: Daily trading analysis and backtesting

#### Collector 3: Monthly Archive (`3_monthly_archive.js`)
- **Purpose**: Long-term data storage (up to 30 days)
- **Storage**: `data/monthly/`
- **Format**: One master file per asset (e.g., `BTCUSD_otc_full_history.json`)
- **Retention**: Automatically prunes data older than 30 days
- **Update Frequency**: Flushes every 60 seconds
- **Use Case**: Historical analysis, pattern recognition, ML training

## How to Start the System

### Option 1: Manual Start (Step by Step)

1. **Start the Dashboard Server**:
   ```
   python dashboard_server.py
   ```
   Wait for: "Uvicorn running on http://127.0.0.1:8000"

2. **Start Collector 1 (Recent History)**:
   ```
   node collectors/1_recent_history.js
   ```
   Wait for: "✅ [Recent] Connected to WebSocket"

3. **Start Collector 2 (Daily Cycle)**:
   ```
   node collectors/2_daily_cycle.js
   ```
   Wait for: "✅ [24H] Connected to WebSocket"

4. **Start Collector 3 (Monthly Archive)**:
   ```
   node collectors/3_monthly_archive.js
   ```
   Wait for: "✅ [Monthly] Connected to WebSocket"

### Option 2: Use the Launcher (Coming Soon)
Run `start_collectors.bat` to start all components automatically.

## Data Format

All collectors save data in the same candle format:
```json
[
  {
    "time": 1769852220,
    "open": 87688.86,
    "high": 87698.43,
    "low": 87677.53,
    "close": 87680.23
  }
]
```

- **time**: Unix timestamp (seconds)
- **open**: Opening price of the candle
- **high**: Highest price during the candle period
- **low**: Lowest price during the candle period
- **close**: Closing price of the candle

## Important Notes

### Market Behavior
- The system **only collects data when markets are OPEN**
- When a market closes, data collection stops for that asset
- When a market reopens, collection resumes automatically
- No "closed market" data is saved (as requested)

### Data Integrity
- All collectors run independently
- If one collector crashes, others continue working
- Auto-reconnect logic ensures continuous operation
- Data is saved incrementally to prevent loss

### Storage Management
- **Recent**: Limited to 600 candles per asset (~10 hours of 1-minute data)
- **Daily**: Automatically rotates at midnight
- **Monthly**: Auto-prunes data older than 30 days

## Monitoring

### Check if collectors are running:
Look for these messages in the terminal:
- `💾 [Recent] Saving data for X assets...` (every 10s)
- `💾 [24H] Flushing data for X assets...` (every 30s)
- `💾 [Monthly] Archiving data for X assets...` (every 60s)

### Check collected data:
- Navigate to `data/recent/` to see real-time files
- Navigate to `data/24h/` to see today's data
- Navigate to `data/monthly/` to see historical archives

## Accessing the Data

### From Python:
```python
import json

# Load recent data
with open('data/recent/BTCUSD_otc.json', 'r') as f:
    candles = json.load(f)
    
print(f"Latest price: {candles[-1]['close']}")
```

### From JavaScript:
```javascript
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/recent/BTCUSD_otc.json'));
console.log(`Latest price: ${data[data.length-1].close}`);
```

## Troubleshooting

### Collectors keep disconnecting:
- Ensure `dashboard_server.py` is running first
- Check that port 8000 is not blocked by firewall

### No data being saved:
- Verify markets are open (check Quotex platform)
- Ensure `data/` directories exist
- Check terminal for error messages

### Old data not being deleted:
- Daily collector deletes files automatically at midnight
- Monthly collector prunes on each flush cycle

## Current Status

✅ Dashboard Server: Running
✅ Collector 1 (Recent): Running - 50 assets tracked
✅ Collector 2 (Daily): Running
✅ Collector 3 (Monthly): Running

All systems operational and collecting live data!
