"""
Type II RaceBench: Item Availability Change
E-commerce product page where stock quantity drops to 0 after a delay.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Configuration
INITIAL_STOCK = int(os.getenv("INITIAL_STOCK", "3"))
STOCK_DROP_DELAY = float(os.getenv("STOCK_DROP_DELAY", "3.0"))
PORT = int(os.getenv("PORT", "8003"))

# State
current_stock = INITIAL_STOCK
stock_dropped = False
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
        "initial_stock": INITIAL_STOCK,
        "delay": STOCK_DROP_DELAY,
    }


@app.get("/api/reset")
async def reset():
    global current_stock, stock_dropped
    current_stock = INITIAL_STOCK
    stock_dropped = False
    for ws in connected_clients:
        try:
            await ws.send_json({"type": "stock_update", "stock": current_stock})
        except Exception:
            pass
    return {"status": "reset", "stock": current_stock}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global current_stock, stock_dropped
    await ws.accept()
    connected_clients.append(ws)

    await ws.send_json({"type": "stock_update", "stock": current_stock})

    if not stock_dropped:
        stock_dropped = True

        async def drain_stock():
            global current_stock
            await asyncio.sleep(STOCK_DROP_DELAY)
            # Stock drops progressively to 0
            while current_stock > 0:
                current_stock -= 1
                for client in list(connected_clients):
                    try:
                        await client.send_json({
                            "type": "stock_update",
                            "stock": current_stock,
                        })
                    except Exception:
                        pass
                if current_stock > 0:
                    await asyncio.sleep(0.3)

        asyncio.create_task(drain_stock())

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "add_to_cart":
                qty = msg.get("quantity", 1)
                if current_stock >= qty:
                    await ws.send_json({
                        "type": "cart_result",
                        "success": True,
                        "quantity": qty,
                        "stock_at_action": current_stock,
                    })
                else:
                    await ws.send_json({
                        "type": "cart_result",
                        "success": False,
                        "quantity": qty,
                        "stock_at_action": current_stock,
                        "message": "Item is out of stock",
                    })
    except WebSocketDisconnect:
        connected_clients.remove(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
