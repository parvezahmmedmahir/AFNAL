
import asyncio
import websockets
import json

async def test_dashboard_ws():
    uri = "ws://127.0.0.1:8000/ws"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            msg_type = data.get("type")
            
            print(f"Received message type: {msg_type}")
            
            if msg_type == "assets":
                print(f"Received {len(data['data'])} assets.")
                # Once we get assets, let's pick one and request it to test history/ticks
                assets = data['data']
                open_assets = [a for a in assets if a.get('open')]
                
                target = None
                for a in open_assets:
                    if "EURUSD" in a['symbol']:
                        target = a['symbol']
                        break
                
                if not target and open_assets:
                    target = open_assets[0]['symbol']
                
                if target:
                    print(f"Switching to open asset: {target}")
                    await websocket.send(json.dumps({
                        "type": "switch",
                        "asset": target,
                        "period": 60
                    }))
                else:
                    print("No open assets found to test switch.")
                    break

            elif msg_type == "history":
                print(f"Received history: {len(data['data'])} candles.")
                print("Waiting for ticks...")

            elif msg_type == "tick":
                print(f"Tick received: {data['data']}")
                # Receive a few ticks then exit
                print("Live data verified.")
                break
                
            elif msg_type == "error":
                print(f"Error: {data['message']}")
                break

if __name__ == "__main__":
    try:
        asyncio.run(test_dashboard_ws())
    except Exception as e:
        print(f"Test failed: {e}")
