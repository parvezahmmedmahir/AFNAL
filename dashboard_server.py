from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict
import uvicorn
from fastapi.responses import HTMLResponse
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials

# --- INITIALIZATION ---
app = FastAPI(title="LUX Master Hub Pro", version="2.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"
router = APIRouter(prefix="/lux")

# --- GLOBAL STATE (MEMORY ENGINE) ---
# This fixes the Render "Isolated Container" problem
MASTER_SNAPSHOT: Dict[str, dict] = {}
client = None

async def get_client():
    global client
    if client is None:
        try:
            email, password = credentials()
            client = Quotex(email=email, password=password)
            check, _ = await client.connect()
            if not check: client = None
        except: client = None
    return client

async def core_engine_task():
    """Background task to maintain real-time price state in memory"""
    global client
    while True:
        cl = await get_client()
        if cl:
            try:
                # Poll ticks from broker buffer
                for asset in list(cl.api.realtime_price.keys()):
                    ticks = cl.api.realtime_price.get(asset, [])
                    if ticks:
                        cl.api.realtime_price[asset] = []
                        last_tick = ticks[-1]
                        
                        # Update or Create Candle in Memory
                        price = last_tick['price']
                        t = last_tick['time']
                        candle_time = (t // 60) * 60
                        
                        if asset not in MASTER_SNAPSHOT or MASTER_SNAPSHOT[asset]['time'] != candle_time:
                            MASTER_SNAPSHOT[asset] = {
                                "time": candle_time,
                                "open": price, "high": price, "low": price, "close": price
                            }
                        else:
                            c = MASTER_SNAPSHOT[asset]
                            c['close'] = price
                            c['high'] = max(c['high'], price)
                            c['low'] = min(c['low'], price)
            except: pass
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(core_engine_task())

# --- MASTER API ENDPOINTS ---

@router.get("/api/price/{asset}")
async def get_latest_price(asset: str):
    """Real-time price endpoint using the LUX Memory Engine"""
    # 1. Check Memory Engine (Truly LIVE)
    if asset in MASTER_SNAPSHOT:
        c = MASTER_SNAPSHOT[asset]
        return {
            "asset": asset,
            "price": c['close'],
            "timestamp": c['time'],
            "market_open": True, # If it's in memory, it's open
            "status": "LIVE",
            "candle": c,
            "source": "memory_engine"
        }

    # 2. Check Disk Cache (Fallback)
    try:
        if (RECENT_DIR / f"{asset}.json").exists():
            with open(RECENT_DIR / f"{asset}.json", 'r') as f:
                data = json.load(f)
                if data:
                    return {
                        "asset": asset, "price": data[-1]['close'], "timestamp": data[-1]['time'],
                        "status": "CACHED", "candle": data[-1], "source": "disk_cache"
                    }
    except: pass

    return {"asset": asset, "status": "NOT_FOUND"}

@router.get("/api/snapshot")
async def get_market_snapshot():
    """Returns memory state of all 80+ assets in one go"""
    data = []
    for asset, c in MASTER_SNAPSHOT.items():
        data.append({"asset": asset, "price": c['close'], "ohlc": c})
    return {"total": len(data), "status": "LIVE", "data": data}

@router.get("/api/assets")
async def get_assets():
    assets = []
    if RECENT_DIR.exists():
        for file in RECENT_DIR.glob("*.json"):
            assets.append({"symbol": file.stem, "active": True})
    return {"total": len(assets), "assets": sorted(assets, key=lambda x: x['symbol'])}

# --- DASHBOARD WEBSOCKET ---

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    cl = await get_client()
    if cl is None: 
        await websocket.close()
        return
    
    # Send initial asset list
    try:
        instr = await cl.get_instruments()
        await websocket.send_json({"type": "assets", "data": [{"symbol": i[1], "name": i[2], "open": bool(i[14])} for i in instr if len(i) > 14]})
    except: pass

    try:
        while True:
            # Simple relay of memory engine ticks for dashboard
            for asset, c in MASTER_SNAPSHOT.items():
                await websocket.send_json({"type": "tick", "asset": asset, "data": {"price": c['close'], "time": c['time']}})
            
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data["type"] == "switch":
                asset = data["asset"]
                cl.start_candles_stream(asset, 60)
                history = await cl.get_candles_v3(asset, 600, 60)
                await websocket.send_json({"type": "history", "asset": asset, "data": history})
            elif data["type"] == "subscribe_all":
                instr = await cl.get_instruments()
                for i in instr:
                    if len(i) > 14 and i[14]: cl.start_candles_stream(i[1], 60)
            await asyncio.sleep(1)
    except: pass

app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
