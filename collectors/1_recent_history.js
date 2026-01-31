const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuration
const WS_URL = process.env.WS_URL || "ws://127.0.0.1:8000/ws";
console.log(`📡 Connecting to server at: ${WS_URL}`);
const DATA_DIR = path.join(__dirname, '../data/recent');
const MAX_CANDLES = 600;
const TIMEFRAME = 60; // 1 minute

// Ensure directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// In-memory store: { "EURUSD": [ {time, open, high, low, close}, ... ] }
let marketData = {};

function connect() {
    const ws = new WebSocket(WS_URL);

    ws.on('open', () => {
        console.log("✅ [Recent] Connected to WebSocket");
        // Trigger broad subscription
        ws.send(JSON.stringify({ type: 'subscribe_all' }));
    });

    ws.on('message', (data) => {
        try {
            const msg = JSON.parse(data);

            if (msg.type === 'tick') {
                handleTick(msg.asset, msg.data);
            }
        } catch (e) {
            console.error("Parse Error:", e);
        }
    });

    ws.on('close', () => {
        console.log("❌ [Recent] Disconnected. Reconnecting in 5s...");
        setTimeout(connect, 5000);
    });

    ws.on('error', (err) => {
        console.error("❌ [Recent] Error:", err.message);
    });
}

function handleTick(asset, tick) {
    if (!asset) return;

    if (!marketData[asset]) {
        marketData[asset] = [];
    }

    const price = tick.price;
    const time = tick.time;
    // Calculate candle start time (e.g., round down to nearest minute)
    const candleTime = Math.floor(time / TIMEFRAME) * TIMEFRAME;

    let candles = marketData[asset];
    let lastCandle = candles[candles.length - 1];

    if (lastCandle && lastCandle.time === candleTime) {
        // Update existing candle
        lastCandle.close = price;
        lastCandle.high = Math.max(lastCandle.high, price);
        lastCandle.low = Math.min(lastCandle.low, price);
    } else {
        // Create new candle
        const newCandle = {
            time: candleTime,
            open: price,
            high: price,
            low: price,
            close: price
        };
        candles.push(newCandle);

        // Keep only last 600
        if (candles.length > MAX_CANDLES) {
            candles.shift();
        }
    }

    // Debounced Save (Optional: Save every update is too heavy, maybe save periodically)
}

// Periodic Save Routine (Every 10 seconds) - Full History
setInterval(() => {
    const assets = Object.keys(marketData);
    if (assets.length === 0) return;

    console.log(`💾 [Recent] Saving full data for ${assets.length} assets...`);

    assets.forEach(asset => {
        const filePath = path.join(DATA_DIR, `${asset}.json`);
        const candles = marketData[asset];
        if (candles && candles.length > 0) {
            fs.writeFile(filePath, JSON.stringify(candles), (err) => {
                if (err) console.error(`Failed to save ${asset}:`, err);
            });
        }
    });
}, 10000);

// NEW: Real-time Snapshot (Every 2 seconds) - Single latest candle
setInterval(() => {
    const assets = Object.keys(marketData);
    if (assets.length === 0) return;

    const snapshot = {};
    assets.forEach(asset => {
        const candles = marketData[asset];
        if (candles && candles.length > 0) {
            snapshot[asset] = candles[candles.length - 1];
        }
    });

    const snapshotPath = path.join(DATA_DIR, '../live_snapshot.json');
    const tempPath = snapshotPath + '.tmp';

    try {
        fs.writeFileSync(tempPath, JSON.stringify(snapshot));
        fs.renameSync(tempPath, snapshotPath);
    } catch (err) {
        console.error("Failed to save live snapshot:", err);
    }
}, 2000);

connect();
