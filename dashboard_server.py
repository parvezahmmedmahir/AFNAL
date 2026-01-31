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

# --- CONFIGURATION ---
app = FastAPI(title="LUX Master Hub Pro", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"
RECENT_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/lux")

# --- GLOBAL STATE ENGINE ---
MASTER_SNAPSHOT: Dict[str, dict] = {}
client = None
broker_status = "DISCONNECTED"
last_login_error = ""

async def get_client():
    global client, broker_status, last_login_error
    if client is not None:
        return client
    
    broker_status = "CONNECTING..."
    try:
        email, password = credentials()
        cl = Quotex(email=email, password=password)
        check, reason = await cl.connect()
        
        if not check:
            broker_status = "FAILED"
            last_login_error = reason
            print(f"❌ [HARVESTER] Login Failed: {reason}")
            return None
            
        print("✅ [HARVESTER] Account Connected!")
        broker_status = "CONNECTED"
        client = cl
        asyncio.create_task(broadcast_subscription(cl))
        return cl
    except Exception as e:
        broker_status = "ERROR"
        last_login_error = str(e)
        print(f"❌ [HARVESTER] Critical Init Error: {e}")
        return None

async def broadcast_subscription(cl):
    """Subscribes to all assets with a safety throttle"""
    try:
        print("🔍 [HARVESTER] Scanning for all open markets...")
        instruments = await cl.get_instruments()
        count = 0
        for i in instruments:
            if len(i) > 14 and i[14]: # If open
                asset = i[1]
                cl.start_candles_stream(asset, 60)
                count += 1
                if count % 5 == 0: await asyncio.sleep(0.5) # Anti-ban throttle
        print(f"🚀 [HARVESTER] Collecting live data for {count} assets.")
    except Exception as e:
        print(f"⚠️ [HARVESTER] Subscription Error: {e}")

async def harvester_engine():
    """The Core Harvesting Loop - Mirroring JS functionality but on Python speed"""
    while True:
        cl = await get_client()
        if not cl:
            await asyncio.sleep(10) # Wait before retry
            continue
            
        try:
            # 1. Process Real-time Ticks
            current_assets = list(cl.api.realtime_price.keys())
            for asset in current_assets:
                ticks = cl.api.realtime_price.get(asset, [])
                if ticks:
                    cl.api.realtime_price[asset] = [] # Flush buffer
                    last_tick = ticks[-1]
                    
                    price = last_tick['price']
                    timestamp = last_tick['time']
                    candle_time = (timestamp // 60) * 60
                    
                    # 2. Update In-Memory Candle
                    if asset not in MASTER_SNAPSHOT or MASTER_SNAPSHOT[asset]['time'] != candle_time:
                        # New Minute Candle
                        MASTER_SNAPSHOT[asset] = {
                            "time": candle_time,
                            "open": price, "high": price, "low": price, "close": price
                        }
                    else:
                        # Update current candle
                        c = MASTER_SNAPSHOT[asset]
                        c['close'] = price
                        c['high'] = max(c['high'], price)
                        c['low'] = min(c['low'], price)
                    
                    # 3. Millisecond Injection to Supabase
                    save_candle_realtime(asset, MASTER_SNAPSHOT[asset])
                    
            # 4. Periodic Local Persistence (Mirroring JS files)
            # We do this every 5 seconds to avoid disk stress
            if int(time.time()) % 5 == 0:
                # Save live snapshot
                with open(DATA_DIR / "live_snapshot.json", "w") as f:
                    json.dump(MASTER_SNAPSHOT, f)
                
        except Exception as e:
            print(f"⚠️ [HARVESTER] Loop Warning: {e}")
            
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(harvester_engine())

# --- API ENDPOINTS ---

@router.get("/health")
async def health_check():
    return {
        "broker_status": broker_status,
        "active_assets": len(MASTER_SNAPSHOT),
        "last_error": last_login_error,
        "time": time.ctime()
    }

@router.get("/api/price/{asset}")
async def get_price(asset: str):
    if asset in MASTER_SNAPSHOT:
        c = MASTER_SNAPSHOT[asset]
        return {
            "asset": asset, "price": c['close'], "timestamp": c['time'],
            "market_open": True, "status": "LIVE", "candle": c, "source": "harvester_engine"
        }
    
    # Check fallback
    fallback_file = RECENT_DIR / f"{asset}.json"
    if fallback_file.exists():
        try:
            with open(fallback_file, 'r') as f:
                data = json.load(f)
                if data:
                    return {"asset": asset, "status": "CACHED", "candle": data[-1], "source": "disk_cache"}
        except: pass
        
    return {"asset": asset, "status": "NOT_FOUND", "broker_status": broker_status}

@router.get("/api/snapshot")
async def get_snapshot():
    return {"total": len(MASTER_SNAPSHOT), "status": broker_status, "data": MASTER_SNAPSHOT}

@app.get("/")
async def dashboard():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read())

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    if not client: await websocket.send_json({"type": "info", "message": f"Broker: {broker_status}"})
    try:
        while True:
            # Stream all ticks from harvester engine to dashboard
            for asset, c in MASTER_SNAPSHOT.items():
                await websocket.send_json({"type": "tick", "asset": asset, "data": {"price": c['close'], "time": c['time']}})
            
            # Simple heartbeat/command check
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                data = json.loads(raw)
                if data["type"] == "switch" and client:
                    client.start_candles_stream(data["asset"], 60)
            except asyncio.TimeoutError:
                pass
    except: pass

app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"💎 LUX MASTER HARVESTER 3.0 LIVE ON PORT {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
