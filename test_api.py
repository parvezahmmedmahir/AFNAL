import requests
import json

API_URL = "http://127.0.0.1:8001"

print("=" * 60)
print("  OTC Market Data API - Live Test")
print("=" * 60)
print()

# Test 1: Get all assets
print("📋 Test 1: Get All Assets")
print("-" * 60)
try:
    response = requests.get(f"{API_URL}/api/assets")
    data = response.json()
    print(f"✅ Total assets available: {data['total']}")
    print(f"✅ Sample assets: {[a['symbol'] for a in data['assets'][:5]]}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 2: Get latest BTC price
print("💰 Test 2: Get Latest BTC Price")
print("-" * 60)
try:
    response = requests.get(f"{API_URL}/api/price/BTCUSD_otc")
    data = response.json()
    print(f"✅ Asset: {data['asset']}")
    print(f"✅ Price: ${data['price']:,.2f}")
    print(f"✅ Timestamp: {data['timestamp']}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 3: Get recent candles
print("📊 Test 3: Get Recent Candles (Last 5)")
print("-" * 60)
try:
    response = requests.get(f"{API_URL}/api/recent/BTCUSD_otc?limit=5")
    data = response.json()
    print(f"✅ Asset: {data['asset']}")
    print(f"✅ Timeframe: {data['timeframe']}")
    print(f"✅ Candles received: {data['count']}")
    print()
    print("  Candle Data:")
    for i, candle in enumerate(data['candles'], 1):
        print(f"    {i}. Time: {candle['time']} | O: {candle['open']} | H: {candle['high']} | L: {candle['low']} | C: {candle['close']}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 4: Get OHLC
print("📈 Test 4: Get OHLC (Last 10 candles)")
print("-" * 60)
try:
    response = requests.get(f"{API_URL}/api/ohlc/EURUSD_otc?period=10")
    data = response.json()
    ohlc = data['ohlc']
    print(f"✅ Asset: {data['asset']}")
    print(f"✅ Period: {data['period']} candles")
    print(f"✅ Open: {ohlc['open']}")
    print(f"✅ High: {ohlc['high']}")
    print(f"✅ Low: {ohlc['low']}")
    print(f"✅ Close: {ohlc['close']}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 5: Health check
print("🏥 Test 5: Health Check")
print("-" * 60)
try:
    response = requests.get(f"{API_URL}/api/health")
    data = response.json()
    print(f"✅ Status: {data['status']}")
    print(f"✅ Data directories:")
    for dir_name, exists in data['data_directories'].items():
        status = "✅" if exists else "❌"
        print(f"    {status} {dir_name}: {'Available' if exists else 'Missing'}")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
print("  All API Tests Complete!")
print("=" * 60)
print()
print("🌐 Interactive API Docs: http://127.0.0.1:8001/docs")
print("📖 Usage Guide: API_USAGE_GUIDE.md")
