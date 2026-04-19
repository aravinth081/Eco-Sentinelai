import time
import random
import math
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
SERVICE_ACCOUNT_PATH = 'serviceAccountKey.json'
db = None

if os.path.exists(SERVICE_ACCOUNT_PATH):
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Realtime Sync: ON")
else:
    print("Firebase Config not found. Simulator running in Local Mirror Mode.")

# --- CITY ZONES & STATES ---
ZONES = {
    "zone_0": {"name": "Industrial District", "lat": 40.7306, "lng": -73.9352},
    "zone_1": {"name": "Downtown Core",       "lat": 40.7128, "lng": -74.0060},
    "zone_2": {"name": "Riverside Sector",    "lat": 40.7484, "lng": -73.9857},
    "zone_3": {"name": "Airport Corridor",    "lat": 40.6413, "lng": -73.7781},
}

# Initial State
t = 0
wind_speed = 12.0
wind_direction = "NE"

def generate_telemetry():
    global t, wind_speed, wind_direction
    t += 1
    
    # Simulate gradual wind changes
    wind_speed = max(5, min(45, wind_speed + random.uniform(-2, 2)))
    wind_direction = random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]) if t % 10 == 0 else wind_direction

    zones_data = {}
    for zid, zcfg in ZONES.items():
        # --- NEW: Sensor Drift Simulation (Needs AI Calibration) ---
        drift = random.uniform(-8, 8) if random.random() < 0.05 else 0

        # Realistic Sine-wave fluctuations + GAUSS noise
        wave = math.sin(t * 0.1) * 10
        
        pm25 = 15 + wave + random.gauss(0, 5) + drift
        co2 = 400 + wave * 5 + random.gauss(0, 20)
        ph = 7.0 + math.sin(t * 0.05) * 0.5 + random.gauss(0, 0.1)
        turbidity = 2.0 + abs(math.sin(t * 0.08)) * 3 + random.gauss(0, 0.5)
        
        # --- NEW: Microbial Biosensors ---
        ecoli = max(0, 1.5 + math.sin(t * 0.03) + random.gauss(0, 0.5))
        microplastics = max(5, 10 + random.gauss(0, 1.5))

        # --- UPDATED: Scenario Injections (Air vs Bio-Hazard) ---
        spike_active = False
        spike_type = "NONE"
        
        if random.random() < 0.06:  # 6% chance for a disaster event
            spike_active = True
            if random.random() > 0.5:
                # Scenario 1: Industrial Smog Spike
                pm25 = random.uniform(180, 450)
                co2 = random.uniform(2500, 5500)
                spike_type = "INDUSTRIAL_SMOG"
            else:
                # Scenario 2: Bio-Hazard Water Leak
                turbidity = random.uniform(35, 90)
                ecoli = random.uniform(60, 250)  # Lethal pathogen level
                ph = random.uniform(3.0, 5.0)    # Highly acidic
                spike_type = "BIO_HAZARD_LEAK"

        zones_data[zid] = {
            "name": zcfg["name"],
            "gps": {"lat": zcfg["lat"], "lng": zcfg["lng"]},
            "air": {
                "pm25": round(max(0, pm25), 1),
                "co2": round(max(300, co2), 1),
                "status": "CRITICAL" if pm25 > 100 else "STABLE"
            },
            "water": {
                "ph": round(max(0, min(14, ph)), 2),
                "turbidity": round(max(0, turbidity), 1),
                "ecoli": round(ecoli, 2),             # ADDED BIOSENSOR
                "plastics": round(microplastics, 2),  # ADDED BIOSENSOR
                "status": "CRITICAL" if turbidity > 20 or ecoli > 40 else "STABLE"
            },
            "infrastructure": {
                "water_valve": "OPEN",
                "power_grid": "NOMINAL",
                "traffic_status": "NORMAL"
            },
            "health": "DRIFT_DETECTED" if drift != 0 else "OPTIMAL", # ADDED CALIBRATION METRIC
            "spike": spike_active,
            "spike_type": spike_type
        }

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "weather": {
            "wind_speed": round(wind_speed, 1),
            "wind_direction": wind_direction,
            "temp": round(22 + math.sin(t * 0.02) * 5, 1)
        },
        "zones": zones_data
    }
    
    return snapshot

def run_simulator():
    print("EcoSentinel Ultra-Simulator v4 | BIOSENSORS & DRIFT ONLINE 🔥")
    while True:
        data = generate_telemetry()
        
        # Log to console
        crit_zones = [z['name'] for z in data['zones'].values() if z['air']['status'] == 'CRITICAL' or z['water']['status'] == 'CRITICAL']
        status_msg = f"CRITICAL: {', '.join(crit_zones)}" if crit_zones else "Status: NOMINAL"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_msg} | Wind: {data['weather']['wind_speed']} km/h {data['weather']['wind_direction']}")

        if db:
            try:
                # Update Firestore with the new complex payload
                db.collection("system_state").document("city_snapshot").set(data)
                
                # Optionally keep the historical log, but snapshot is enough for the UI
                # db.collection("logs").add(data) 
            except Exception as e:
                print(f"Firebase Update Failed: {e}")

        time.sleep(3)

if __name__ == "__main__":
    run_simulator()