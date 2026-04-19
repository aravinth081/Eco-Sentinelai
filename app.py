 from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# --- Core Engines ---
from ai_engine import engine
from predictor import predictor
from impact_calculator import compute_impact

load_dotenv()

# Shared In-Memory State (Unified Brain State)
current_state = {
    "telemetry": {},
    "ai_decision": {},
    "forecast": {},
    "impact": {},
    "timeline": [],
    "last_update": None
}

# --- Firebase Initializer (Internal) ---
import firebase_admin
from firebase_admin import credentials, firestore

SERVICE_ACCOUNT_PATH = 'serviceAccountKey.json'
db = None

if os.path.exists(SERVICE_ACCOUNT_PATH):
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    db = firestore.client()

def trigger_cognitive_pipeline(snapshot):
    """The Advanced Multi-Agent Autonomous Pipeline (Explorer Thesis '26)"""
    zones = snapshot.get("zones", {})
    z0 = zones.get("zone_0", {})
    zw = z0.get("water", {})
    za = z0.get("air", {})

    pm25 = za.get("pm25", 15)
    co2 = za.get("co2", 400)
    ph = zw.get("ph", 7.2)
    turb = zw.get("turbidity", 2.0)
    ecoli = zw.get("ecoli", 0)

    # Agent 1: Prediction Engine (T+30m Forecast)
    predictor.push(pm25, co2, ph, turb)
    current_state["forecast"] = predictor.forecast(steps_ahead=10)

    # Agent 2: Impact & Economic Engine (Includes Agro & Population)
    affected = 1 if pm25 > 50 or ecoli > 20 else 0
    current_state["impact"] = compute_impact(pm25, co2, ph, turb, affected_zones=affected)

    # Agent 3: Commander AI (Decision, CV trigger, & Bio-Swarm)
    has_anomaly = any(
        z.get("air", {}).get("status") == "CRITICAL" or 
        z.get("water", {}).get("status") == "CRITICAL" or
        z.get("water", {}).get("ecoli", 0) > 40 or
        z.get("health") == "DRIFT_DETECTED"
        for z in zones.values()
    )

    if has_anomaly or not current_state.get("ai_decision"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Triggering Sentinel-Core AI Analysis...")
        decision = engine.analyze_telemetry(snapshot)
        current_state["ai_decision"] = decision
        
        # Multi-Tier Workflow Logging
        threat_level = decision.get('threat_level', 'LOW')
        event = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "event": f"Threat Level {threat_level} Declared",
            "action": decision.get("ai_summary", "Monitoring nominal parameters.")
        }
        current_state["timeline"].insert(0, event)
        if len(current_state["timeline"]) > 8: # Increased timeline buffer
            current_state["timeline"].pop()

        if db:
            try:
                db.collection("system_state").document("latest_decision").set(decision)
            except Exception as e:
                print(f"Error saving decision to Firebase: {e}")

async def sync_with_firebase():
    """Background task to keep local state synced with Firestore."""
    global db
    if not db:
        return
    
    print("Background Sync: READY")
    doc_ref = db.collection("system_state").document("city_snapshot")
    
    def on_snapshot(doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            data = doc.to_dict()
            if data:
                current_state["telemetry"] = data
                current_state["last_update"] = datetime.now().isoformat()
                trigger_cognitive_pipeline(data)

    doc_ref.on_snapshot(on_snapshot)

# --- FASTAPI LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("EcoSentinel API v5 | Ultra-Cognitive Brain Online")
    asyncio.create_task(sync_with_firebase())
    yield
    # Shutdown logic
    print("EcoSentinel API shutting down...")

app = FastAPI(title="EcoSentinel AI - Cognitive Brain", version="2.0.0", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ENDPOINTS ---

@app.get("/api/state")
async def get_full_state():
    """Returns the entire unified brain state for the UI"""
    return current_state

@app.get("/api/telemetry")
async def get_telemetry():
    """Legacy Endpoint for raw telemetry"""
    return current_state["telemetry"]

@app.get("/api/decision")
async def get_latest_decision():
    """Legacy Endpoint for AI Decision"""
    return current_state["ai_decision"]

@app.post("/api/simulate")
async def inject_disaster(body: dict = Body(...)):
    """Disaster Simulation Engine (Triggers UI logic)"""
    disaster_type = body.get("type")
    
    # Generate contextual timeline events based on the disaster type
    action_text = "Injecting critical spikes..."
    if disaster_type == 'SMOG':
        action_text = "Orbital CV engaged. Simulating industrial emission spike."
    elif disaster_type == 'BIO':
        action_text = "Simulating pathogen leak. Prepping Bio-Bot Swarm."

    event = {
        "time": datetime.now().strftime("%H:%M:%S"), 
        "event": f"MANUAL OVERRIDE: {disaster_type}", 
        "action": action_text
    }
    current_state["timeline"].insert(0, event)
    if len(current_state["timeline"]) > 8:
        current_state["timeline"].pop()
    
    return {"status": "Disaster injected", "type": disaster_type}

@app.post("/api/chat")
async def chat_with_copilot(body: dict = Body(...)):
    """Eco-Copilot NLP endpoint (Edge & Cloud routing)"""
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="No question provided")
    
    # Passing telemetry, impact, and timeline to the AI context
    context = {
        "telemetry": current_state["telemetry"], 
        "impact": current_state["impact"],
        "recent_events": current_state["timeline"][:3] # Give AI memory of what just happened
    }
    answer = engine.eco_copilot_chat(question, context)
    return {"answer": answer}

@app.get("/api/infrastructure")
async def get_infrastructure_status():
    """Aggregated view of all auto-actuated infrastructure."""
    zones = current_state["telemetry"].get("zones", {})
    actuation_state = {}
    for zid, zdata in zones.items():
        actuation_state[zid] = zdata.get("infrastructure", {})
    
    return {
        "timestamp": datetime.now().isoformat(),
        "infrastructure": actuation_state,
        "autonomous_mode": True
    }

# --- STATIC FILES (mounted last so it doesn't interfere with API routes) ---
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Run on port 8000
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)