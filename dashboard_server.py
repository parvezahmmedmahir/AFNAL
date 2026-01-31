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
    description="Professional Unified Hub - Branded Broker API with Supabase Storage",
    version="2.2.0",
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

# --- UTILS ---
async def safe_read_json(file_path: Path):
    """Resilient JSON reading with retries to prevent corruption errors"""
    for _ in range(5):
        try:
            if not file_path.exists(): return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            await asyncio.sleep(0.1)
        except Exception:
            break
    return None

async def get_client():
    global client
    if client is None:
        try:
            email, password = credentials()
            client = Quotex(email=email, password=password)
            check, reason = await client.connect()
            if not check:
                client = None
                return None
        except Exception:
            client = None
            return None
    return client

# --- MASTER API ENDPOINTS (REST) ---

@router.get("/api/price/{asset}")
async def get_latest_price(asset: str):
    """Get latest price for an asset with full schema and market status"""
    try:
        # Load market status
        market_open = True
        status_data = await safe_read_json(DATA_DIR / "market_status.json")
        if status_data and asset in status_data:
            market_open = status_data[asset].get('open', True)

        # 1. Path: Live Snapshot
        snapshot = await safe_read_json(DATA_DIR / "live_snapshot.json")
        if snapshot and asset in snapshot:
            c = snapshot[asset]
            return {
                "asset": asset,
                "price": c['close'],
                "timestamp": c['time'],
                "market_open": market_open,
                "status": "LIVE",
                "candle": {
                    "time": c['time'],
                    "open": c['open'],
                    "high": c['high'],
                    "low": c['low'],
                    "close": c['close']
                },
                "source": "live_streaming"
            }

        # 2. Path: Cache Fallback
        cached = await safe_read_json(RECENT_DIR / f"{asset}.json")
        if cached:
            c = cached[-1]
            return {
                "asset": asset,
                "price": c['close'],
                "timestamp": c['time'],
                "market_open": market_open,
                "status": "CACHED",
                "candle": c,
                "source": "disk_cache"
            }

        return {"asset": asset, "status": "NOT_FOUND"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/snapshot")
async def get_market_snapshot():
    """Aggregated snapshot for all assets"""
    try:
        snapshot = await safe_read_json(DATA_DIR / "live_snapshot.json")
        if not snapshot:
            return {"total": 0, "status": "INITIALIZING", "data": []}
            
        formatted = []
        for asset, c in snapshot.items():
            formatted.append({
                "asset": asset,
                "price": c['close'],
                "timestamp": c['time'],
                "candle": c,
                "source": "live_streaming"
            })
            
        return {
            "total": len(formatted),
            "status": "LIVE",
            "data": sorted(formatted, key=lambda x: x['asset'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/assets")
async def get_assets():
    assets = []
    if RECENT_DIR.exists():
        for file in RECENT_DIR.glob("*.json"):
            assets.append({"symbol": file.stem, "active": True})
    return {"total": len(assets), "assets": sorted(assets, key=lambda x: x['symbol'])}

@router.get("/api/history/{asset}")
async def get_historical_data(asset: str, days: int = 1):
    """Fetches historical data from Supabase (Integration in progress)"""
    # For now, return disk data
    file_path = RECENT_DIR / f"{asset}.json"
    data = await safe_read_json(file_path)
    return {"asset": asset, "count": len(data) if data else 0, "candles": data if data else []}

# --- DASHBOARD WEBSOCKET ---

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read(), status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "hello", "message": "LUX Pro Connection Active"})
    
    cl = await get_client()
    if cl is None:
        await websocket.send_json({"type": "error", "message": "Broker Login Required"})
        await websocket.close()
        return

    # Background Relay
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

    relay_task = asyncio.create_task(relay_ticks())
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data["type"] == "switch":
                asset = data["asset"]
                cl.start_candles_stream(asset, 60)
                history = await cl.get_candles_v3(asset, 600, 60)
                await websocket.send_json({"type": "history", "asset": asset, "data": history})
            elif data["type"] == "subscribe_all":
                instruments = await cl.get_instruments()
                for i in instruments:
                    if len(i) > 14 and i[14]: cl.start_candles_stream(i[1], 60)
    except: pass
    finally:
        relay_task.cancel()

# Global inclusion
app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"💎 LUX MASTER HUB PRO V2.2 LIVE ON PORT {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
