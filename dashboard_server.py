import asyncio
import json
import time
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials, load_session
from datetime import datetime

from pathlib import Path

app = FastAPI()

# Data directories
DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"

# Global Quotex client
client = None

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

@app.get("/")
async def get():
    return HTMLResponse(content=open("index.html", encoding="utf-8").read(), status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] WebSocket accepted and opened.")
    await websocket.send_json({"type": "hello", "message": "Connection established"})
    
    print("[WS] Initializing/Getting Quotex client...")
    client = await get_client()
    
    if client is None:
        print("[WS] Client initialization failed!")
        await websocket.send_json({"type": "error", "message": "Failed to connect to Quotex"})
        await websocket.close()
        return
    print("[WS] Client initialized successfully.")

    active_asset = None
    active_period = 60
    subscribe_all = False
    
    async def get_formatted_assets():
        raw = await client.get_instruments()
        formatted = []
        for i in raw:
            try:
                # i[1] symbol, i[2] name, i[14] is_open
                if len(i) > 14:
                    # Filter: Prioritize OTC if requested, but for now send all
                    formatted.append({
                        "id": i[0], 
                        "symbol": i[1], 
                        "name": i[2],
                        "open": bool(i[14])
                    })
            except Exception:
                continue
        return formatted

    # Send initial list
    asset_list = await get_formatted_assets()
    
    print(f"[WS] Sending {len(asset_list)} assets to client.")
    await websocket.send_json({"type": "assets", "data": asset_list})

    async def market_monitor():
        nonlocal subscribe_all
        while True:
            try:
                await asyncio.sleep(20) # Pulse every 20s
                print("[WS] Refreshing market status...")
                updated_assets = await get_formatted_assets()
                await websocket.send_json({"type": "assets", "data": updated_assets})
                
                # If in Subscribe-All mode, ensure we are subscribed to newly opened assets
                if subscribe_all:
                    for asset in updated_assets:
                        if asset['open']:
                            # start_candles_stream is idempotent (won't hurt if already started)
                            client.start_candles_stream(asset['symbol'], 60)
            except Exception as e:
                print(f"[WS] Market Monitor Info: {e}")

    monitor_task = asyncio.create_task(market_monitor())
    
    async def tick_relay():
        nonlocal active_asset, active_period, subscribe_all
        try:
            while True:
                # Mode 1: Global Subscription (Streams ALL OPEN assets)
                if subscribe_all:
                    # Iterate over everything in the realtime buffer
                    # We accept a race condition here where data might be popped by another task, 
                    # but since we are the only consumer of this client instance in this context, it's okay.
                    # Note: Ideally we should use the harvester engine structure, but accessing api.realtime_price directly works.
                    
                    # Snapshot keys to avoid runtime change error
                    current_assets = list(client.api.realtime_price.keys())
                    for asset in current_assets:
                        ticks = client.api.realtime_price.get(asset, [])
                        if ticks:
                            client.api.realtime_price[asset] = [] # Clear buffer
                            for tick in ticks:
                                await websocket.send_json({
                                    "type": "tick",
                                    "asset": asset, # Include asset name
                                    "data": {
                                        "time": tick['time'],
                                        "price": tick['price']
                                    }
                                })
                
                # Mode 2: Single Asset (Legacy Dashboard)
                elif active_asset:
                    ticks = client.api.realtime_price.get(active_asset, [])
                    if ticks:
                        client.api.realtime_price[active_asset] = []
                        for tick in ticks:
                            await websocket.send_json({
                                "type": "tick",
                                "asset": active_asset,
                                "data": {
                                    "time": tick['time'],
                                    "price": tick['price']
                                }
                            })
                await asyncio.sleep(0.05) # Faster polling for multi-asset
        except Exception as e:
            print(f"[WS-Relay] Error: {e}")

    relay_task = asyncio.create_task(tick_relay())

    try:
        while True:
            raw_data = await websocket.receive_text()
            print(f"[WS] Received: {raw_data[:100]}...")
            try:
                data = json.loads(raw_data)
                
                # NEW: Subscribe All Command
                if data["type"] == "subscribe_all":
                    print("[WS] Enabling Global Subscription Mode (ALL ASSETS)")
                    subscribe_all = True
                    # Auto-subscribe to all streaming on the backend
                    # This requires the client to really be listening to everything.
                    # We rely on the otc_harvester or master mechanism to keep streams open,
                    # OR we force open them here.
                    instruments = await client.get_instruments()
                    for i in instruments:
                        if i[14]: # If open
                           client.start_candles_stream(i[1], 60)
                    print("[WS] Subscribed to all open streams.")
                
                elif data["type"] == "switch":
                    subscribe_all = False # Disable global if switching to single
                    new_asset = data["asset"]
                    new_period = int(data["period"])
                    print(f"[WS] Switching to {new_asset} ({new_period}s)...")
                    
                    # Force update status of this asset specifically
                    # In a full system we'd check if it's open first
                    
                    if active_asset:
                        client.stop_candles_stream(active_asset)
                    
                    active_asset = new_asset
                    active_period = new_period
                    
                    print(f"[WS] Fetching history for {active_asset}...")
                    try:
                        # Fetch 600 candles as requested by USER
                        history = await client.get_candles_v3(active_asset, 600, active_period)
                        
                        # Fallback: If broker gives nothing, check our own recent data
                        if not history:
                            local_file = RECENT_DIR / f"{active_asset}.json"
                            if local_file.exists():
                                print(f"[WS] Broker history empty. Falling back to {local_file}")
                                with open(local_file, "r") as f:
                                    history = json.load(f)
                    except Exception as he:
                        print(f"[WS] Failed to fetch history: {he}")
                        history = []

                    print(f"[WS] History fetched: {len(history)} candles.")
                    
                    if history:
                        print(f"[WS] Sample candle: {history[0]}")
                        print(f"[WS] Last candle: {history[-1]}")
                    else:
                        print(f"[WS] WARNING: No history data for {active_asset}")
                    
                    client.start_candles_stream(active_asset, active_period)
                    
                    await websocket.send_json({
                        "type": "history",
                        "asset": active_asset,
                        "data": history
                    })
                    print(f"[WS] Sent history for {active_asset}.")
            except Exception as process_error:
                print(f"[WS] Error processing message: {process_error}")
                
    except (WebSocketDisconnect, ConnectionClosed):
        print("[WS] Client disconnected.")
        relay_task.cancel()
        monitor_task.cancel() # Cancel monitor too
        if active_asset:
            client.stop_candles_stream(active_asset)
    except Exception as e:
        print(f"[WS] Loop Exception: {e}")
        relay_task.cancel()
        monitor_task.cancel()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
