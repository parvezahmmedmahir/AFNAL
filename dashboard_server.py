from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import uvicorn
from fastapi.responses import HTMLResponse
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials, load_session

# --- INITIALIZATION ---
app = FastAPI(
    title="LUX Master Hub Pro", 
    description="Professional Unified Hub - Branded Broker API",
    version="2.1.0",
    docs_url="/lux/docs",
    redoc_url="/lux/redoc",
    openapi_url="/lux/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directories
DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"
DAILY_DIR = DATA_DIR / "24h"
MONTHLY_DIR = DATA_DIR / "monthly"

# Global Quotex client
client = None

# API Router with prefix
router = APIRouter(prefix="/lux")

async def get_client():
    global client
    if client is None:
        print("Initializing Quotex client...")
        try:
            email, password = credentials()
            client = Quotex(email=email, password=password)
            check, reason = await client.connect()
            if not check:
                print(f"Connection failed: {reason}")
                client = None
                return None
            print("Quotex client initialized.")
        except Exception as e:
            print(f"Error initializing client: {e}")
            client = None
            return None
    return client

# --- MASTER API ENDPOINTS (REST) ---

@router.get("/")
async def api_root():
    return {
        "name": "LUX Professional Broker API",
        "status": "operational",
        "v": "2.1.0",
        "endpoints": {
            "assets": "/lux/api/assets",
            "price": "/lux/api/price/{asset}",
            "recent": "/lux/api/recent/{asset}",
            "docs": "/lux/docs"
        }
    }

@router.get("/api/assets")
async def get_assets():
    """Get list of all available assets with status and size metadata"""
    try:
        assets = []
        if RECENT_DIR.exists():
            for file in RECENT_DIR.glob("*.json"):
                f_size = file.stat().st_size
                assets.append({
                    "symbol": file.stem,
                    "active": True,
                    "data_available": f_size > 10,
                    "file_size": f_size
                })
        
        # Also check market_status.json if available
        status_file = DATA_DIR / "market_status.json"
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    market_status = json.load(f)
                    for asset, info in market_status.items():
                        # Update existing or add new
                        found = False
                        for a in assets:
                            if a['symbol'] == asset:
                                a['open'] = info.get('open', False)
                                a['name'] = info.get('name', asset)
                                found = True
                                break
                        if not found:
                            assets.append({
                                "symbol": asset,
                                "name": info.get('name', asset),
                                "open": info.get('open', False),
                                "active": False,
                                "data_available": False
                            })
            except: pass

        return {
            "total": len(assets), 
            "assets": sorted(assets, key=lambda x: x['symbol'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/price/{asset}")
async def get_latest_price(asset: str):
    """Get latest price for an asset with full OHLC data"""
    try:
        # Path 1: Live Snapshot (Aggregated by Node.js collector)
        snapshot_file = DATA_DIR / "live_snapshot.json"
        if snapshot_file.exists():
            try:
                for _ in range(3):
                    try:
                        with open(snapshot_file, 'r') as f:
                            snapshot = json.load(f)
                            if asset in snapshot:
                                candle = snapshot[asset]
                                return {
                                    "asset": asset,
                                    "price": candle['close'],
                                    "open": candle['open'],
                                    "high": candle['high'],
                                    "low": candle['low'],
                                    "close": candle['close'],
                                    "timestamp": candle['time'],
                                    "source": "live_streaming",
                                    "status": "LIVE"
                                }
                        break
                    except json.JSONDecodeError:
                        await asyncio.sleep(0.1)
            except: pass

        # Path 2: Recent History File Fallback
        recent_file = RECENT_DIR / f"{asset}.json"
        if recent_file.exists():
            try:
                with open(recent_file, 'r') as f:
                    candles = json.load(f)
                    if candles:
                        last = candles[-1]
                        return {
                            "asset": asset,
                            "price": last['close'],
                            "open": last['open'],
                            "high": last['high'],
                            "low": last['low'],
                            "close": last['close'],
                            "timestamp": last['time'],
                            "source": "disk_cache",
                            "status": "CACHED"
                        }
            except: pass

        return {"asset": asset, "status": "NOT_FOUND", "message": "No data available yet"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/recent/{asset}")
async def get_recent_data(asset: str, limit: Optional[int] = 600):
    """Get recent history candles"""
    try:
        file_path = RECENT_DIR / f"{asset}.json"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Data for {asset} not found")
        
        with open(file_path, 'r') as f:
            candles = json.load(f)
            
        return {
            "asset": asset,
            "count": len(candles[-limit:]),
            "candles": candles[-limit:]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DASHBOARD LOGIC (WEBSOCKETS) ---

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read(), status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "hello", "message": "LUX Professional Stream Connected"})
    
    cl = await get_client()
    if cl is None:
        # Try to provide real reason
        await websocket.send_json({"type": "error", "message": "Broker Login Required. Check Render logs/env variables."})
        await websocket.close()
        return

    # 1. Helper: Format assets for client
    async def get_client_assets():
        raw = await cl.get_instruments()
        return [{"symbol": i[1], "name": i[2], "open": bool(i[14])} for i in raw if len(i) > 14]

    # Initial send
    initial_assets = await get_client_assets()
    await websocket.send_json({"type": "assets", "data": initial_assets})

    # 2. Market Monitor Task (Keeps client asset list fresh)
    async def market_monitor():
        while True:
            try:
                await asyncio.sleep(30)
                updated = await get_client_assets()
                await websocket.send_json({"type": "assets", "data": updated})
            except: break

    # 3. Tick Relay Task
    async def relay_ticks():
        try:
            while True:
                current_assets = list(cl.api.realtime_price.keys())
                for asset in current_assets:
                    ticks = cl.api.realtime_price.get(asset, [])
                    if ticks:
                        cl.api.realtime_price[asset] = []
                        for tick in ticks:
                            await websocket.send_json({"type": "tick", "asset": asset, "data": tick})
                await asyncio.sleep(0.05)
        except: pass

    monitor_task = asyncio.create_task(market_monitor())
    relay_task = asyncio.create_task(relay_ticks())
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            if data["type"] == "switch":
                asset = data["asset"]
                period = data.get("period", 60)
                cl.start_candles_stream(asset, period)
                history = await cl.get_candles_v3(asset, 600, period)
                await websocket.send_json({"type": "history", "asset": asset, "data": history})
                
            elif data["type"] == "subscribe_all":
                instruments = await cl.get_instruments()
                for i in instruments:
                    if len(i) > 14 and i[14]: # if open
                        cl.start_candles_stream(i[1], 60)
                await websocket.send_json({"type": "info", "message": "Subscribed to all open streams"})
                
    except (WebSocketDisconnect, ConnectionError):
        pass
    finally:
        monitor_task.cancel()
        relay_task.cancel()

# Global inclusion
app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"💎 LUX MASTER HUB PRO V2.1 LIVE ON PORT {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
