import psycopg2
from psycopg2 import sql
import os
import time

DB_URL = "postgresql://postgres.glpbrxqonrplrpmvityq:MahirANAS1122@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"

def init_db():
    print("🚀 Initializing Supabase Storage...")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                asset TEXT,
                time BIGINT,
                open NUMERIC,
                high NUMERIC,
                low NUMERIC,
                close NUMERIC,
                PRIMARY KEY (asset, time)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_time ON candles(time);")
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Supabase Table 'candles' is ready.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")

def save_candles(candles_list):
    """Bulk save for efficiency"""
    if not candles_list: return
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        query = "INSERT INTO candles (asset, time, open, high, low, close) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (asset, time) DO NOTHING;"
        cur.executemany(query, candles_list)
        conn.commit()
        cur.close()
        conn.close()
    except: pass

def save_candle_realtime(asset, candle):
    """Upserts a single candle to Supabase in real-time (with update logic)"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        query = """
            INSERT INTO candles (asset, time, open, high, low, close)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (asset, time) 
            DO UPDATE SET high = GREATEST(candles.high, EXCLUDED.high), low = LEAST(candles.low, EXCLUDED.low), close = EXCLUDED.close;
        """
        cur.execute(query, (asset, candle['time'], candle['open'], candle['high'], candle['low'], candle['close']))
        conn.commit()
        cur.close()
        conn.close()
    except: pass

def cleanup_old_data(days=30):
    try:
        cutoff = int(time.time()) - (days * 24 * 60 * 60)
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM candles WHERE time < %s;", (cutoff,))
        conn.commit()
        cur.close()
        conn.close()
    except: pass

if __name__ == "__main__":
    init_db()
