"""
ml_engine.py - Production ML Engine with full feature pipeline
GBM model, 21 engineered features, explainability
"""
import numpy as np, pandas as pd, pickle, os, random
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

MODEL_FILE = os.path.join(os.path.dirname(__file__), "..", "model.pkl")

class DeliveryPredictor:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.features = []
        self.metrics = {}

    def _synth(self, n=4000):
        np.random.seed(42)
        dist     = np.random.uniform(0.5, 22, n)
        traffic  = np.random.randint(0, 3, n)
        weather  = np.random.randint(0, 4, n)
        weight   = np.clip(np.random.exponential(2.5, n), 0.1, 25)
        vtype    = np.random.randint(0, 3, n)
        hour     = np.random.randint(6, 23, n)
        stops    = np.clip(np.random.poisson(2, n), 1, 8)
        exp      = np.random.uniform(0.5, 10, n)
        is_cod   = np.random.randint(0, 2, n)
        fragile  = np.random.randint(0, 2, n)
        road_q   = np.random.uniform(3, 10, n)
        priority = np.random.randint(0, 3, n)
        area     = np.where(dist<5, 0, np.where(dist<12, 1, 2))

        spd = np.where(vtype==0, 28.0, np.where(vtype==1, 32.0, 22.0))
        spd = spd * (1 - traffic*0.13) * (1 - weather*0.07) * (0.7 + road_q/33)
        travel = (dist/spd)*60

        y = (travel + traffic*7.5 + weather*4.5 + stops*3.2 + is_cod*3
             + fragile*3.5 + weight*0.22 - exp*0.4 - priority*4.5
             + area*2.5 + np.random.normal(0, 4, n)).clip(7, 150)

        return pd.DataFrame({
            "distance_km":dist,"traffic_level":traffic,"weather":weather,
            "weight_kg":weight,"vehicle_type":vtype,"hour":hour,"prior_stops":stops,
            "experience":exp,"is_cod":is_cod,"is_fragile":fragile,
            "road_quality":road_q,"priority":priority,"area_type":area
        }), pd.Series(y)

    def _engineer(self, df):
        X = df.copy()
        X["log_dist"]        = np.log1p(X["distance_km"])
        X["dist_sq"]         = X["distance_km"] ** 2
        X["dist_x_traffic"]  = X["distance_km"] * X["traffic_level"]
        X["dist_x_weather"]  = X["distance_km"] * X["weather"]
        X["traffic_x_wx"]    = X["traffic_level"] * X["weather"]
        X["hour_sin"]        = np.sin(2*np.pi*X["hour"]/24)
        X["hour_cos"]        = np.cos(2*np.pi*X["hour"]/24)
        X["is_rush"]         = ((X["hour"]>=8)&(X["hour"]<=10)|(X["hour"]>=17)&(X["hour"]<=20)).astype(int)
        X["is_night"]        = ((X["hour"]>=21)|(X["hour"]<=7)).astype(int)
        X["complexity"]      = (X["traffic_level"]*2 + X["weather"]*1.5 + X["prior_stops"]*0.5
                                + X["is_fragile"]*1.5 + X["is_cod"]*0.5 + X["weight_kg"]*0.1)
        X["efficiency"]      = X["experience"] / (X["complexity"] + 1)
        X["adj_dist"]        = X["distance_km"] * (1 + X["traffic_level"]*0.1 + X["area_type"]*0.08)
        X["speed_factor"]    = 1 - X["traffic_level"]*0.13 - X["weather"]*0.07
        X["est_travel"]      = (X["distance_km"] / np.clip(
                                  (np.where(X["vehicle_type"]==0,28,np.where(X["vehicle_type"]==1,32,22))
                                   * X["speed_factor"]), 5, 50)) * 60
        X.drop(columns=["hour"], inplace=True)
        return X

    def train(self):
        if os.path.exists(MODEL_FILE):
            with open(MODEL_FILE,"rb") as f:
                d = pickle.load(f)
                self.model, self.features, self.metrics = d["model"], d["features"], d.get("metrics",{})
                self.is_trained = True
                print(f"✅ Model loaded — MAE:{self.metrics.get('mae','?')} R²:{self.metrics.get('r2','?')}")
                return
        print("🔧 Training ML model...")
        Xr, y = self._synth(4000)
        X = self._engineer(Xr)
        self.features = list(X.columns)
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model = Pipeline([
            ("sc", StandardScaler()),
            ("gb", GradientBoostingRegressor(n_estimators=400, learning_rate=0.04,
                                             max_depth=5, subsample=0.8, random_state=42))
        ])
        self.model.fit(Xtr, ytr)
        preds = self.model.predict(Xte)
        mae = round(mean_absolute_error(yte, preds), 2)
        r2  = round(r2_score(yte, preds), 4)
        acc = round(np.mean(np.abs(preds-yte)<=15)*100, 1)
        self.metrics = {"mae": mae, "r2": r2, "accuracy_15min": acc, "n_features": len(self.features)}
        self.is_trained = True
        with open(MODEL_FILE,"wb") as f:
            pickle.dump({"model":self.model,"features":self.features,"metrics":self.metrics}, f)
        print(f"✅ Model trained — MAE:{mae} min  R²:{r2}  Acc@15min:{acc}%")

    def predict(self, data: dict) -> dict:
        if not self.is_trained:
            return {"predicted_minutes": 30, "error": "model not ready"}
        try:
            vmap  = {"Bike":0,"Scooter":1,"Van":2,"Electric Bike":0}
            pmap  = {"NORMAL":0,"EXPRESS":1,"SAME_DAY":2}
            dist  = float(data.get("distance_km", 5))
            area  = 0 if dist<5 else (1 if dist<12 else 2)
            row = {
                "distance_km":  dist,
                "traffic_level":int(data.get("traffic_level", 1)),
                "weather":      int(data.get("weather", 0)),
                "weight_kg":    float(data.get("weight_kg", 1)),
                "vehicle_type": vmap.get(data.get("vehicle_type","Bike"),0),
                "hour":         int(data.get("hour", 14)),
                "prior_stops":  int(data.get("prior_stops", 2)),
                "experience":   float(data.get("experience", 3)),
                "is_cod":       int(data.get("is_cod", 0)),
                "is_fragile":   int(data.get("is_fragile", 0)),
                "road_quality": float(data.get("road_quality", 7)),
                "priority":     pmap.get(data.get("priority","NORMAL"),0),
                "area_type":    area,
            }
            df = pd.DataFrame([row])
            X  = self._engineer(df)
            for c in self.features:
                if c not in X.columns: X[c] = 0
            X = X[self.features]
            pred = float(self.model.predict(X)[0])
            pred = max(7, pred)
            margin = max(8, pred * 0.18)
            factors = self._explain(row, pred)
            return {
                "predicted_minutes": round(pred, 1),
                "range_min":  round(max(7, pred-margin), 1),
                "range_max":  round(pred+margin, 1),
                "confidence": "high" if pred<60 else "medium",
                "category":   ("⚡ Express" if pred<25 else "🕐 Standard" if pred<60 else "🕓 Extended"),
                "factors":    factors,
                "model_metrics": self.metrics,
                "eta_display": self._format_time(pred),
            }
        except Exception as e:
            return {"predicted_minutes": 35, "error": str(e)}

    def _format_time(self, mins):
        m = int(round(mins))
        if m < 60: return f"{m} min"
        return f"{m//60}h {m%60}m"

    def _explain(self, row, pred):
        factors = []
        if row["traffic_level"] == 2:
            factors.append({"icon":"🚦","name":"Heavy traffic","impact":"+12–15 min","severity":"high"})
        elif row["traffic_level"] == 1:
            factors.append({"icon":"🚦","name":"Moderate traffic","impact":"+5–8 min","severity":"medium"})
        if row["weather"] >= 3:
            factors.append({"icon":"⛈️","name":"Heavy rain","impact":"+12 min","severity":"high"})
        elif row["weather"] == 2:
            factors.append({"icon":"🌧️","name":"Rain","impact":"+6 min","severity":"medium"})
        if row["distance_km"] > 12:
            factors.append({"icon":"📍","name":"Long distance","impact":f"+{int(row['distance_km']*0.8)} min","severity":"low"})
        if row["is_cod"]:
            factors.append({"icon":"💵","name":"Cash on delivery","impact":"+3 min","severity":"low"})
        if row["is_fragile"]:
            factors.append({"icon":"📦","name":"Fragile item","impact":"+4 min","severity":"low"})
        if row["experience"] > 6:
            factors.append({"icon":"⭐","name":"Expert driver","impact":f"-{int(row['experience']*0.5)} min","severity":"positive"})
        if row["priority"] == 2:
            factors.append({"icon":"🚀","name":"Same-day priority","impact":"-6 min","severity":"positive"})
        return factors
