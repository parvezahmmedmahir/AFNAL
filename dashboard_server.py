import os
import json
import asyncio
import time
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials
from datetime import datetime, timedelta

app = FastAPI(title="PyQuotex Ultimate Real-Time 600-Candle Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Storage
client = None
last_error = "Not initialized"
# live_buffers[asset] = [ {time, open, high, low, close, ticks}, ... ] (exactly 600)
live_buffers = {}
is_collecting = False

async def get_client():
    global client, last_error
    if client is None:
        try:
            email, password = credentials()
            if not email or not password:
                last_error = "Missing QUOTEX_EMAIL or QUOTEX_PASSWORD"
                return None
            
            client = Quotex(email=email, password=password)
            try:
                check, reason = await client.connect()
                if not check:
                    last_error = f"Login Failed: {reason}"
                    return client if "pin" in str(reason).lower() else None
                last_error = "Connected"
            except Exception as e:
                last_error = f"Connection error: {str(e)}"
                client = None
        except Exception as e:
            last_error = f"Initialization error: {str(e)}"
            client = None
    return client

async def init_asset_buffer(q_client, asset):
    """Fetches initial 600 candles from history."""
    try:
        # Fetch 600 historical candles
        candles = await q_client.get_candles_v3(asset, 600, 60)
        if candles:
            live_buffers[asset] = candles
            # Subscribe to real-time stream
            q_client.start_candles_stream(asset, 60)
            return True
    except:
        return False

async def sync_live_prices():
    """Updates the 600th candle using real-time WebSocket data."""
    global client, live_buffers, is_collecting
    while True:
        try:
            q_client = await get_client()
            if q_client and last_error == "Connected":
                is_collecting = True
                
                # 1. Detect and Init New Assets
                instruments = await q_client.get_instruments()
                all_open = [i[1] for i in instruments if len(i) > 14 and i[14]]
                
                # Process in batches to initialize buffers if missing
                for asset in all_open:
                    if asset not in live_buffers:
                        await init_asset_buffer(q_client, asset)
                        await asyncio.sleep(0.1)

                # 2. Update buffers from WebSocket Tick Data
                for asset in list(live_buffers.keys()):
                    # Quotex lib stores real-time candles in api.realtime_candles[asset][period]
                    # We look for the 60-second period.
                    rt_candle_dict = q_client.api.realtime_candles.get(asset, {}).get(60)
                    if not rt_candle_dict:
                        continue
                    
                    # Convert dict to our candle format
                    # rt_candle_dict format: {'open':..., 'close':..., 'high':..., 'low':..., 'time':...}
                    rt_time = rt_candle_dict.get('time')
                    if not rt_time: continue
                    
                    buffer = live_buffers[asset]
                    last_buffered = buffer[-1]
                    
                    if rt_time == last_buffered['time']:
                        # Update the current running candle
                        buffer[-1].update({
                            'open': rt_candle_dict['open'],
                            'high': rt_candle_dict['high'],
                            'low': rt_candle_dict['low'],
                            'close': rt_candle_dict['close'],
                            'ticks': rt_candle_dict.get('ticks', last_buffered.get('ticks', 0) + 1)
                        })
                    elif rt_time > last_buffered['time']:
                        # New candle started! Push new, pop old.
                        new_candle = {
                            'time': rt_time,
                            'open': rt_candle_dict['open'],
                            'high': rt_candle_dict['high'],
                            'low': rt_candle_dict['low'],
                            'close': rt_candle_dict['close'],
                            'ticks': 1
                        }
                        buffer.append(new_candle)
                        if len(buffer) > 600:
                            buffer.pop(0)

                await asyncio.sleep(1) # High frequency sync
            else:
                is_collecting = False
                await asyncio.sleep(10)
        except Exception as e:
            print(f"Sync Error: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(sync_live_prices())

@app.get("/")
async def root():
    q_domain = "Unknown"
    if client and hasattr(client, 'api') and client.api:
        # Check login object for current domain
        from pyquotex.http.login import Login
        q_domain = getattr(Login, 'base_url', 'Checking...')

    return {
        "status": "online",
        "connection": last_error,
        "current_target": q_domain,
        "is_collecting": is_collecting,
        "total_assets": len(live_buffers),
        "endpoints": {
            "live_600": "/api/live/{asset}",
            "assets": "/api/assets",
            "verify_pin": "/api/verify?pin=XXXXXX"
        }
    }

@app.get("/api/live/{asset}")
async def get_live(asset: str):
    if asset in live_buffers:
        return live_buffers[asset]
    return {"error": "Asset not yet initialized or closed", "asset": asset}

@app.get("/api/assets")
async def get_assets():
    q_client = await get_client()
    if not q_client: return {"error": "Not connected", "reason": last_error}
    instruments = await q_client.get_instruments()
    return [{
        "symbol": i[1], 
        "name": i[2], 
        "open": bool(i[14]),
        "ready": i[1] in live_buffers
    } for i in instruments if len(i) > 14]

@app.get("/api/verify")
async def verify(pin: str):
    global client
    if not client: return {"error": "Init failed"}
    ok, msg = await client.send_pin(pin)
    return {"success": ok, "message": msg}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active = None
    async def loop():
        while True:
            if active and active in live_buffers:
                # Send the LIVE running candle (the 600th one)
                await websocket.send_json({"type": "live", "data": live_buffers[active][-1]})
            await asyncio.sleep(0.5)
    t = asyncio.create_task(loop())
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            if data["type"] == "switch": active = data["asset"]
    except: t.cancel()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
