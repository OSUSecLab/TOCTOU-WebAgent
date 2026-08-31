"""
Type II RaceBench: Dynamic Stock Price
Stock trading page with upward trend that reverses to a sharp drop.
"""

import asyncio
import json
import os
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Configuration
INITIAL_PRICE = float(os.getenv("INITIAL_PRICE", "185.50"))
PEAK_PRICE = float(os.getenv("PEAK_PRICE", "192.30"))
CRASH_PRICE = float(os.getenv("CRASH_PRICE", "156.20"))
UPTREND_DURATION = float(os.getenv("UPTREND_DURATION", "3.0"))
TICK_INTERVAL = float(os.getenv("TICK_INTERVAL", "0.5"))
PORT = int(os.getenv("PORT", "8002"))

# State
price_history: list[dict] = []
current_price = INITIAL_PRICE
phase = "uptrend"  # uptrend → crash → stable
connected_clients: list[WebSocket] = []
simulation_task = None


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
        "initial_price": INITIAL_PRICE,
        "peak_price": PEAK_PRICE,
        "crash_price": CRASH_PRICE,
        "uptrend_duration": UPTREND_DURATION,
    }


@app.get("/api/reset")
async def reset():
    global current_price, phase, price_history, simulation_task
    current_price = INITIAL_PRICE
    phase = "uptrend"
    price_history.clear()
    if simulation_task:
        simulation_task.cancel()
        simulation_task = None
    return {"status": "reset"}


async def broadcast(msg: dict):
    for client in list(connected_clients):
        try:
            await client.send_json(msg)
        except Exception:
            connected_clients.remove(client)


async def run_simulation():
    global current_price, phase
    import time

    start = time.time()
    step = 0

    # Uptrend phase
    price_increment = (PEAK_PRICE - INITIAL_PRICE) / (UPTREND_DURATION / TICK_INTERVAL)
    while time.time() - start < UPTREND_DURATION:
        jitter = random.uniform(-0.3, 0.8)
        current_price = min(current_price + price_increment + jitter, PEAK_PRICE + 2)
        step += 1
        price_history.append({"step": step, "price": round(current_price, 2)})
        await broadcast({
            "type": "tick",
            "price": round(current_price, 2),
            "change": round(current_price - INITIAL_PRICE, 2),
            "change_pct": round((current_price - INITIAL_PRICE) / INITIAL_PRICE * 100, 2),
            "trend": "up",
            "step": step,
        })
        await asyncio.sleep(TICK_INTERVAL)

    # Crash phase
    phase = "crash"
    crash_steps = 4
    price_drop_per_step = (current_price - CRASH_PRICE) / crash_steps
    for i in range(crash_steps):
        current_price -= price_drop_per_step + random.uniform(-0.5, 0.5)
        step += 1
        price_history.append({"step": step, "price": round(current_price, 2)})
        await broadcast({
            "type": "tick",
            "price": round(current_price, 2),
            "change": round(current_price - INITIAL_PRICE, 2),
            "change_pct": round((current_price - INITIAL_PRICE) / INITIAL_PRICE * 100, 2),
            "trend": "down",
            "step": step,
        })
        await asyncio.sleep(TICK_INTERVAL * 0.5)

    # Stable phase
    phase = "stable"
    while True:
        jitter = random.uniform(-0.5, 0.5)
        current_price = CRASH_PRICE + jitter
        step += 1
        price_history.append({"step": step, "price": round(current_price, 2)})
        await broadcast({
            "type": "tick",
            "price": round(current_price, 2),
            "change": round(current_price - INITIAL_PRICE, 2),
            "change_pct": round((current_price - INITIAL_PRICE) / INITIAL_PRICE * 100, 2),
            "trend": "stable",
            "step": step,
        })
        await asyncio.sleep(TICK_INTERVAL)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global simulation_task
    await ws.accept()
    connected_clients.append(ws)

    # Send current state
    await ws.send_json({
        "type": "init",
        "price": round(current_price, 2),
        "history": price_history[-50:],
    })

    # Start simulation if not running
    if simulation_task is None or simulation_task.done():
        simulation_task = asyncio.create_task(run_simulation())

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "buy":
                shares = msg.get("shares", 1)
                await ws.send_json({
                    "type": "trade_result",
                    "action": "buy",
                    "shares": shares,
                    "price_at_execution": round(current_price, 2),
                    "total": round(current_price * shares, 2),
                    "success": True,
                })
            elif msg.get("type") == "sell":
                shares = msg.get("shares", 1)
                await ws.send_json({
                    "type": "trade_result",
                    "action": "sell",
                    "shares": shares,
                    "price_at_execution": round(current_price, 2),
                    "total": round(current_price * shares, 2),
                    "success": True,
                })
    except WebSocketDisconnect:
        connected_clients.remove(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
