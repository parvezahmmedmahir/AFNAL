const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuration
const WS_URL = 'ws://127.0.0.1:8000/ws';
const DATA_DIR = path.join(__dirname, '../data/24h');
const TIMEFRAME = 60; // 1 minute

// Ensure directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// In-memory buffer to reduce IO
let buffer = {};

function connect() {
    const ws = new WebSocket(WS_URL);

    ws.on('open', () => {
        console.log("✅ [24H] Connected to WebSocket");
        // Trigger broad subscription
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
        console.log("❌ [24H] Disconnected. Reconnecting...");
        setTimeout(connect, 5000);
    });
}

function processTick(asset, tick) {
    if (!asset) return;

    // Logic: We append tick data or consolidated candles to a daily file
    // For 24h candle data, we usually mean minute candles collected for 24h

    // We reuse the candle construction logic
    const price = tick.price;
    const time = tick.time;
    const candleTime = Math.floor(time / TIMEFRAME) * TIMEFRAME;

    if (!buffer[asset]) {
        buffer[asset] = { current: null, pending_save: [] };
    }

    let b = buffer[asset];

    if (b.current && b.current.time === candleTime) {
        // Update current
        b.current.close = price;
        b.current.high = Math.max(b.current.high, price);
        b.current.low = Math.min(b.current.low, price);
    } else {
        // Current finished (or new start)
        if (b.current) {
            b.pending_save.push(b.current);
        }
        b.current = {
            time: candleTime,
            open: price,
            high: price,
            low: price,
            close: price
        };
    }
}

// Daily Rotation Logic
// "after 24 hour JS file after fully complete... then that is delayed"
// We will interpret this as checking the date and starting a new file, deleting old ones.
setInterval(() => {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD

    const assets = Object.keys(buffer);
    if (assets.length === 0) return;

    console.log(`💾 [24H] Flushing data for ${assets.length} assets...`);

    assets.forEach(asset => {
        const b = buffer[asset];
        if (b.pending_save.length > 0) {
            const filePath = path.join(DATA_DIR, `${asset}_${dateStr}.json`);

            // Read existing or init array
            let existingData = [];
            if (fs.existsSync(filePath)) {
                try {
                    existingData = JSON.parse(fs.readFileSync(filePath));
                } catch (e) { }
            }

            // Append
            existingData.push(...b.pending_save);
            fs.writeFileSync(filePath, JSON.stringify(existingData));

            // Clear buffer
            b.pending_save = [];
        }
    });

    // Cleanup Old Files (Keep only today)
    fs.readdir(DATA_DIR, (err, files) => {
        if (err) return;
        files.forEach(file => {
            if (!file.includes(dateStr)) {
                console.log(`🗑️ [24H] Deleting old file: ${file}`);
                fs.unlinkSync(path.join(DATA_DIR, file));
            }
        });
    });

}, 30000); // Check/Flush every 30s

connect();
