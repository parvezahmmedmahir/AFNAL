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
from supabase_db import save_candle_realtime

# --- INITIALIZATION ---
app = FastAPI(title="LUX Master Hub Pro", version="2.4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"
router = APIRouter(prefix="/lux")

# --- GLOBAL STATE (MEMORY ENGINE) ---
MASTER_SNAPSHOT: Dict[str, dict] = {}
client = None
last_reconnect_attempt = 0
reconnect_cooldown = 30 # Seconds

async def get_client():
    global client, last_reconnect_attempt
    
    if client is not None:
        return client

    # Prevent rapid-fire login attempts (Anti-spam cooldown)
    now = time.time()
    if now - last_reconnect_attempt < reconnect_cooldown:
        return None

    last_reconnect_attempt = now
    print("🚀 Connecting User Account ...")
    try:
        email, password = credentials()
        client = Quotex(email=email, password=password)
        check, reason = await client.connect()
        
        if not check:
            print(f"❌ Connection Failed: {reason}")
            client = None
            return None
            
        print("✅ Account Connected Successfully!")
        # --- AUTO-SUBSCRIBE TO ALL ASSETS ON STARTUP ---
        # Run this in background so we don't block the memory engine
        asyncio.create_task(subscribe_all_assets(client))
        return client
        
    except Exception as e:
        print(f"❌ Client Init Error: {e}")
        client = None
        return None

async def subscribe_all_assets(cl):
    """Subscribes to all active instruments for real-time memory tracking"""
    try:
        print("🔍 Scanning markets for broad subscription...")
        instr = await cl.get_instruments()
        count = 0
        for i in instr:
            if len(i) > 14 and i[14]: # If open
                cl.start_candles_stream(i[1], 60)
                count += 1
                if count % 10 == 0: await asyncio.sleep(0.5) # Throttle subscription
        print(f"✅ Subscribed to {count} assets for real-time tracking.")
    except Exception as e:
        print(f"⚠️ Subscription Error: {e}")

async def core_engine_task():
    """Maintains real-time state and pushes to Supabase in milliseconds"""
    while True:
        cl = await get_client()
        if cl:
            try:
                for asset in list(cl.api.realtime_price.keys()):
                    ticks = cl.api.realtime_price.get(asset, [])
                    if ticks:
                        cl.api.realtime_price[asset] = []
                        last_tick = ticks[-1]
                        
                        price = last_tick['price']
                        t = last_tick['time']
                        candle_time = (t // 60) * 60
                        
                        # Memory Update
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
                        
                        # --- REAL-TIME SUPABASE PUSH ---
                        # Saves to cloud in milliseconds
                        save_candle_realtime(asset, MASTER_SNAPSHOT[asset])
                        
            except: pass
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(core_engine_task())

# --- MASTER API ENDPOINTS ---

@router.get("/api/price/{asset}")
async def get_latest_price(asset: str):
    """Real-time price API with exact LUX schema"""
    # 1. Memory Engine (Truly LIVE)
    if asset in MASTER_SNAPSHOT:
        c = MASTER_SNAPSHOT[asset]
        return {
            "asset": asset,
            "price": c['close'],
            "timestamp": c['time'],
            "market_open": True,
            "status": "LIVE",
            "candle": c,
            "source": "live_streaming"
        }

    # 2. Disk Fallback
    try:
        if (RECENT_DIR / f"{asset}.json").exists():
            with open(RECENT_DIR / f"{asset}.json", 'r') as f:
                data = json.load(f)
                if data:
                    c = data[-1]
                    return {
                        "asset": asset, "price": c['close'], "timestamp": c['time'],
                        "market_open": True, "status": "CACHED", "candle": c, "source": "disk_cache"
                    }
    except: pass

    return {"asset": asset, "status": "NOT_FOUND"}

@router.get("/api/snapshot")
async def get_market_snapshot():
    """Full cloud snapshot for all assets"""
    data = []
    for asset, c in MASTER_SNAPSHOT.items():
        data.append({
            "asset": asset,
            "price": c['close'],
            "timestamp": c['time'],
            "market_open": True,
            "status": "LIVE",
            "candle": c,
            "source": "live_streaming"
        })
    return {"total": len(data), "status": "LIVE", "data": data}

@router.get("/api/assets")
async def get_assets():
    assets = []
    if RECENT_DIR.exists():
        for file in RECENT_DIR.glob("*.json"):
            assets.append({"symbol": file.stem, "active": True})
    return {"total": len(assets), "assets": sorted(assets, key=lambda x: x['symbol'])}

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    cl = await get_client()
    if cl:
        try:
            instr = await cl.get_instruments()
            await websocket.send_json({"type": "assets", "data": [{"symbol": i[1], "name": i[2], "open": bool(i[14])} for i in instr if len(i) > 14]})
        except: pass

    try:
        while True:
            # Relay ticks from memory engine
            for asset, c in MASTER_SNAPSHOT.items():
                await websocket.send_json({"type": "tick", "asset": asset, "data": {"price": c['close'], "time": c['time']}})
            
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data["type"] == "switch":
                asset = data["asset"]
                cl.start_candles_stream(asset, 60)
                history = await cl.get_candles_v3(asset, 600, 60)
                await websocket.send_json({"type": "history", "asset": asset, "data": history})
            await asyncio.sleep(1)
    except: pass

app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"💎 LUX MASTER HUB V2.4 (Supabase Real-time) LIVE ON PORT {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
