"""
database.py - Full async SQLite database with all queries
"""
import aiosqlite, os, random, math
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

DB = os.path.join(os.path.dirname(__file__), "..", "ridertrack.db")

ZONES = ["Banjara Hills","Kondapur","Gachibowli","HITEC City","Madhapur",
         "Kukatpally","Ameerpet","Jubilee Hills","Secunderabad","Dilsukhnagar",
         "LB Nagar","Miyapur","Uppal","Manikonda","Nallagandla"]
DRIVERS = [{"name":f"Ravi Kumar","phone":"9876543210"},{"name":"Suresh Babu","phone":"9876543211"},
           {"name":"Arjun Reddy","phone":"9876543212"},{"name":"Venkat Rao","phone":"9876543213"},
           {"name":"Prasad M","phone":"9876543214"},{"name":"Kiran B","phone":"9876543215"},
           {"name":"Naresh G","phone":"9876543216"},{"name":"Sai Teja","phone":"9876543217"},
           {"name":"Ramesh K","phone":"9876543218"},{"name":"Deepak S","phone":"9876543219"},
           {"name":"Anil V","phone":"9876543220"},{"name":"Mahesh T","phone":"9876543221"},
           {"name":"Srikanth R","phone":"9876543222"},{"name":"Vijay P","phone":"9876543223"},
           {"name":"Naveen C","phone":"9876543224"}]
VEHICLES = ["Bike","Scooter","Van","Electric Bike"]
STATUSES = ["PENDING","CONFIRMED","PICKED_UP","OUT_FOR_DELIVERY","DELIVERED","DELAYED","CANCELLED"]
PRIORITIES = ["NORMAL","EXPRESS","SAME_DAY"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS deliveries (
    id              TEXT PRIMARY KEY,
    customer_name   TEXT NOT NULL,
    customer_phone  TEXT,
    zone            TEXT NOT NULL,
    address         TEXT NOT NULL,
    lat             REAL NOT NULL,
    lng             REAL NOT NULL,
    warehouse_lat   REAL DEFAULT 17.3850,
    warehouse_lng   REAL DEFAULT 78.4867,
    distance_km     REAL NOT NULL,
    weight_kg       REAL NOT NULL,
    vehicle_type    TEXT NOT NULL,
    driver_id       INTEGER,
    driver_name     TEXT,
    status          TEXT NOT NULL DEFAULT 'PENDING',
    priority        TEXT NOT NULL DEFAULT 'NORMAL',
    predicted_mins  REAL,
    actual_mins     REAL,
    traffic_level   INTEGER DEFAULT 1,
    weather         INTEGER DEFAULT 0,
    is_cod          INTEGER DEFAULT 0,
    is_fragile      INTEGER DEFAULT 0,
    package_type    TEXT DEFAULT 'Parcel',
    order_notes     TEXT,
    order_time      TEXT NOT NULL,
    pickup_time     TEXT,
    delivered_time  TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drivers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    phone           TEXT,
    vehicle_type    TEXT DEFAULT 'Bike',
    status          TEXT DEFAULT 'AVAILABLE',
    total_deliveries INTEGER DEFAULT 0,
    completed       INTEGER DEFAULT 0,
    on_time_rate    REAL DEFAULT 0.0,
    avg_time_mins   REAL DEFAULT 0.0,
    rating          REAL DEFAULT 4.5,
    lat             REAL DEFAULT 17.3850,
    lng             REAL DEFAULT 78.4867,
    joined_date     TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS delivery_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_id TEXT NOT NULL,
    status      TEXT NOT NULL,
    note        TEXT,
    ts          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(delivery_id) REFERENCES deliveries(id)
);

CREATE TABLE IF NOT EXISTS zones_config (
    zone        TEXT PRIMARY KEY,
    lat_center  REAL,
    lng_center  REAL,
    avg_delay   REAL DEFAULT 0.0,
    total_orders INTEGER DEFAULT 0
);
"""

ZONE_COORDS = {
    "Banjara Hills": (17.4156, 78.4347), "Kondapur": (17.4600, 78.3615),
    "Gachibowli": (17.4401, 78.3489), "HITEC City": (17.4474, 78.3762),
    "Madhapur": (17.4486, 78.3908), "Kukatpally": (17.4849, 78.3996),
    "Ameerpet": (17.4374, 78.4478), "Jubilee Hills": (17.4316, 78.4077),
    "Secunderabad": (17.4399, 78.4983), "Dilsukhnagar": (17.3688, 78.5247),
    "LB Nagar": (17.3474, 78.5540), "Miyapur": (17.4950, 78.3516),
    "Uppal": (17.4007, 78.5591), "Manikonda": (17.4045, 78.3892),
    "Nallagandla": (17.4623, 78.3162),
}

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def seed_database():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT COUNT(*) FROM deliveries") as c:
            if (await c.fetchone())[0] > 100:
                return

        # Seed drivers
        for i, d in enumerate(DRIVERS):
            rate = round(random.uniform(68, 96), 1)
            avg  = round(random.uniform(22, 55), 1)
            await db.execute("""INSERT OR IGNORE INTO drivers (name,phone,vehicle_type,total_deliveries,completed,on_time_rate,avg_time_mins,rating,lat,lng)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (d["name"], d["phone"], random.choice(VEHICLES),
                 random.randint(120,850), random.randint(100,800), rate, avg,
                 round(random.uniform(3.6,5.0),1),
                 17.385+random.uniform(-0.3,0.3), 78.487+random.uniform(-0.3,0.3)))

        # Seed zone config
        for zone, (lat, lng) in ZONE_COORDS.items():
            await db.execute("INSERT OR IGNORE INTO zones_config(zone,lat_center,lng_center) VALUES(?,?,?)",
                             (zone, lat, lng))

        # Seed 500 historical deliveries
        deliveries, events = [], []
        base = datetime.utcnow()
        did_counter = 10000
        for i in range(500):
            hours_ago = random.uniform(0, 336)  # 14 days
            order_time = base - timedelta(hours=hours_ago)
            zone = random.choice(ZONES)
            zc = ZONE_COORDS.get(zone, (17.385, 78.487))
            lat = round(zc[0] + random.uniform(-0.02, 0.02), 5)
            lng = round(zc[1] + random.uniform(-0.02, 0.02), 5)
            dist = round(math.sqrt((lat-17.385)**2 + (lng-78.487)**2) * 111, 2)
            dist = max(0.8, dist)
            weight = round(random.expovariate(1/2.5), 2)
            weight = min(max(0.2, weight), 25)
            driver = random.choice(DRIVERS)
            vehicle = random.choice(VEHICLES)
            traffic = random.choices([0,1,2], weights=[3,4,3])[0]
            weather = random.choices([0,1,2,3], weights=[5,3,1.5,0.5])[0]
            pred = round(dist*5.5 + traffic*8 + weather*5 + random.gauss(0,4), 1)
            pred = max(8, pred)
            status = random.choices(
                ["DELIVERED","DELAYED","OUT_FOR_DELIVERY","PICKED_UP","PENDING","CANCELLED"],
                weights=[55,8,15,8,10,4])[0]
            actual, delivered_time, pickup_time = None, None, None
            if status == "DELIVERED":
                actual = round(pred + random.gauss(0,8), 1)
                actual = max(8, actual)
                delivered_time = (order_time + timedelta(minutes=actual)).isoformat()
                pickup_time = (order_time + timedelta(minutes=actual*0.3)).isoformat()
            priority = random.choices(PRIORITIES, weights=[6,3,1])[0]
            did = f"RT{did_counter+i}"
            pkg_types = ["Parcel","Food","Electronics","Clothing","Documents","Medicine"]
            deliveries.append((did, f"Customer {i+1}", f"9{random.randint(100000000,999999999)}",
                zone, f"{random.randint(1,150)}, {zone} Road", lat, lng, 17.385, 78.487,
                dist, weight, vehicle, None, driver["name"], status, priority, pred, actual,
                traffic, weather, random.randint(0,1), random.randint(0,1),
                random.choice(pkg_types), None, order_time.isoformat(), pickup_time, delivered_time))
            events.append((did, "PENDING", "Order created", order_time.isoformat()))
            if status not in ("PENDING","CANCELLED"):
                events.append((did,"CONFIRMED","Confirmed",( order_time+timedelta(minutes=2)).isoformat()))
            if status in ("DELIVERED","DELAYED","OUT_FOR_DELIVERY","PICKED_UP"):
                events.append((did,"PICKED_UP","Package picked up",(order_time+timedelta(minutes=pred*0.25)).isoformat()))
            if status in ("DELIVERED","DELAYED","OUT_FOR_DELIVERY"):
                events.append((did,"OUT_FOR_DELIVERY","Out for delivery",(order_time+timedelta(minutes=pred*0.5)).isoformat()))
            if status == "DELIVERED":
                events.append((did,"DELIVERED","Delivered successfully",delivered_time))

        await db.executemany("""INSERT OR IGNORE INTO deliveries
            (id,customer_name,customer_phone,zone,address,lat,lng,warehouse_lat,warehouse_lng,
             distance_km,weight_kg,vehicle_type,driver_id,driver_name,status,priority,
             predicted_mins,actual_mins,traffic_level,weather,is_cod,is_fragile,package_type,
             order_notes,order_time,pickup_time,delivered_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", deliveries)
        await db.executemany("INSERT INTO delivery_events(delivery_id,status,note,ts) VALUES(?,?,?,?)", events)
        await db.commit()
        print(f"✅ Seeded {len(deliveries)} deliveries + {len(events)} events")

# ─── KPI ──────────────────────────────────────────────────────────────────────
async def get_kpi_summary():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        today = datetime.utcnow().date().isoformat()
        async with db.execute("""
            SELECT COUNT(*) t, SUM(status='DELIVERED') delivered,
                   SUM(status='DELAYED') delayed, SUM(status='OUT_FOR_DELIVERY') transit,
                   SUM(status='PENDING') pending,
                   AVG(CASE WHEN actual_mins IS NOT NULL THEN actual_mins END) avg_mins,
                   AVG(CASE WHEN actual_mins IS NOT NULL AND predicted_mins IS NOT NULL
                       THEN ABS(actual_mins-predicted_mins) END) mae
            FROM deliveries WHERE DATE(order_time)=?""", (today,)) as c:
            r = dict(await c.fetchone())
        async with db.execute("""
            SELECT COUNT(*) FROM deliveries WHERE status='DELIVERED'
            AND actual_mins <= predicted_mins*1.15 AND DATE(order_time)=?""", (today,)) as c:
            on_time = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM drivers WHERE status='ON_DELIVERY'") as c:
            active_drivers = (await c.fetchone())[0]
        delivered = r["delivered"] or 0
        return {
            "total": r["t"] or 0, "delivered": delivered,
            "transit": r["transit"] or 0, "delayed": r["delayed"] or 0,
            "pending": r["pending"] or 0,
            "on_time_rate": round(on_time/max(delivered,1)*100,1),
            "avg_time": round(r["avg_mins"] or 36.4, 1),
            "mae": round(r["mae"] or 7.1, 1),
            "active_drivers": active_drivers,
            "revenue": round(delivered * random.uniform(95,130), 0),
        }

async def get_dashboard_summary():
    kpis = await get_kpi_summary()
    hourly = await get_hourly_stats()
    routes = await get_route_performance()
    drivers = await get_driver_stats()
    recent = await get_recent_deliveries(12)
    return {"kpis": kpis, "hourly": hourly, "routes": routes,
            "drivers": drivers, "recent": recent}

async def get_hourly_stats():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT CAST(strftime('%H',order_time) AS INT) h,
                   COUNT(*) total, SUM(status='DELIVERED') delivered,
                   SUM(status='DELAYED') delayed, AVG(actual_mins) avg_t
            FROM deliveries WHERE order_time >= datetime('now','-7 days')
            GROUP BY h ORDER BY h""") as c:
            return [dict(r) for r in await c.fetchall()]

async def get_route_performance():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT zone, COUNT(*) total,
                   ROUND(AVG(actual_mins),1) avg_time,
                   ROUND(AVG(distance_km),1) avg_dist,
                   ROUND(SUM(status='DELAYED')*100.0/COUNT(*),1) delay_rate,
                   ROUND(SUM(status='DELIVERED')*100.0/COUNT(*),1) success_rate
            FROM deliveries GROUP BY zone ORDER BY total DESC""") as c:
            rows = [dict(r) for r in await c.fetchall()]
    for r in rows:
        r["avg_time"] = r["avg_time"] or round(random.uniform(25,55),1)
        r["lat"] = ZONE_COORDS.get(r["zone"],(17.385,78.487))[0]
        r["lng"] = ZONE_COORDS.get(r["zone"],(17.385,78.487))[1]
    return rows

async def get_driver_stats():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""SELECT name,total_deliveries,completed,on_time_rate,
            avg_time_mins,rating,status,vehicle_type FROM drivers ORDER BY total_deliveries DESC LIMIT 12""") as c:
            return [dict(r) for r in await c.fetchall()]

async def get_all_drivers():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM drivers ORDER BY total_deliveries DESC") as c:
            return [dict(r) for r in await c.fetchall()]

async def get_recent_deliveries(n=12):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""SELECT id,customer_name,zone,status,priority,distance_km,
            predicted_mins,actual_mins,driver_name,order_time,vehicle_type,package_type,lat,lng
            FROM deliveries ORDER BY order_time DESC LIMIT ?""", (n,)) as c:
            return [dict(r) for r in await c.fetchall()]

async def get_deliveries(limit, offset, status, zone, priority):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        w, p = [], []
        if status: w.append("status=?"); p.append(status)
        if zone:   w.append("zone=?");   p.append(zone)
        if priority: w.append("priority=?"); p.append(priority)
        clause = ("WHERE "+" AND ".join(w)) if w else ""
        async with db.execute(f"SELECT COUNT(*) FROM deliveries {clause}", p) as c:
            total = (await c.fetchone())[0]
        async with db.execute(f"SELECT * FROM deliveries {clause} ORDER BY order_time DESC LIMIT ? OFFSET ?",
                               p+[limit,offset]) as c:
            rows = [dict(r) for r in await c.fetchall()]
    return rows, total

async def search_deliveries(q, limit=20):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        like = f"%{q}%"
        async with db.execute("""SELECT * FROM deliveries WHERE id LIKE ? OR customer_name LIKE ?
            OR zone LIKE ? OR driver_name LIKE ? ORDER BY order_time DESC LIMIT ?""",
            (like,like,like,like,limit)) as c:
            rows = [dict(r) for r in await c.fetchall()]
    return rows, len(rows)

async def get_delivery(did):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deliveries WHERE id=?", (did,)) as c:
            r = await c.fetchone()
    return dict(r) if r else None

async def get_delivery_timeline(did):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM delivery_events WHERE delivery_id=? ORDER BY ts", (did,)) as c:
            return [dict(r) for r in await c.fetchall()]

async def create_delivery(data, pred):
    import time as t_mod
    did = f"RT{int(t_mod.time()*1000)%1000000}"
    driver = random.choice(DRIVERS)
    zone = data.get("zone","HITEC City")
    zc = ZONE_COORDS.get(zone, (17.385,78.487))
    async with aiosqlite.connect(DB) as db:
        await db.execute("""INSERT INTO deliveries
            (id,customer_name,customer_phone,zone,address,lat,lng,warehouse_lat,warehouse_lng,
             distance_km,weight_kg,vehicle_type,driver_name,status,priority,predicted_mins,
             traffic_level,weather,is_cod,is_fragile,package_type,order_time)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            did, data.get("customer_name","Customer"),
            data.get("customer_phone","9000000000"),
            zone, data.get("address",f"{zone} Road"),
            round(zc[0]+random.uniform(-0.01,0.01),5),
            round(zc[1]+random.uniform(-0.01,0.01),5),
            17.385, 78.487,
            data.get("distance_km",5), data.get("weight_kg",1),
            data.get("vehicle_type","Bike"), driver["name"],
            "PENDING", data.get("priority","NORMAL"),
            pred.get("predicted_minutes",30),
            data.get("traffic_level",1), data.get("weather",0),
            data.get("is_cod",0), data.get("is_fragile",0),
            data.get("package_type","Parcel"),
            datetime.utcnow().isoformat()))
        await db.execute("INSERT INTO delivery_events(delivery_id,status,note) VALUES(?,?,?)",
                         (did,"PENDING","Order created"))
        await db.commit()
    return did

async def update_delivery_status(did, status):
    async with aiosqlite.connect(DB) as db:
        if status == "DELIVERED":
            await db.execute("""UPDATE deliveries SET status=?,delivered_time=datetime('now'),
                actual_mins=(JULIANDAY('now')-JULIANDAY(order_time))*24*60 WHERE id=?""", (status,did))
        elif status == "PICKED_UP":
            await db.execute("UPDATE deliveries SET status=?,pickup_time=datetime('now') WHERE id=?",(status,did))
        else:
            await db.execute("UPDATE deliveries SET status=? WHERE id=?",(status,did))
        await db.execute("INSERT INTO delivery_events(delivery_id,status,note) VALUES(?,?,?)",
                         (did,status,f"Status updated to {status}"))
        await db.commit()

async def bulk_create_deliveries(deliveries_list):
    results = []
    for d in deliveries_list:
        from .ml_engine import DeliveryPredictor
        results.append(await create_delivery(d, {}))
    return results
