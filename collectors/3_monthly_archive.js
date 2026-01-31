const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuration
const WS_URL = process.env.WS_URL || "ws://127.0.0.1:8000/ws";
console.log(`📡 [Monthly] Connecting to server at: ${WS_URL}`);
const DATA_DIR = path.join(__dirname, '../data/monthly');
const TIMEFRAME = 60; // 1 minute

// Ensure directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

let buffer = {};

function connect() {
    const ws = new WebSocket(WS_URL);

    ws.on('open', () => {
        console.log("✅ [Monthly] Connected to WebSocket");
        ws.send(JSON.stringify({ type: 'subscribe_all' }));
    });

    ws.on('message', (data) => {
        try {
            const msg = JSON.parse(data);
            if (msg.type === 'tick') {
                processTick(msg.asset, msg.data);
            }
        } catch (e) { }
    });

    ws.on('close', () => {
        console.log("❌ [Monthly] Disconnected. Reconnecting...");
        setTimeout(connect, 5000);
    });
}

function processTick(asset, tick) {
    if (!asset) return;
    const price = tick.price;
    const time = tick.time;
    const candleTime = Math.floor(time / TIMEFRAME) * TIMEFRAME;

    if (!buffer[asset]) buffer[asset] = { current: null, pending: [] };
    let b = buffer[asset];

    if (b.current && b.current.time === candleTime) {
        b.current.close = price;
        b.current.high = Math.max(b.current.high, price);
        b.current.low = Math.min(b.current.low, price);
    } else {
        if (b.current) b.pending.push(b.current);
        b.current = { time: candleTime, open: price, high: price, low: price, close: price };
    }
}

// Monthly Storage Logic
// Append data to a massive file per asset. 
// "collect one month candle data"
setInterval(() => {
    const assets = Object.keys(buffer);
    if (assets.length === 0) return;

    console.log(`💾 [Monthly] Archiving data for ${assets.length} assets...`);

    assets.forEach(asset => {
        const b = buffer[asset];
        if (b.pending.length > 0) {
            const filePath = path.join(DATA_DIR, `${asset}_full_history.json`);

            let existingData = [];
            if (fs.existsSync(filePath)) {
                try {
                    existingData = JSON.parse(fs.readFileSync(filePath));
                } catch (e) { }
            }

            existingData.push(...b.pending);

            // Prune data older than 30 days
            const thirtyDaysAgo = Math.floor(Date.now() / 1000) - (30 * 24 * 60 * 60);
            existingData = existingData.filter(c => c.time > thirtyDaysAgo);

            fs.writeFileSync(filePath, JSON.stringify(existingData));
            b.pending = [];
        }
    });

}, 60000); // Flush every minute

connect();
