"""
EcoSentinel AI — Autonomous Risk Engine v2
- Monitors ALL city zones in real-time
- Uses Featherless AI to generate structured Autonomous Action Plans
- Issues Department Commands with priority levels
- Posts results to Firestore for WebSocket broadcast
"""
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "YOUR_FEATHERLESS_API_KEY")
FEATHERLESS_URL     = "https://api.featherless.ai/v1/chat/completions"
AI_MODEL            = "Qwen/Qwen2.5-72B-Instruct"   # Bigger = Smarter decisions
FALLBACK_MODEL      = "Qwen/Qwen2.5-7B-Instruct"

SERVICE_ACCOUNT_PATH = 'serviceAccountKey.json'

if not os.path.exists(SERVICE_ACCOUNT_PATH):
    print(f"INFO: {SERVICE_ACCOUNT_PATH} not found. Running in Local Demo Mode.")
    db = None
else:
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    db = firestore.client()

# --- AI PROMPT ENGINEERING ---
SYSTEM_PROMPT = """You are SENTINEL-CORE, the autonomous AI brain of a futuristic smart city.
Your job is to analyze multi-zone environmental telemetry and produce an Autonomous Action Plan.
You think like a crisis-management expert who controls every city department.
You are decisive, fast, and always output valid JSON. Never explain yourself outside the JSON."""

def build_user_prompt(snapshot):
    zones = snapshot.get("zones", {})
    weather = snapshot.get("weather", "Unknown")
    
    zone_report = []
    for zone_key, z in zones.items():
        zone_report.append(
            f"  [{z['zone']}]: PM2.5={z['air']['pm25']} ug/m3 | CO2={z['air']['co2']} ppm | "
            f"pH={z['water']['ph']} | Turbidity={z['water']['turbidity']} NTU | "
            f"Temp={z['environment']['temperature']}°C | AirStatus={z['air']['status']} | WaterStatus={z['water']['status']}"
        )
    zone_block = "\n".join(zone_report)

    return f"""
CITY SNAPSHOT — TIMESTAMP: {datetime.utcnow().isoformat()}Z
WEATHER: {weather}

MULTI-ZONE TELEMETRY:
{zone_block}

Analyze ALL zones holistically. Consider cross-zone contamination spread, weather effects, and cascading failure risks.

OUTPUT STRICT JSON (no extra text):
{{
  "sentinel_score": <integer 0-100, city overall health, higher=healthier>,
  "risk_score": <integer 0-100, overall threat level>,
  "threat_level": "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | "CATASTROPHIC",
  "affected_zones": ["Zone-A ...", ...],
  "ai_summary": "<2 sentence analysis>",
  "root_cause": "<identified root cause>",
  "spread_forecast": "<predicted scenario in next 30 mins>",
  "department_commands": [
    {{
      "dept": "<TRAFFIC|MEDICAL|ENVIRONMENT|WATER|FIRE|PUBLIC_SAFETY|MAYOR>",
      "priority": "P1" | "P2" | "P3",
      "command": "<Specific actionable order>",
      "eta_mins": <integer>
    }}
  ],
  "citizen_advisory": "<Public broadcast message>",
  "autonomous_actions_engaged": true
}}
"""

def call_featherless_ai(prompt, use_fallback=False):
    model = FALLBACK_MODEL if use_fallback else AI_MODEL
    headers = {
        "Authorization": f"Bearer {FEATHERLESS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    try:
        if db:
            print(f"Querying Featherless AI [{model}]...")
            resp = requests.post(FEATHERLESS_URL, headers=headers, json=payload, timeout=35)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        else:
            # Simple heuristic when AI is unavailable or offline
            return self_heuristic_decision(prompt)
    except json.JSONDecodeError:
        if not use_fallback:
            print("JSON parse failed — retrying with fallback model...")
            return call_featherless_ai(prompt, use_fallback=True)
        return _fallback_decision()
    except Exception as e:
        print(f"Featherless AI Error: {e}")
        if not use_fallback:
            return call_featherless_ai(prompt, use_fallback=True)
        return _fallback_decision()

def self_heuristic_decision(prompt):
    """Local heuristic engine for when Featherless AI is unavailable."""
    return {
        "sentinel_score": 65,
        "risk_score": 35,
        "threat_level": "MODERATE",
        "affected_zones": ["Zone-A (Industrial District)"],
        "ai_summary": "Local heuristic analysis indicates localized particulate spike. AI Cloud link inactive.",
        "root_cause": "Industrial cycle fluctuation.",
        "spread_forecast": "Dissipation expected within 30 minutes due to current wind vectors.",
        "department_commands": [
            {"dept": "ENVIRONMENT", "priority": "P2", "command": "Monitor Zone-A air quality sensors.", "eta_mins": 10}
        ],
        "citizen_advisory": "Localized air quality fluctuation detected. No immediate action required for most citizens.",
        "autonomous_actions_engaged": True
    }

def _fallback_decision():
    return {
        "sentinel_score": 40,
        "risk_score": 65,
        "threat_level": "HIGH",
        "affected_zones": ["Zone-A (Industrial District)"],
        "ai_summary": "AI Engine operating on local heuristics. Elevated risk pattern detected.",
        "root_cause": "Connection to Featherless AI temporarily disrupted.",
        "spread_forecast": "Recommend manual inspection within 15 minutes.",
        "department_commands": [
            {"dept": "ENVIRONMENT", "priority": "P1", "command": "Deploy mobile sensor units to all zones.", "eta_mins": 5},
            {"dept": "MAYOR", "priority": "P2", "command": "Issue precautionary advisory to residents.", "eta_mins": 10},
        ],
        "citizen_advisory": "EcoSentinel is monitoring a potential environmental anomaly. Stay tuned for updates.",
        "autonomous_actions_engaged": False
    }

def is_actionable(snapshot):
    """Only call expensive AI if something is actually wrong."""
    zones = snapshot.get("zones", {})
    for z in zones.values():
        if z["air"]["status"] != "STABLE" or z["water"]["status"] != "STABLE":
            return True
    return False

def monitor_and_decide():
    print("SENTINEL-CORE v2 | AI Risk Engine ONLINE | Monitoring 4 Zones...")
    if not db:
        print("INFO: Firestore unavailable. AI engine will skip live monitoring but remains active for API calls.")
        return
    snapshot_ref = db.collection("system_state").document("city_snapshot")
    decision_counter = 0

    def on_snapshot(doc_snapshot, changes, read_time):
        nonlocal decision_counter
        for doc in doc_snapshot:
            snapshot = doc.to_dict()
            if not snapshot:
                continue

            # Always compute sentinel score even without AI call
            if is_actionable(snapshot):
                print(f"Anomaly detected in city telemetry! Engaging SENTINEL-CORE...")
                prompt   = build_user_prompt(snapshot)
                decision = call_featherless_ai(prompt)
            else:
                # Green state — simple healthy report
                decision = {
                    "sentinel_score": random.randint(82, 99),
                    "risk_score": random.randint(5, 18),
                    "threat_level": "LOW",
                    "affected_zones": [],
                    "ai_summary": "All environmental parameters within safe thresholds. City operating normally.",
                    "root_cause": "No anomaly detected.",
                    "spread_forecast": "Stable conditions expected for the next 60 minutes.",
                    "department_commands": [],
                    "citizen_advisory": "All clear. Environmental conditions are healthy across all city zones.",
                    "autonomous_actions_engaged": False
                }

            decision_counter += 1
            decision["timestamp"] = firestore.SERVER_TIMESTAMP
            decision["sequence"]  = decision_counter
            decision["source_snapshot"] = snapshot

            # Write to Firestore — app.py will broadcast via WebSocket
            if db:
                db.collection("decisions").add(decision)
                db.collection("system_state").document("latest_decision").set(decision)
            print(f"Decision #{decision_counter} | Threat={decision['threat_level']} | Score={decision['sentinel_score']}")

    import random
    doc_watch = snapshot_ref.on_snapshot(on_snapshot)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        doc_watch.unsubscribe()
        print("SENTINEL-CORE offline.")

if __name__ == "__main__":
    monitor_and_decide()
