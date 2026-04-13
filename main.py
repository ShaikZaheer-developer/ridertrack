"""
RiderTrack - Last-Mile Delivery Intelligence Platform
FastAPI Backend with SQLite, ML Engine, WebSocket Real-time
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio, json, random, math, time
from datetime import datetime, timedelta
from typing import Optional, List
import numpy as np

from .database import init_db, seed_database, get_kpi_summary, get_deliveries, get_delivery, \
    create_delivery, update_delivery_status, get_hourly_stats, get_route_performance, \
    get_driver_stats, get_recent_deliveries, get_all_drivers, get_dashboard_summary, \
    search_deliveries, get_delivery_timeline, bulk_create_deliveries
from .ml_engine import DeliveryPredictor
from .realtime import ConnectionManager, generate_live_positions, generate_alert

app = FastAPI(title="RiderTrack API", version="3.0.0", docs_url="/docs")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=True)

predictor = DeliveryPredictor()
manager = ConnectionManager()

# ─── STARTUP ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await init_db()
    await seed_database()
    predictor.train()
    asyncio.create_task(realtime_broadcast_loop())
    print("✅ RiderTrack API v3.0 running")

# ─── WEBSOCKET ────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    try:
        # Send initial state immediately on connect
        snapshot = await get_dashboard_summary()
        await websocket.send_text(json.dumps({"type": "snapshot", "data": snapshot}))
        while True:
            await asyncio.sleep(0.5)
            msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.1) if False else None
    except (WebSocketDisconnect, asyncio.TimeoutError, Exception):
        manager.disconnect(client_id)

async def realtime_broadcast_loop():
    tick = 0
    while True:
        await asyncio.sleep(2.5)
        tick += 1
        try:
            positions = generate_live_positions(tick)
            kpis = await get_kpi_summary()
            alert = generate_alert(tick)
            payload = {"type": "live", "tick": tick, "positions": positions,
                       "kpis": kpis, "alert": alert,
                       "timestamp": datetime.utcnow().isoformat()}
            await manager.broadcast(json.dumps(payload))
        except Exception as e:
            pass

# ─── DASHBOARD ────────────────────────────────────────────────────────────────
@app.get("/api/dashboard")
async def dashboard():
    return await get_dashboard_summary()

@app.get("/api/kpis")
async def kpis():
    return await get_kpi_summary()

@app.get("/api/analytics/hourly")
async def hourly():
    return await get_hourly_stats()

@app.get("/api/analytics/routes")
async def routes():
    return await get_route_performance()

@app.get("/api/analytics/drivers")
async def drivers_analytics():
    return await get_driver_stats()

# ─── DELIVERIES ───────────────────────────────────────────────────────────────
@app.get("/api/deliveries")
async def list_deliveries(page: int=1, limit: int=15, status: str=None,
                           zone: str=None, priority: str=None, search: str=None):
    if search:
        rows, total = await search_deliveries(search, limit)
    else:
        rows, total = await get_deliveries(limit, (page-1)*limit, status, zone, priority)
    return {"data": rows, "total": total, "page": page,
            "pages": max(1, math.ceil(total/limit)), "limit": limit}

@app.get("/api/deliveries/{did}")
async def delivery_detail(did: str):
    d = await get_delivery(did)
    if not d: raise HTTPException(404, "Not found")
    d["timeline"] = await get_delivery_timeline(did)
    return d

@app.post("/api/deliveries")
async def create(body: dict):
    pred = predictor.predict(body)
    did = await create_delivery(body, pred)
    asyncio.create_task(simulate_delivery_lifecycle(did, pred.get("predicted_minutes", 30)))
    return {"id": did, "prediction": pred, "status": "PENDING"}

@app.patch("/api/deliveries/{did}/status")
async def patch_status(did: str, body: dict):
    await update_delivery_status(did, body["status"])
    await manager.broadcast(json.dumps({"type": "status_update", "id": did, "status": body["status"]}))
    return {"ok": True}

# ─── PREDICTION ───────────────────────────────────────────────────────────────
@app.post("/api/predict")
async def predict(body: dict):
    return predictor.predict(body)

@app.get("/api/predict/batch-demo")
async def batch_demo():
    scenarios = [
        {"label":"Morning rush, short", "distance_km":3,"traffic_level":2,"weather":0,"hour":9,"vehicle_type":"Bike"},
        {"label":"Rainy evening, long", "distance_km":14,"traffic_level":2,"weather":2,"hour":18,"vehicle_type":"Van"},
        {"label":"Clear noon, medium",  "distance_km":7,"traffic_level":0,"weather":0,"hour":13,"vehicle_type":"Scooter"},
        {"label":"Night express",       "distance_km":5,"traffic_level":0,"weather":1,"hour":22,"vehicle_type":"Bike","priority":"SAME_DAY"},
    ]
    return [{"scenario": s["label"], **predictor.predict(s)} for s in scenarios]

# ─── DRIVERS ─────────────────────────────────────────────────────────────────
@app.get("/api/drivers")
async def drivers():
    return await get_all_drivers()

# ─── HEALTH ──────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "model_trained": predictor.is_trained,
            "ws_clients": len(manager.active), "ts": datetime.utcnow().isoformat()}

# ─── SIMULATE DELIVERY LIFECYCLE ─────────────────────────────────────────────
async def simulate_delivery_lifecycle(did: str, eta_minutes: float):
    steps = [("CONFIRMED",4),("PICKED_UP",6),("OUT_FOR_DELIVERY",10),("DELIVERED",15)]
    for status, delay in steps:
        await asyncio.sleep(delay)
        await update_delivery_status(did, status)
        await manager.broadcast(json.dumps({"type":"delivery_update","id":did,"status":status,
                                             "ts":datetime.utcnow().isoformat()}))
