"""
EcoSentinel AI — Self-Healing City Protocol
Generates a physical resource dispatch plan when thresholds are breached.
Simulates integration with city infrastructure APIs.
"""
from datetime import datetime, timedelta
import random

# ── Resource Fleet (simulated inventory) ──────────────────────────
FLEET = {
    "Air Scrubber Unit":    {"total": 8,  "deployed": 0, "eta_mins": 8},
    "Hazmat Response Team": {"total": 4,  "deployed": 0, "eta_mins": 12},
    "Mobile Medical Unit":  {"total": 6,  "deployed": 0, "eta_mins": 10},
    "Water Treatment Tank": {"total": 5,  "deployed": 0, "eta_mins": 15},
    "Traffic Drone":        {"total": 20, "deployed": 0, "eta_mins": 3},
    "Emergency Broadcast":  {"total": 1,  "deployed": 0, "eta_mins": 1},
}

def generate_protocol(decision: dict, snapshot: dict = None) -> dict:
    """
    Takes an AI decision dict and generates a physical
    Self-Healing Protocol with real resource dispatch orders and simulated API calls.
    """
    threat = decision.get("threat_level", "LOW")
    zones  = decision.get("affected_zones", [])
    cmds   = decision.get("department_commands", [])

    deployments = []
    fleet_state = {k: v.copy() for k, v in FLEET.items()}

    # Rule-based dispatch based on department commands
    dept_resource_map = {
        "TRAFFIC":      "Traffic Drone",
        "MEDICAL":      "Mobile Medical Unit",
        "ENVIRONMENT":  "Air Scrubber Unit",
        "WATER":        "Water Treatment Tank",
        "FIRE":         "Hazmat Response Team",
        "PUBLIC_SAFETY":"Emergency Broadcast",
        "MAYOR":        None,
    }

    now = datetime.utcnow()
    for cmd in cmds:
        dept = cmd.get("dept", "ENVIRONMENT")
        res_name = dept_resource_map.get(dept)
        if not res_name:
            continue
        res = fleet_state[res_name]
        available = res["total"] - res["deployed"]
        qty = 1 if threat in ("LOW", "MODERATE") else (2 if threat == "HIGH" else min(available, 3))
        qty = min(qty, available)
        if qty <= 0:
            continue
        res["deployed"] += qty
        eta = res["eta_mins"] + random.randint(-2, 4)
        arrival = (now + timedelta(minutes=eta)).strftime("%H:%M UTC")
        deployments.append({
            "resource":       res_name,
            "quantity":       qty,
            "destination":    zones[0] if zones else "City-Wide",
            "eta_mins":       eta,
            "arrival_time":   arrival,
            "status":         "DISPATCHED",
            "command_ref":    cmd.get("command", "")[:60],
        })

    # City Infrastructure Actions (simulated API calls)
    infra_actions = []
    if threat in ("CRITICAL", "CATASTROPHIC"):
        infra_actions = [
            {"system": "Traffic Control API",    "action": "POST /api/v2/routing/divert", "payload": {"zone": "Zone-A", "protocol": "emergency-lanes"}, "status": "HTTP 200 OK"},
            {"system": "Water SCADA",            "action": "PUT /api/v1/valve/RV-04", "payload": {"status": "CLOSED", "reserve": "ON"}, "status": "HTTP 200 OK"},
            {"system": "Ventilation Grid API",   "action": "POST /api/v3/ventilation/fans", "payload": {"target": "Industrial_Dist", "speed": 1.20}, "status": "HTTP 200 OK"},
            {"system": "Citizen Broadcast API",  "action": "POST /api/v1/sms/alert", "payload": {"audience": 234000, "msg": "SHELTER IN PLACE"}, "status": "HTTP 202 ACCEPTED"},
        ]
    elif threat == "HIGH":
        infra_actions = [
            {"system": "Traffic Control API",   "action": "PUT /api/v2/speed-limits", "payload": {"zone": "Zone-A", "modifier": 0.8}, "status": "HTTP 200 OK"},
            {"system": "Citizen Broadcast API", "action": "POST /api/v1/app/push", "payload": {"type": "HEALTH_ADVISORY"}, "status": "HTTP 202 ACCEPTED"},
        ]

    total_deployed = sum(d["quantity"] for d in deployments)
    fleet_summary = [
        {"resource": k, "available": v["total"] - v["deployed"], "deployed": v["deployed"]}
        for k, v in fleet_state.items()
    ]

    return {
        "protocol_id":       f"SHP-{now.strftime('%Y%m%d%H%M%S')}",
        "initiated_at":      now.isoformat() + "Z",
        "threat_level":      threat,
        "total_deployed":    total_deployed,
        "deployments":       deployments,
        "infrastructure_actions": infra_actions,
        "fleet_summary":     fleet_summary,
        "auto_resolved":     threat in ("LOW", "MODERATE"),
    }
