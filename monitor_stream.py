import asyncio
import websockets
import json
import time

async def monitor():
    uri = "ws://127.0.0.1:8000/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Server. Waiting for asset list...")
            
            assets_received = False
            open_assets = []
            
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                
                if data['type'] == 'assets':
                    all_assets = data['data']
                    open_assets = [a['symbol'] for a in all_assets if a.get('open')]
                    print(f"✅ Received Asset List: {len(all_assets)} total, {len(open_assets)} OPEN.")
                    if not open_assets:
                        print("❌ No open assets found!")
                        return
                    
                    # Start Testing Loop
                    print(f"🚀 Starting Test of {len(open_assets)} Open Assets...")
                    
                    for i, asset in enumerate(open_assets):
                        print(f"\n[{i+1}/{len(open_assets)}] testing {asset}...")
                        await websocket.send(json.dumps({'type': 'switch', 'asset': asset, 'period': 60}))
                        
                        # Wait for confirmation of data flow (History + at least 1 tick)
                        history_received = False
                        tick_received = False
                        start_time = time.time()
                        
                        while time.time() - start_time < 5: # 5 second timeout per asset
                            try:
                                msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                                data = json.loads(msg)
                                
                                if data['type'] == 'history':
                                    history_received = True
                                    print(f"   📄 History: {len(data['data'])} candles")
                                elif data['type'] == 'tick':
                                    tick_received = True
                                    t = data['data']
                                    print(f"   ⚡ Tick: {t['price']}")
                                    
                                if history_received and tick_received:
                                    print(f"   ✅ {asset} VERIFIED")
                                    break
                            except asyncio.TimeoutError:
                                continue
                                
                        if not (history_received and tick_received):
                            print(f"   ⚠️  {asset} warning: Data incomplete (History: {history_received}, Tick: {tick_received})")
                            
                    print("\n\n🎉 ALL ASSETS TESTED.")
                    return

    except Exception as e:
         print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(monitor())
