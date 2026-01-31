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
from pyquotex.config import credentials, load_session
from supabase_db import save_candle_realtime

# --- CONFIGURATION ---
app = FastAPI(title="LUX Master Hub Pro", version="3.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"
RECENT_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/lux")

# --- GLOBAL STATE ENGINE ---
MASTER_SNAPSHOT: Dict[str, dict] = {}
client = None
broker_status = "DISCONNECTED"
last_login_attempt = 0

async def get_client():
    global client, broker_status, last_login_attempt
    if client is not None:
        return client
    
    # Anti-spam cooldown (60 seconds for safety on Render)
    if time.time() - last_login_attempt < 60:
        return None
        
    last_login_attempt = time.time()
    broker_status = "CONNECTING..."
    print("🚀 [MASTER] Attempting secure broker connection...")
    
    try:
        email, password = credentials()
        # Try to use existing session if available
        cl = Quotex(email=email, password=password)
        
        # Robust connect with retry
        check = False
        reason = "Unknown"
        for i in range(3):
            print(f"   [Try {i+1}] Connecting to Quotex...")
            check, reason = await cl.connect()
            if check: break
            await asyncio.sleep(5)

        if not check:
            broker_status = f"FAILED: {reason}"
            print(f"❌ [MASTER] Broker Connection Failed: {reason}")
            return None
            
        print("✅ [MASTER] Broker Connection Established!")
        broker_status = "CONNECTED"
        client = cl
        
        # Immediate Broad Subscription
        asyncio.create_task(broad_subscribe_task(cl))
        return cl
        
    except Exception as e:
        broker_status = f"CRITICAL: {str(e)}"
        print(f"❌ [MASTER] Critical Error: {e}")
        return None

async def broad_subscribe_task(cl):
    """Subscribes to all assets to populate the memory engine"""
    try:
        instr = await cl.get_instruments()
        print(f"🔍 [MASTER] Scanning {len(instr)} markets...")
        count = 0
        for i in instr:
            if len(i) > 14 and i[14]: # If market is open
                cl.start_candles_stream(i[1], 60)
                count += 1
                if count % 10 == 0: await asyncio.sleep(1) # Safety throttle
        print(f"🚀 [MASTER] System is harvesting {count} assets LIVE.")
    except Exception as e:
        print(f"⚠️ [MASTER] Broad Subscribe Error: {e}")

async def live_harvester_loop():
    """Real-time tick-to-memory and tick-to-supabase engine"""
    while True:
        cl = await get_client()
        if not cl:
            await asyncio.sleep(5)
            continue
            
        try:
            current_assets = list(cl.api.realtime_price.keys())
            for asset in current_assets:
                ticks = cl.api.realtime_price.get(asset, [])
                if ticks:
                    cl.api.realtime_price[asset] = [] # Clear buffer
                    last = ticks[-1]
                    
                    price = last['price']
                    ts = last['time']
                    candle_time = (ts // 60) * 60
                    
                    # Update Memory
                    if asset not in MASTER_SNAPSHOT or MASTER_SNAPSHOT[asset]['time'] != candle_time:
                        MASTER_SNAPSHOT[asset] = {
                            "time": candle_time, "open": price, "high": price, "low": price, "close": price
                        }
                    else:
                        c = MASTER_SNAPSHOT[asset]
                        c['close'] = price
                        c['high'] = max(c['high'], price)
                        c['low'] = min(c['low'], price)
                    
                    # --- SUPABASE MILLISECOND SYNC ---
                    save_candle_realtime(asset, MASTER_SNAPSHOT[asset])
            
            # Write periodic snapshot for REST API
            if int(time.time()) % 2 == 0:
                with open(DATA_DIR / "live_snapshot.json", "w") as f:
                    json.dump(MASTER_SNAPSHOT, f)
                    
        except Exception:
            pass
            
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def start_engines():
    asyncio.create_task(live_harvester_loop())

# --- API ENDPOINTS ---

@router.get("/health")
async def health():
    return {"status": broker_status, "assets_tracking": len(MASTER_SNAPSHOT), "time": time.ctime()}

@router.get("/api/snapshot")
async def get_snapshot():
    return {
        "total": len(MASTER_SNAPSHOT),
        "status": broker_status,
        "data": MASTER_SNAPSHOT
    }

@router.get("/api/price/{asset}")
async def get_price(asset: str):
    if asset in MASTER_SNAPSHOT:
        c = MASTER_SNAPSHOT[asset]
        return {
            "asset": asset, "price": c['close'], "timestamp": c['time'],
            "market_open": True, "status": "LIVE", "candle": c, "source": "live_streaming"
        }
    return {"asset": asset, "status": "PENDING", "broker_status": broker_status}

@app.get("/")
async def ui():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read())

@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Relay ticks for everything in memory
            for asset, c in MASTER_SNAPSHOT.items():
                await websocket.send_json({"type": "tick", "asset": asset, "data": {"price": c['close'], "time": c['time']}})
            await asyncio.sleep(1)
            # Receive ping to keep alive
            try: await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except: pass
    except: pass

app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
