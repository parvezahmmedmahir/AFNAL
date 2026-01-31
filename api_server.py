from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from pathlib import Path
from typing import Optional, List
import uvicorn

app = FastAPI(
    title="OTC Market Data API",
    description="Real-time and historical OTC market data from Quotex",
    version="1.0.0"
)

# Enable CORS for external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefix all routes with /lux
router = APIRouter(prefix="/lux")

# Data directories
DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"
DAILY_DIR = DATA_DIR / "24h"
MONTHLY_DIR = DATA_DIR / "monthly"

@router.get("/")
async def root():
    """API Information"""
    return {
        "name": "OTC Market Data API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "assets": "/lux/api/assets",
            "recent": "/lux/api/recent/{asset}",
            "daily": "/lux/api/daily/{asset}",
            "monthly": "/lux/api/monthly/{asset}",
            "latest_price": "/lux/api/price/{asset}",
            "ohlc": "/lux/api/ohlc/{asset}"
        }
    }

@router.get("/api/assets")
async def get_assets():
    """Get list of all available assets"""
    try:
        assets = []
        if RECENT_DIR.exists():
            for file in RECENT_DIR.glob("*.json"):
                asset_name = file.stem  # filename without .json
                file_size = file.stat().st_size
                assets.append({
                    "symbol": asset_name,
                    "data_available": file_size > 10,
                    "file_size": file_size
                })
        
        return {
            "total": len(assets),
            "assets": sorted(assets, key=lambda x: x['symbol'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/recent/{asset}")
async def get_recent_data(asset: str, limit: Optional[int] = None):
    """
    Get recent candle data with LIVE status and real-time merge
    
    - **asset**: Asset symbol (e.g., BTCUSD_otc)
    - **limit**: Optional limit on number of candles to return
    """
    try:
        file_path = RECENT_DIR / f"{asset}.json"
        
        # 1. Get History
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Asset {asset} not found")
        
        with open(file_path, 'r') as f:
            candles = json.load(f)
        
        # 2. Get Live Snapshot (for 1s level accuracy)
        snapshot_file = DATA_DIR / "live_snapshot.json"
        live_candle = None
        if snapshot_file.exists():
            try:
                with open(snapshot_file, 'r') as f:
                    snapshot = json.load(f)
                    live_candle = snapshot.get(asset)
            except:
                pass
        
        # 3. Merge Live Candle into History if newer
        if live_candle and candles:
            if live_candle['time'] > candles[-1]['time']:
                candles.append(live_candle)
            elif live_candle['time'] == candles[-1]['time']:
                # Update existing last candle with most recent tick data
                candles[-1] = live_candle
        elif live_candle and not candles:
            candles = [live_candle]

        # 4. Get Market Status
        market_status = await get_market_status(asset)
        status_msg = "LIVE" if (market_status and market_status['open']) else "CLOSED"
        
        if limit:
            candles = candles[-limit:]
        
        return {
            "asset": asset,
            "status": status_msg,
            "market_open": market_status['open'] if market_status else False,
            "timeframe": "1m",
            "count": len(candles),
            "last_update": candles[-1]['time'] if candles else None,
            "candles": candles
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid data format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/daily/{asset}")
async def get_daily_data(asset: str, date: Optional[str] = None):
    """
    Get 24-hour candle data
    
    - **asset**: Asset symbol (e.g., BTCUSD_otc)
    - **date**: Optional date in YYYY-MM-DD format (defaults to today)
    """
    try:
        from datetime import datetime
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        file_path = DAILY_DIR / f"{asset}_{date}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"No data for {asset} on {date}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return {
            "asset": asset,
            "date": date,
            "timeframe": "1m",
            "count": len(data),
            "candles": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/monthly/{asset}")
async def get_monthly_data(asset: str, limit: Optional[int] = None):
    """
    Get monthly archive data (up to 30 days)
    
    - **asset**: Asset symbol (e.g., BTCUSD_otc)
    - **limit**: Optional limit on number of candles to return
    """
    try:
        file_path = MONTHLY_DIR / f"{asset}_full_history.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"No monthly data for {asset}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if limit:
            data = data[-limit:]
        
        return {
            "asset": asset,
            "timeframe": "1m",
            "retention": "30 days",
            "count": len(data),
            "candles": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/price/{asset}")
async def get_latest_price(asset: str):
    """
    Get the latest price for an asset with market status
    
    - **asset**: Asset symbol (e.g., BTCUSD_otc)
    
    Returns live data if market is OPEN, or last known data with CLOSED status
    """
    try:
        # 1. Try Live Snapshot first (Real-time aggregated by collector)
        snapshot_file = DATA_DIR / "live_snapshot.json"
        if snapshot_file.exists():
            try:
                with open(snapshot_file, 'r') as f:
                    snapshot = json.load(f)
                    if asset in snapshot:
                        live_data = snapshot[asset]
                        status = "LIVE" if live_data.get('market_open', True) else "CLOSED"
                        return {
                            "asset": asset,
                            "price": live_data['close'],
                            "timestamp": live_data['time'],
                            "market_open": live_data.get('market_open', True),
                            "status": status,
                            "candle": live_data,
                            "source": "live_streaming"
                        }
            except:
                pass

        # 2. Fallback to Recent files (Saved every 10s)
        file_path = RECENT_DIR / f"{asset}.json"
        
        # Get current market status from broker
        market_status = await get_market_status(asset)
        
        if not file_path.exists():
            # Asset not found in our data, but check if it exists in broker
            if market_status:
                return {
                    "asset": asset,
                    "status": "INITIALIZING",
                    "market_open": market_status['open'],
                    "message": "Asset found in broker but data collection starting. Please wait 10-30 seconds.",
                    "price": None,
                    "timestamp": None
                }
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Asset {asset} not found in broker. Check /api/assets for available assets."
                )
        
        # Load last known data
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not data:
            raise HTTPException(status_code=404, detail="No data available yet")
        
        latest = data[-1]
        
        # Build response with market status
        response = {
            "asset": asset,
            "price": latest['close'],
            "timestamp": latest['time'],
            "market_open": market_status['open'] if market_status else False,
            "status": "LIVE" if (market_status and market_status['open']) else "CLOSED",
            "candle": latest,
            "source": "database_disk"
        }
        
        # Add message if market is closed
        if not (market_status and market_status['open']):
            response["message"] = "Market is currently CLOSED. Showing last known data."
            response["last_update"] = latest['time']
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid data format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_market_status(asset: str):
    """Get real-time market status from broker"""
    try:
        # Read from a status cache file that the harvester updates
        status_file = DATA_DIR / "market_status.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                all_status = json.load(f)
                return all_status.get(asset)
        return None
    except:
        return None

@router.get("/api/ohlc/{asset}")
async def get_ohlc(asset: str, period: Optional[int] = 1):
    """
    Get OHLC data for the last N candles
    
    - **asset**: Asset symbol (e.g., BTCUSD_otc)
    - **period**: Number of recent candles (default: 1)
    """
    try:
        file_path = RECENT_DIR / f"{asset}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Asset {asset} not found")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        
        recent_candles = data[-period:]
        
        # Calculate aggregate OHLC if multiple candles
        if len(recent_candles) > 1:
            ohlc = {
                "open": recent_candles[0]['open'],
                "high": max(c['high'] for c in recent_candles),
                "low": min(c['low'] for c in recent_candles),
                "close": recent_candles[-1]['close'],
                "start_time": recent_candles[0]['time'],
                "end_time": recent_candles[-1]['time']
            }
        else:
            ohlc = recent_candles[0]
        
        return {
            "asset": asset,
            "period": period,
            "ohlc": ohlc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "data_directories": {
            "recent": RECENT_DIR.exists(),
            "daily": DAILY_DIR.exists(),
            "monthly": MONTHLY_DIR.exists()
        }
    }

# Include the router in the app
app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Starting OTC Market Data API on port {port}...")
    print(f"📊 API Documentation: http://0.0.0.0:{port}/lux/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
