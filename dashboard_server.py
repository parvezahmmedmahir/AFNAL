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
app = FastAPI(title="LUX Master Hub Pro", version="3.2.0")
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
    
    # Cooldown to avoid being banned
    if time.time() - last_login_attempt < 60:
        return None
        
    last_login_attempt = time.time()
    broker_status = "CONNECTING..."
    print("🚀 [MASTER] Initializing clean broker handshake...")
    
    try:
        email, password = credentials()
        # Always start with a fresh instance to clear "No response stored" errors
        cl = Quotex(email=email, password=password)
        
        check = False
        reason = "Unknown"
        for i in range(2): # 2 clear attempts
            print(f"   [Handshake] Attempt {i+1}...")
            try:
                check, reason = await cl.connect()
                if check: break
            except Exception as inner_e:
                reason = str(inner_e)
            await asyncio.sleep(10)

        if not check:
            broker_status = f"FAILED: {reason}"
            print(f"❌ [MASTER] Broker Connection Failed: {reason}")
            return None
            
        print("✅ [MASTER] Broker Connection Secure!")
        broker_status = "CONNECTED"
        client = cl
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
        print(f"🔍 [MASTER] Scanning {len(instr)} markets for collective harvesting...")
        count = 0
        for i in instr:
            if len(i) > 14 and i[14]: 
                cl.start_candles_stream(i[1], 60)
                count += 1
                if count % 15 == 0: await asyncio.sleep(2) # Slower throttle for stability
        print(f"🚀 [MASTER] Harvesting {count} assets in parallel.")
    except Exception as e:
        print(f"⚠️ [MASTER] Broad Subscribe Error: {e}")

async def live_harvester_loop():
    """Real-time tick engine with Supabase and Disk mirroring"""
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
                    cl.api.realtime_price[asset] = []
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
                    
                    # --- SUPABASE PUSH ---
                    save_candle_realtime(asset, MASTER_SNAPSHOT[asset])
            
            # Write periodic snapshot for REST API Fallback
            if int(time.time()) % 3 == 0:
                with open(DATA_DIR / "live_snapshot.json", "w") as f:
                    json.dump(MASTER_SNAPSHOT, f)
                    
        except Exception: pass
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def start_engines():
    asyncio.create_task(live_harvester_loop())

# --- REST API ENDPOINTS ---

@router.get("/health")
async def health():
    return {"status": broker_status, "assets_tracking": len(MASTER_SNAPSHOT)}

@router.get("/api/assets")
async def get_assets():
    """REST: Get all assets from disk cache or memory"""
    assets = []
    if RECENT_DIR.exists():
        for file in RECENT_DIR.glob("*.json"):
            assets.append({"symbol": file.stem, "active": True})
    
    # Also add from memory if disk is empty
    for asset in MASTER_SNAPSHOT.keys():
        if not any(a['symbol'] == asset for a in assets):
            assets.append({"symbol": asset, "active": True})
            
    return {"total": len(assets), "assets": sorted(assets, key=lambda x: x['symbol'])}

@router.get("/api/snapshot")
async def get_snapshot():
    """REST: Full collective snapshot"""
    return {"total": len(MASTER_SNAPSHOT), "status": broker_status, "data": MASTER_SNAPSHOT}

@router.get("/api/price/{asset}")
async def get_price(asset: str):
    """REST: Single asset price with fallback mechanism"""
    if asset in MASTER_SNAPSHOT:
        c = MASTER_SNAPSHOT[asset]
        return {
            "asset": asset, "price": c['close'], "timestamp": c['time'],
            "market_open": True, "status": "LIVE", "candle": c, "source": "memory_engine"
        }
    
    # Disk Fallback
    try:
        f = RECENT_DIR / f"{asset}.json"
        if f.exists():
            with open(f, 'r') as j:
                d = json.load(j)
                if d: return {"asset": asset, "status": "CACHED", "candle": d[-1], "source": "disk_cache"}
    except: pass

    return {"asset": asset, "status": "PENDING", "broker_status": broker_status}

@app.get("/")
async def ui():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read())

@app.websocket("/ws")
async def ws_handler(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            for asset, c in MASTER_SNAPSHOT.items():
                await websocket.send_json({"type": "tick", "asset": asset, "data": {"price": c['close'], "time": c['time']}})
            await asyncio.sleep(1)
            try: await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except: pass
    except: pass

app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
