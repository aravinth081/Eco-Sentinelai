from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse   # ✅ ADDED
from contextlib import asynccontextmanager
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# --- Core Engines ---
from ai_engine import engine
from predictor import predictor
from impact_calculator import compute_impact

load_dotenv()

# Shared State
current_state = {
    "telemetry": {},
    "ai_decision": {},
    "forecast": {},
    "impact": {},
    "timeline": [],
    "last_update": None
}

# --- Firebase Safe Init ---
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    SERVICE_ACCOUNT_PATH = 'serviceAccountKey.json'

    if os.path.exists(SERVICE_ACCOUNT_PATH):
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
except Exception as e:
    print("Firebase disabled:", e)
    db = None


# --- CORE PIPELINE ---
def trigger_cognitive_pipeline(snapshot):
    zones = snapshot.get("zones", {})
    z0 = zones.get("zone_0", {})
    zw = z0.get("water", {})
    za = z0.get("air", {})

    pm25 = za.get("pm25", 15)
    co2 = za.get("co2", 400)
    ph = zw.get("ph", 7.2)
    turb = zw.get("turbidity", 2.0)
    ecoli = zw.get("ecoli", 0)

    predictor.push(pm25, co2, ph, turb)
    current_state["forecast"] = predictor.forecast(steps_ahead=10)

    affected = 1 if pm25 > 50 or ecoli > 20 else 0
    current_state["impact"] = compute_impact(pm25, co2, ph, turb, affected_zones=affected)

    decision = engine.analyze_telemetry(snapshot)
    current_state["ai_decision"] = decision

    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": f"Threat Level {decision.get('threat_level', 'LOW')}",
        "action": decision.get("ai_summary", "Monitoring")
    }

    current_state["timeline"].insert(0, event)
    if len(current_state["timeline"]) > 8:
        current_state["timeline"].pop()

    if db:
        try:
            db.collection("system_state").document("latest_decision").set(decision)
        except Exception as e:
            print("Firebase error:", e)


async def sync_with_firebase():
    if not db:
        return

    doc_ref = db.collection("system_state").document("city_snapshot")

    def on_snapshot(doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            data = doc.to_dict()
            if data:
                current_state["telemetry"] = data
                current_state["last_update"] = datetime.now().isoformat()
                trigger_cognitive_pipeline(data)

    doc_ref.on_snapshot(on_snapshot)


# --- FIXED LIFESPAN ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    print("EcoSentinel AI started")
    try:
        asyncio.create_task(sync_with_firebase())
    except:
        pass
    yield
    print("Shutdown complete")


# --- FASTAPI APP ---
app = FastAPI(
    title="EcoSentinel AI",
    version="2.0",
    lifespan=lifespan
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 IMPORTANT CHANGE HERE 👇
@app.get("/")
def root():
    return FileResponse("index.html")   # ✅ UI SHOW

# --- API ROUTES ---
@app.get("/api/state")
async def get_state():
    return current_state


@app.get("/api/telemetry")
async def get_telemetry():
    return current_state["telemetry"]


@app.get("/api/decision")
async def get_decision():
    return current_state["ai_decision"]


@app.post("/api/simulate")
async def simulate(body: dict = Body(...)):
    disaster_type = body.get("type", "UNKNOWN")

    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": f"SIMULATION: {disaster_type}",
        "action": "Injected"
    }

    current_state["timeline"].insert(0, event)

    return {"status": "ok"}


@app.post("/api/chat")
async def chat(body: dict = Body(...)):
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="No question")

    context = {
        "telemetry": current_state["telemetry"],
        "impact": current_state["impact"]
    }

    answer = engine.eco_copilot_chat(question, context)
    return {"answer": answer}


# --- STATIC FILES ---
app.mount("/static", StaticFiles(directory=".", html=True), name="static")
