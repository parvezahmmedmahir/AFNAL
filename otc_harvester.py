import asyncio
import json
import time
from pyquotex.stable_api import Quotex
from pyquotex.config import credentials

async def run_otc_harvester():
    print("🚀 Initializing OTC Data Harvester Engine...")
    
    # 1. Login
    email, password = credentials()
    client = Quotex(email=email, password=password)
    check, reason = await client.connect()
    
    if not check:
        print(f"❌ Connection Failed: {reason}")
        return

    print("✅ Connected to Quotex Broker.")
    
    # Track state
    known_open_assets = set()
    
    while True:
        try:
            print("\n🔍 Scanning Market Status...")
            instruments = await client.get_instruments()
            
            broker_assets = [
                {'symbol': i[1], 'name': i[2], 'open': bool(i[14])} 
                for i in instruments 
            ]
            with open("harvester_debug.txt", "a") as f:
                f.write(f"[{time.ctime()}] Discovered {len(broker_assets)} assets\n")
                if len(broker_assets) > 0:
                    f.write(f"Sample: {broker_assets[0]['symbol']}\n")
                f.write(f"Is AUDCAD present? {any(a['symbol'] == 'AUDCAD' for a in broker_assets)}\n")
            
            print(f"   [Harvester] Discovered {len(broker_assets)} assets. sample: {broker_assets[0]['symbol'] if broker_assets else 'None'}", flush=True)
            
            # Check for a specific regular one
            found_audcad = any(a['symbol'] == 'AUDCAD' for a in broker_assets)
            if not found_audcad:
                print("   [Harvester] WARNING: AUDCAD not found in instruments list!", flush=True)
            else:
                print("   [Harvester] OK: AUDCAD found.", flush=True)
            
            current_open = {a['symbol'] for a in broker_assets if a['open']}
            current_closed = {a['symbol'] for a in broker_assets if not a['open']}
            
            # Save market status to file for API
            import os
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(data_dir, exist_ok=True)
            status_file = os.path.join(data_dir, 'market_status.json')
            
            market_status = {}
            for asset_info in broker_assets:
                market_status[asset_info['symbol']] = {
                    'name': asset_info['name'],
                    'open': asset_info['open'],
                    'last_checked': time.time()
                }
            
            with open(status_file, 'w') as f:
                json.dump(market_status, f)
            
            # Detect Changes
            newly_opened = current_open - known_open_assets
            newly_closed = known_open_assets - current_open
            
            # Handle Closed Markets
            for asset in newly_closed:
                print(f"🔴 MARKET CLOSED: {asset}. Stopping data collection.")
                client.stop_candles_stream(asset)
                known_open_assets.remove(asset)
                
            # Handle Opened Markets
            for asset in newly_opened:
                print(f"🟢 MARKET OPENED: {asset}. Auto-subscribing for live data...")
                # Subscribe to 1M candles
                client.start_candles_stream(asset, 60)
                known_open_assets.add(asset)
            
            print(f"📊 Tracking {len(known_open_assets)} Active Broker Assets.", flush=True)
            
            # Process Live Data for ALL tracked assets
            # In a real engine, you would dump this to a DB
            if known_open_assets:
                sample_asset = list(known_open_assets)[0]
                price_data = client.api.realtime_price.get(sample_asset)
                if price_data:
                    print(f"   ⚡ Data Flowing... (Sample: {sample_asset} @ {price_data[-1]['price']})")
                else:
                    print("   ⏳ Waiting for first ticks...")
            
            await asyncio.sleep(10) # Scan every 10 seconds
            
        except Exception as e:
            print(f"⚠️ Error in loop: {e}")
            await asyncio.sleep(5)
            # Reconnect logic could go here

if __name__ == "__main__":
    asyncio.run(run_otc_harvester())
