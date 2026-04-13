"""
realtime.py - WebSocket connection manager + live position simulation
"""
import asyncio, random, math, time
from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self._id = 0

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        self._id += 1
        cid = str(self._id)
        self.active[cid] = ws
        print(f"WS connected: {cid} | Total: {len(self.active)}")
        return cid

    def disconnect(self, cid: str):
        self.active.pop(cid, None)

    async def broadcast(self, msg: str):
        dead = []
        for cid, ws in self.active.items():
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.active.pop(cid, None)

# ── Live GPS position simulation ─────────────────────────────────────────────
DEPOT = {"lat": 17.3850, "lng": 78.4867}
ZONE_TARGETS = [
    (17.4156, 78.4347, "Banjara Hills"), (17.4600, 78.3615, "Kondapur"),
    (17.4401, 78.3489, "Gachibowli"),    (17.4474, 78.3762, "HITEC City"),
    (17.4486, 78.3908, "Madhapur"),      (17.4849, 78.3996, "Kukatpally"),
    (17.4374, 78.4478, "Ameerpet"),      (17.4316, 78.4077, "Jubilee Hills"),
    (17.4399, 78.4983, "Secunderabad"),  (17.3688, 78.5247, "Dilsukhnagar"),
    (17.3474, 78.5540, "LB Nagar"),      (17.4950, 78.3516, "Miyapur"),
]
DRIVER_NAMES = ["Ravi K","Suresh B","Arjun R","Venkat R","Prasad M",
                "Kiran B","Naresh G","Sai T","Ramesh K","Deepak S",
                "Anil V","Mahesh T","Srikanth R","Vijay P","Naveen C"]

def generate_live_positions(tick: int) -> list:
    positions = []
    t = tick * 0.04  # smooth movement speed
    for i, (tlat, tlng, zone) in enumerate(ZONE_TARGETS[:12]):
        # Smooth interpolation between depot and target with sine wave variation
        progress = (math.sin(t + i * 0.7) + 1) / 2  # 0..1 oscillating
        lat = DEPOT["lat"] + (tlat - DEPOT["lat"]) * progress + math.sin(t*1.3+i)*0.004
        lng = DEPOT["lng"] + (tlng - DEPOT["lng"]) * progress + math.cos(t*1.1+i)*0.004
        eta = max(1, int(30 * (1 - progress) + 3))
        statuses = ["moving","moving","moving","delivered","delayed"]
        status = statuses[i % len(statuses)]
        if tick % 40 == i % 40:  # occasionally flip status
            status = random.choice(["moving","delayed"])
        positions.append({
            "id":       f"RT{10000+i}",
            "driver":   DRIVER_NAMES[i],
            "lat":      round(lat, 5),
            "lng":      round(lng, 5),
            "status":   status,
            "eta":      f"{eta} min",
            "zone":     zone,
            "speed":    round(random.uniform(18, 38), 1),
            "battery":  round(random.uniform(40, 100), 0) if i % 3 == 0 else None,
        })
    return positions

ALERT_POOL = [
    ("warning",  "⚠️ Heavy traffic on NH65 — rerouting affected deliveries"),
    ("success",  "✅ Ravi Kumar completed 20th delivery today!"),
    ("info",     "🌧️ Rain expected in Kondapur — 3 deliveries may be delayed"),
    ("warning",  "⚠️ RT10423 delayed — customer not available"),
    ("success",  "✅ Zone Gachibowli: 98% on-time rate this hour"),
    ("info",     "📦 Peak hour surge: 47 orders in last 30 min"),
    ("success",  "✅ New driver Naveen C joined the fleet"),
    ("warning",  "⚠️ Battery low on Electric Bike EV-03 — reassigning"),
]

def generate_alert(tick: int):
    if tick % 12 == 0:  # every ~30 seconds
        return random.choice(ALERT_POOL)
    return None
