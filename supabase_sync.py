import os
import json
import time
import asyncio
from pathlib import Path
from supabase_db import save_candles, cleanup_old_data, init_db

DATA_DIR = Path(__file__).parent / "data"
RECENT_DIR = DATA_DIR / "recent"

async def sync_task():
    print("🚀 Starting Supabase Sync Engine...")
    init_db()
    
    while True:
        try:
            total_synced = 0
            if RECENT_DIR.exists():
                for file in RECENT_DIR.glob("*.json"):
                    asset = file.stem
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                            if not data: continue
                            
                            # Prepare for batch insert
                            to_save = []
                            for c in data:
                                to_save.append((
                                    asset,
                                    c['time'],
                                    c['open'],
                                    c['high'],
                                    c['low'],
                                    c['close']
                                ))
                            
                            if to_save:
                                save_candles(to_save)
                                total_synced += len(to_save)
                    except: continue
                    
            print(f"✅ Synced {total_synced} candles to Supabase. Next sync in 10 minutes.")
            
            # 30-day sliding window cleanup
            cleanup_old_data(days=30)
            
            await asyncio.sleep(600) # Sync every 10 minutes
            
        except Exception as e:
            print(f"⚠️ Sync Loop Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(sync_task())
