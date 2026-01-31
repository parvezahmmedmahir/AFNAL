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
    title="LUX Master Hub", 
    description="Unified API and WebSocket Hub for Quotex OTC Markets",
    version="2.0.0",
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
        "endpoints": {
            "assets": "/lux/api/assets",
            "price": "/lux/api/price/{asset}",
            "recent": "/lux/api/recent/{asset}",
            "docs": "/lux/docs"
        }
    }

@router.get("/api/assets")
async def get_assets():
    try:
        assets = []
        if RECENT_DIR.exists():
            for file in RECENT_DIR.glob("*.json"):
                assets.append({
                    "symbol": file.stem,
                    "active": True,
                    "file_size": file.stat().st_size
                })
        return {"total": len(assets), "assets": sorted(assets, key=lambda x: x['symbol'])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/price/{asset}")
async def get_latest_price(asset: str):
    try:
        snapshot_file = DATA_DIR / "live_snapshot.json"
        if snapshot_file.exists():
            with open(snapshot_file, 'r') as f:
                snapshot = json.load(f)
                if asset in snapshot:
                    return {
                        "asset": asset,
                        "price": snapshot[asset]['close'],
                        "timestamp": snapshot[asset]['time'],
                        "status": "LIVE",
                        "market_open": True
                    }
        return {"asset": asset, "status": "CLOSED", "market_open": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/recent/{asset}")
async def get_recent_data(asset: str, limit: Optional[int] = 600):
    try:
        file_path = RECENT_DIR / f"{asset}.json"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Asset not found")
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
    await websocket.send_json({"type": "hello", "message": "LUX Master Hub Activated"})
    
    cl = await get_client()
    if cl is None:
        email, password = credentials()
        _, reason = await Quotex(email=email, password=password).connect()
        await websocket.send_json({"type": "error", "message": f"Broker connection failed: {reason}"})
        await websocket.close()
        return

    # Send initial asset list
    instruments = await cl.get_instruments()
    asset_list = []
    for i in instruments:
        if len(i) > 14:
            asset_list.append({"symbol": i[1], "name": i[2], "open": bool(i[14])})
    await websocket.send_json({"type": "assets", "data": asset_list})

    active_asset = None
    
    # Background relay task
    async def relay_ticks():
        try:
            while True:
                for asset in list(cl.api.realtime_price.keys()):
                    ticks = cl.api.realtime_price.get(asset, [])
                    if ticks:
                        cl.api.realtime_price[asset] = []
                        for tick in ticks:
                            await websocket.send_json({"type": "tick", "asset": asset, "data": tick})
                await asyncio.sleep(0.05)
        except:
            pass

    asyncio.create_task(relay_ticks())
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data["type"] == "switch":
                active_asset = data["asset"]
                cl.start_candles_stream(active_asset, 60)
                history = await cl.get_candles_v3(active_asset, 600, 60)
                await websocket.send_json({"type": "history", "asset": active_asset, "data": history})
            elif data["type"] == "subscribe_all":
                for i in instruments:
                    if i[14]: cl.start_candles_stream(i[1], 60)
    except:
        pass

# Include all API routes
app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"💎 LUX MASTER HUB LIVE ON PORT {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
