# 🛵 RiderTrack — Last-Mile Delivery Intelligence Platform

> **Full-stack project** — Uber/Zomato/Zepto quality design · Real-time WebSocket · FastAPI · SQLite · ML Engine · Live Fleet Map

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![ML](https://img.shields.io/badge/ML-Gradient%20Boosting-orange)
![WebSocket](https://img.shields.io/badge/Realtime-WebSocket-purple)

---

## 📸 What This Looks Like

A full operations dashboard with:
- **Live fleet map** — animated rider positions updating every 2.5s
- **KPI cards** — total orders, delivered, in-transit, delayed, on-time rate
- **Real-time charts** — hourly volume, status donut, zone performance bars
- **Deliveries table** — paginated with status/zone/priority filters + row click → modal
- **Predict ETA** — sliders + dropdowns → ML API call → animated result card with factor breakdown
- **Analytics** — zone avg time, delay rate, weekly trend, vehicle/priority splits
- **Driver leaderboard** — ranked with ratings, scatter performance chart
- **WebSocket toasts** — live alerts for delays, achievements, weather

---

## 🗂️ Project Structure

```
ridertrack/
├── backend/
│   ├── src/
│   │   ├── main.py          # FastAPI app, WebSocket, 10+ REST endpoints
│   │   ├── database.py      # SQLite async CRUD + analytics (aiosqlite)
│   │   ├── ml_engine.py     # GBM model, 26 features, predictions + explanations
│   │   ├── realtime.py      # WebSocket manager, live GPS simulation
│   │   └── __init__.py
│   ├── run.py               # Entry point
│   ├── ridertrack.db        # Auto-generated SQLite database
│   └── model.pkl            # Auto-trained ML model
├── frontend/
│   └── index.html           # Complete professional dashboard (single file)
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/ridertrack.git
cd ridertrack

# 2. Python environment
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

# 3. Install
pip install -r requirements.txt

# 4. Run backend
cd backend
python run.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)

# 5. Open frontend
# Just open frontend/index.html in Chrome/Firefox
# No build step needed — pure HTML/CSS/JS
```

**On first run, the backend automatically:**
1. Creates `ridertrack.db` SQLite database
2. Seeds **500 realistic historical deliveries** with full event timelines
3. Trains the **GBM ML model** with 26 engineered features
4. Starts **WebSocket real-time broadcaster** (2.5s interval)

---

## 🗄️ Database Schema

### `deliveries` table
```sql
CREATE TABLE deliveries (
    id              TEXT PRIMARY KEY,    -- RT10042, RT10043...
    customer_name   TEXT,
    customer_phone  TEXT,
    zone            TEXT,                -- HITEC City, Banjara Hills...
    address         TEXT,
    lat, lng        REAL,                -- Delivery GPS coordinates
    distance_km     REAL,
    weight_kg       REAL,
    vehicle_type    TEXT,                -- Bike / Scooter / Van / Electric Bike
    driver_name     TEXT,
    status          TEXT,                -- PENDING → DELIVERED (7 stages)
    priority        TEXT,                -- NORMAL / EXPRESS / SAME_DAY
    predicted_mins  REAL,                -- ML model output
    actual_mins     REAL,                -- Ground truth (post-delivery)
    traffic_level   INTEGER,             -- 0=Low, 1=Med, 2=High
    weather         INTEGER,             -- 0=Clear → 3=Heavy Rain
    is_cod          INTEGER,
    is_fragile      INTEGER,
    order_time      TEXT,
    pickup_time     TEXT,
    delivered_time  TEXT
);
```

### `drivers` table
```sql
CREATE TABLE drivers (
    id              INTEGER PRIMARY KEY,
    name            TEXT,
    phone           TEXT,
    vehicle_type    TEXT,
    status          TEXT,                -- AVAILABLE / ON_DELIVERY
    total_deliveries INTEGER,
    on_time_rate    REAL,
    avg_time_mins   REAL,
    rating          REAL,
    lat, lng        REAL                 -- Current GPS
);
```

### `delivery_events` table (timeline)
```sql
CREATE TABLE delivery_events (
    delivery_id TEXT,
    status      TEXT,
    note        TEXT,
    ts          TEXT                     -- timestamp
);
```

---

## 🔌 REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Full dashboard (KPIs + charts + recent) |
| GET | `/api/kpis` | KPI summary only |
| POST | `/api/predict` | Predict delivery ETA |
| GET | `/api/predict/batch-demo` | 4 pre-built scenarios |
| GET | `/api/deliveries` | Paginated list with filters |
| GET | `/api/deliveries/{id}` | Detail + timeline |
| POST | `/api/deliveries` | Create new order |
| PATCH | `/api/deliveries/{id}/status` | Update status |
| GET | `/api/analytics/hourly` | Hourly stats |
| GET | `/api/analytics/routes` | Zone performance |
| GET | `/api/analytics/drivers` | Driver stats |
| GET | `/api/drivers` | All drivers |
| WS  | `/ws` | Live updates (KPIs, positions, alerts) |
| GET | `/api/health` | Health check |
| GET | `/docs` | Swagger UI |

### Example: Create Order + Get Prediction
```bash
curl -X POST http://localhost:8000/api/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Anwar Sheikh",
    "customer_phone": "9876543210",
    "zone": "HITEC City",
    "address": "42 Cyber Towers, HITEC City",
    "distance_km": 7.5,
    "weight_kg": 2.0,
    "vehicle_type": "Bike",
    "priority": "EXPRESS",
    "traffic_level": 2,
    "weather": 0
  }'
```

---

## 🧠 ML Model Details

**Algorithm:** Gradient Boosting Regressor (sklearn)

### 26 Engineered Features
| Category | Features |
|----------|---------|
| Distance | `distance_km`, `log_dist`, `dist_sq`, `adj_dist`, `area_type` |
| Time | `hour_sin`, `hour_cos`, `is_rush`, `is_night` |
| Conditions | `traffic_level`, `weather`, `road_quality` |
| Interactions | `dist_x_traffic`, `dist_x_weather`, `traffic_x_weather` |
| Package | `weight_kg`, `is_cod`, `is_fragile`, `prior_stops` |
| Vehicle | `vehicle_type`, `speed_factor`, `est_travel` |
| Driver | `experience`, `efficiency` |
| Composite | `complexity` |

### Performance
```
MAE:           ±3.5 minutes
R²:            0.976
±15 min acc:   82%
Training size: 4,000 synthetic records
```

---

## 🗺️ Google Maps Integration

The current map is drawn on an HTML5 Canvas for zero-dependency deployment.
To upgrade to **real Google Maps**, follow these steps:

### Step 1: Get API Key
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → Enable **Maps JavaScript API**
3. Create credentials → API Key
4. Restrict key to your domain for security

### Step 2: Replace the Canvas Map

In `frontend/index.html`, add to `<head>`:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&libraries=marker"></script>
```

Replace the `<canvas id="mapMain">` with:
```html
<div id="mapMain" style="height:280px;border-radius:14px"></div>
```

Replace the `renderMap()` function with:
```javascript
let gmap = null;
const riderMarkers = {};

function renderMap(containerId, positions, height=280) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.style.height = height + 'px';

  // Init map once
  if (!gmap) {
    gmap = new google.maps.Map(container, {
      center: { lat: 17.3850, lng: 78.4867 },
      zoom: 12,
      styles: GOOGLE_MAP_STYLE,  // see style below
      disableDefaultUI: true,
      zoomControl: true,
    });
    // Depot marker
    new google.maps.Marker({
      position: { lat: 17.3850, lng: 78.4867 },
      map: gmap,
      icon: { url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png' },
      title: 'RiderTrack Hub'
    });
  }

  // Update/create rider markers
  positions.forEach(p => {
    const pos = { lat: p.lat, lng: p.lng };
    const icon = {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 8,
      fillColor: p.status==='delivered'?'#00C48C':p.status==='delayed'?'#F53D3D':'#3B7FFF',
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeWeight: 2
    };
    if (riderMarkers[p.id]) {
      riderMarkers[p.id].setPosition(pos);
      riderMarkers[p.id].setIcon(icon);
    } else {
      riderMarkers[p.id] = new google.maps.Marker({
        position: pos, map: gmap, icon,
        title: `${p.driver} · ${p.zone} · ETA ${p.eta}`
      });
      // Info window on click
      const info = new google.maps.InfoWindow({
        content: `<div style="font-family:sans-serif;padding:6px">
          <b>${p.driver}</b><br>${p.zone}<br>ETA: <b>${p.eta}</b>
        </div>`
      });
      riderMarkers[p.id].addListener('click', () => info.open(gmap, riderMarkers[p.id]));
    }
  });
}

// Clean dark map style (like Uber)
const GOOGLE_MAP_STYLE = [
  {featureType:'all',elementType:'geometry',stylers:[{color:'#f5f5f5'}]},
  {featureType:'road',elementType:'geometry',stylers:[{color:'#ffffff'}]},
  {featureType:'road.arterial',elementType:'geometry',stylers:[{color:'#ffffff'}]},
  {featureType:'water',elementType:'geometry',stylers:[{color:'#c9e8f7'}]},
  {featureType:'poi.park',elementType:'geometry',stylers:[{color:'#d5e8c4'}]},
];
```

### Step 3: Enable Real GPS (React Native / Flutter App)
For a real mobile app, replace simulated positions with actual GPS from drivers:
```javascript
// Driver app sends position every 5 seconds
setInterval(() => {
  navigator.geolocation.getCurrentPosition(pos => {
    fetch('http://localhost:8000/api/drivers/me/position', {
      method: 'PATCH',
      body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
    });
  });
}, 5000);
```

---

## Deployment

### Option A: Localhost (for portfolio demo)
```bash
cd backend && python run.py
# Open frontend/index.html
```

### Option B: Railway.app (free cloud hosting)
```bash
# Push to GitHub, then connect to railway.app
# Set start command: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

### Option C: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/ .
RUN pip install -r ../requirements.txt
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📊 Project Bullets

> **RiderTrack — Last-Mile Delivery Intelligence Platform**
> Python · FastAPI · SQLite · Scikit-learn · WebSocket · HTML/CSS/JS
>
> - Built a startup-grade delivery ops platform with real-time WebSocket fleet tracking, FastAPI REST backend (10+ endpoints), and SQLite database with 500+ seeded records across 15 delivery zones
> - Engineered a production ML pipeline with **26 features** (cyclical time encoding, interaction terms, physics-based travel time estimate, domain composite complexity score) achieving **82% prediction accuracy within ±15 minutes**
> - Designed a Uber/Zomato-quality dashboard: animated fleet map, live KPI cards, paginated delivery table with search and filters, modal with delivery timeline, and interactive ETA prediction form
> - Implemented WebSocket broadcast loop with real-time GPS position simulation, live KPI updates every 2.5s, and contextual alert notifications

---

*Built by **Zaheer** · B.Tech AI & Data Science.*
