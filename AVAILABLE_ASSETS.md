# 🎯 Your API - Available Assets

## How It Works

**Anyone can access any asset by just changing the name in the URL!**

### Example:
```
http://127.0.0.1:8001/api/price/BTCUSD_otc
http://127.0.0.1:8001/api/price/EURUSD_otc
http://127.0.0.1:8001/api/price/BRLUSD_otc
```

Just replace `BTCUSD_otc` with any asset from the list below!

---

## 📊 Currently Available Assets (50+)

### 💰 Cryptocurrencies
- `BTCUSD_otc` - Bitcoin
- `ETHUSD_otc` - Ethereum
- `BCHUSD_otc` - Bitcoin Cash
- `LTCUSD_otc` - Litecoin
- `BNBUSD_otc` - Binance Coin
- `ADAUSD_otc` - Cardano
- `DOGUSD_otc` - Dogecoin
- `ETCUSD_otc` - Ethereum Classic
- `AVAUSD_otc` - Avalanche
- `AXSUSD_otc` - Axie Infinity
- `DASUSD_otc` - Dash
- `LINUSD_otc` - Chainlink
- `MANUSD_otc` - Decentraland
- `BEAUSD_otc` - Beam
- `BONUSD_otc` - Bonk
- `FLOUSD_otc` - Flow
- `HMSUSD_otc` - Humanscape
- `MELUSD_otc` - Melon

### 💱 Forex (Major Pairs)
- `EURUSD_otc` - Euro / US Dollar
- `GBPUSD_otc` - British Pound / US Dollar
- `AUDUSD_otc` - Australian Dollar / US Dollar
- `USDJPY_otc` - US Dollar / Japanese Yen (if available)
- `BRLUSD_otc` - Brazilian Real / US Dollar

### 💱 Forex (Cross Pairs)
- `EURAUD_otc` - Euro / Australian Dollar
- `EURCHF_otc` - Euro / Swiss Franc
- `EURGBP_otc` - Euro / British Pound
- `EURJPY_otc` - Euro / Japanese Yen
- `EURNZD_otc` - Euro / New Zealand Dollar
- `EURSGD_otc` - Euro / Singapore Dollar
- `GBPAUD_otc` - British Pound / Australian Dollar
- `GBPCAD_otc` - British Pound / Canadian Dollar
- `GBPCHF_otc` - British Pound / Swiss Franc
- `GBPJPY_otc` - British Pound / Japanese Yen
- `GBPNZD_otc` - British Pound / New Zealand Dollar
- `AUDCAD_otc` - Australian Dollar / Canadian Dollar
- `AUDCHF_otc` - Australian Dollar / Swiss Franc
- `AUDJPY_otc` - Australian Dollar / Japanese Yen
- `AUDNZD_otc` - Australian Dollar / New Zealand Dollar
- `CADCHF_otc` - Canadian Dollar / Swiss Franc
- `CADJPY_otc` - Canadian Dollar / Japanese Yen
- `CHFJPY_otc` - Swiss Franc / Japanese Yen
- `NZDCAD_otc` - New Zealand Dollar / Canadian Dollar

### 📈 Stocks
- `AXP_otc` - American Express
- `BA_otc` - Boeing
- `FB_otc` - Meta (Facebook)
- `INTC_otc` - Intel
- `JNJ_otc` - Johnson & Johnson
- `MCD_otc` - McDonald's
- `MSFT_otc` - Microsoft

### 🌟 Other Assets
- `ARBUSD_otc` - Arbitrum
- `ATOUSD_otc` - Cosmos

---

## 🚀 Quick Examples

### Get Bitcoin Price
```
http://127.0.0.1:8001/api/price/BTCUSD_otc
```

### Get EUR/USD Price
```
http://127.0.0.1:8001/api/price/EURUSD_otc
```

### Get Brazilian Real Price
```
http://127.0.0.1:8001/api/price/BRLUSD_otc
```

### Get Recent Candles (for charts)
```
http://127.0.0.1:8001/api/recent/BTCUSD_otc?limit=100
```

### Get All Available Assets
```
http://127.0.0.1:8001/api/assets
```

---

## 💡 Note About USDBRL

You asked about `USDBRL_otc` - this is the **inverse** of `BRLUSD_otc`.

- ✅ **Available**: `BRLUSD_otc` (Brazilian Real to USD)
- ❌ **Not tracked**: `USDBRL_otc` (USD to Brazilian Real)

**To get USD/BRL rate**: Simply use `1 / BRLUSD_price`

Example:
```javascript
fetch('http://127.0.0.1:8001/api/price/BRLUSD_otc')
  .then(r => r.json())
  .then(data => {
    const brlToUsd = data.price;
    const usdToBrl = 1 / brlToUsd;
    console.log(`USD/BRL: ${usdToBrl.toFixed(4)}`);
  });
```

---

## 🎨 Interactive Demo

Open `api_demo.html` in your browser to see a **live demo** with:
- ✅ Real-time price updates
- ✅ Interactive candlestick charts
- ✅ Click-to-load different assets
- ✅ Code examples

Just double-click `api_demo.html` or open it in any browser!

---

## 🌐 How Anyone Can Use Your API

### For Developers:

**JavaScript:**
```javascript
// Change 'BTCUSD_otc' to any asset!
fetch('http://127.0.0.1:8001/api/price/BTCUSD_otc')
  .then(r => r.json())
  .then(data => console.log(data));
```

**Python:**
```python
import requests

# Change 'EURUSD_otc' to any asset!
r = requests.get('http://127.0.0.1:8001/api/price/EURUSD_otc')
print(r.json())
```

**cURL:**
```bash
# Change 'BRLUSD_otc' to any asset!
curl http://127.0.0.1:8001/api/price/BRLUSD_otc
```

---

## ✅ Your API is Production-Ready!

Anyone can:
1. **Change the asset name** in the URL
2. **Get live data** instantly
3. **Build charts** using the candle data
4. **Create trading bots** with the API
5. **Access from any programming language**

**It works exactly like professional APIs (Binance, Coinbase, etc.)!**

---

## 📖 Full Documentation

- **API Usage Guide**: `API_USAGE_GUIDE.md`
- **Data Collection**: `DATA_COLLECTION_GUIDE.md`
- **Complete Overview**: `README_YOUR_API.md`
- **Interactive Docs**: http://127.0.0.1:8001/docs
