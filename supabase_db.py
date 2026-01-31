import psycopg2
from psycopg2 import sql
import os

DB_URL = "postgresql://postgres.glpbrxqonrplrpmvityq:MahirANAS1122@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"

def init_db():
    print("🚀 Initializing Supabase Storage...")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Create candles table
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
        
        # Index for faster lookup by time
        cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_time ON candles(time);")
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Supabase Table 'candles' is ready.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")

def save_candles(candles_list):
    """
    Saves a list of candles to Supabase.
    Each item: (asset, time, open, high, low, close)
    """
    if not candles_list:
        return
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO candles (asset, time, open, high, low, close)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (asset, time) DO NOTHING;
        """
        
        cur.executemany(insert_query, candles_list)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Supabase Save Error: {e}")

def cleanup_old_data(days=30):
    """Deletes data older than X days to maintain sliding window"""
    try:
        cutoff = int(time.time()) - (days * 24 * 60 * 60)
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM candles WHERE time < %s;", (cutoff,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"🧹 Cleaned up data older than {days} days.")
    except Exception as e:
        print(f"⚠️ Cleanup Error: {e}")

if __name__ == "__main__":
    init_db()
