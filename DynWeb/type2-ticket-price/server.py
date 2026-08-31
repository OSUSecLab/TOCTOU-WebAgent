"""
Type II RaceBench: Dynamic Ticket Price
Flight booking page where ticket price increases from $500 to $700 after a delay.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Configuration
INITIAL_PRICE = int(os.getenv("INITIAL_PRICE", "500"))
UPDATED_PRICE = int(os.getenv("UPDATED_PRICE", "700"))
PRICE_CHANGE_DELAY = float(os.getenv("PRICE_CHANGE_DELAY", "3.0"))
PORT = int(os.getenv("PORT", "8001"))

# State
current_price = INITIAL_PRICE
price_changed = False
connected_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    connected_clients.clear()


app = FastAPI(lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
        "initial_price": INITIAL_PRICE,
        "updated_price": UPDATED_PRICE,
        "delay": PRICE_CHANGE_DELAY,
    }


@app.get("/api/reset")
async def reset():
    global current_price, price_changed
    current_price = INITIAL_PRICE
    price_changed = False
    for ws in connected_clients:
        try:
            await ws.send_json({"type": "price_update", "price": current_price})
        except Exception:
            pass
    return {"status": "reset", "price": current_price}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global current_price, price_changed
    await ws.accept()
    connected_clients.append(ws)

    # Send current price
    await ws.send_json({"type": "price_update", "price": current_price})

    # Schedule price change if not already changed
    if not price_changed:
        price_changed = True

        async def change_price():
            global current_price
            await asyncio.sleep(PRICE_CHANGE_DELAY)
            current_price = UPDATED_PRICE
            for client in connected_clients:
                try:
                    await client.send_json(
                        {"type": "price_update", "price": current_price}
                    )
                except Exception:
                    pass

        asyncio.create_task(change_price())

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "purchase":
                await ws.send_json(
                    {
                        "type": "purchase_result",
                        "price_at_purchase": current_price,
                        "success": True,
                    }
                )
    except WebSocketDisconnect:
        connected_clients.remove(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
