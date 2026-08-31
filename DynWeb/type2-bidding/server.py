"""
Type II RaceBench: Online Bidding
Auction page where the current bid increases from $500 to $700 after a delay.
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Configuration
INITIAL_BID = int(os.getenv("INITIAL_BID", "500"))
UPDATED_BID = int(os.getenv("UPDATED_BID", "700"))
BID_CHANGE_DELAY = float(os.getenv("BID_CHANGE_DELAY", "3.0"))
MIN_INCREMENT = int(os.getenv("MIN_INCREMENT", "25"))
PORT = int(os.getenv("PORT", "8004"))

# State
current_bid = INITIAL_BID
bid_history = [
    {"bidder": "user_jane82", "amount": 350, "time": "2:41 PM"},
    {"bidder": "collector_max", "amount": 420, "time": "2:43 PM"},
    {"bidder": "user_jane82", "amount": 475, "time": "2:45 PM"},
    {"bidder": "collector_max", "amount": INITIAL_BID, "time": "2:47 PM"},
]
bid_changed = False
connected_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    connected_clients.clear()


app = FastAPI(lifespan=lifespan)


def get_html():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path) as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
async def root():
    return get_html()


@app.get("/api/config")
async def config():
    return {
        "initial_bid": INITIAL_BID,
        "updated_bid": UPDATED_BID,
        "delay": BID_CHANGE_DELAY,
        "min_increment": MIN_INCREMENT,
    }


@app.get("/api/reset")
async def reset():
    global current_bid, bid_changed, bid_history
    current_bid = INITIAL_BID
    bid_changed = False
    bid_history = bid_history[:4]
    for ws in connected_clients:
        try:
            await ws.send_json({
                "type": "bid_update",
                "current_bid": current_bid,
                "history": bid_history,
            })
        except Exception:
            pass
    return {"status": "reset", "current_bid": current_bid}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global current_bid, bid_changed
    await ws.accept()
    connected_clients.append(ws)

    await ws.send_json({
        "type": "init",
        "current_bid": current_bid,
        "min_increment": MIN_INCREMENT,
        "history": bid_history,
        "end_time": time.time() + 600,  # 10-min auction window
    })

    if not bid_changed:
        bid_changed = True

        async def incoming_bid():
            global current_bid
            await asyncio.sleep(BID_CHANGE_DELAY)
            current_bid = UPDATED_BID
            bid_history.append({
                "bidder": "sniper_99",
                "amount": UPDATED_BID,
                "time": "2:49 PM",
            })
            for client in list(connected_clients):
                try:
                    await client.send_json({
                        "type": "bid_update",
                        "current_bid": current_bid,
                        "bidder": "sniper_99",
                        "history": bid_history,
                    })
                except Exception:
                    pass

        asyncio.create_task(incoming_bid())

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "place_bid":
                amount = msg.get("amount", 0)
                if amount > current_bid:
                    current_bid = amount
                    bid_history.append({
                        "bidder": "you",
                        "amount": amount,
                        "time": time.strftime("%I:%M %p"),
                    })
                    for client in list(connected_clients):
                        try:
                            await client.send_json({
                                "type": "bid_update",
                                "current_bid": current_bid,
                                "bidder": "you",
                                "history": bid_history,
                            })
                        except Exception:
                            pass
                    await ws.send_json({
                        "type": "bid_result",
                        "success": True,
                        "amount": amount,
                        "message": f"Your bid of ${amount} is now the highest!",
                    })
                else:
                    await ws.send_json({
                        "type": "bid_result",
                        "success": False,
                        "amount": amount,
                        "current_bid": current_bid,
                        "message": f"Your bid of ${amount} is below the current bid of ${current_bid}.",
                    })
    except WebSocketDisconnect:
        connected_clients.remove(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
