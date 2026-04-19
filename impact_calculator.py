"""
EcoSentinel AI — Impact Calculator
Computes real-world human and economic impact
from raw environmental sensor readings.
"""

import math

# ─── City Demographics (configurable) ────────────────────────────
CITY_POPULATION = 2_400_000
VULNERABLE_FRACTION = 0.22   # children + elderly
AVG_HEALTHCARE_COST_PER_PERSON = 340   # USD per episode
AVG_PRODUCTIVITY_LOSS_PER_PERSON = 185  # USD per day
INDUSTRIAL_ZONE_FRACTION = 0.08

# ─── WHO / EPA Thresholds ─────────────────────────────────────────
PM25_SAFE = 15.0
CO2_SAFE  = 800.0
PH_SAFE   = (6.5, 8.5)
TURB_SAFE = 1.0  # drinking water

def compute_impact(pm25, co2, ph, turbidity, affected_zones=1, total_zones=4):
    """
    Returns a dict containing:
      - citizens_at_risk (int)
      - vulnerable_at_risk (int)
      - health_index (0-100, higher = worse)
      - economic_damage_usd (int, per day estimate)
      - carbon_credit_balance (relative score)
      - water_safety_class ("A-Safe","B-Caution","C-Unsafe","D-Hazardous")
      - air_quality_index (AQI estimate)
      - recovery_time_hours (estimated city recovery)
    """
    zone_fraction = affected_zones / total_zones

    # ── AQI Linear Calculation (simplified EPA breakpoints) ──────
    if pm25 <= 12:      aqi = _map(pm25, 0, 12, 0, 50)
    elif pm25 <= 35.4:  aqi = _map(pm25, 12, 35.4, 51, 100)
    elif pm25 <= 55.4:  aqi = _map(pm25, 35.4, 55.4, 101, 150)
    elif pm25 <= 150.4: aqi = _map(pm25, 55.4, 150.4, 151, 200)
    elif pm25 <= 250.4: aqi = _map(pm25, 150.4, 250.4, 201, 300)
    else:               aqi = _map(pm25, 250.4, 500, 301, 500)
    aqi = round(aqi)

    # ── Population at Risk ───────────────────────────────────────
    # Based on AQI and zone coverage
    if aqi < 51:      air_risk_fraction = 0.01
    elif aqi < 101:   air_risk_fraction = 0.05
    elif aqi < 151:   air_risk_fraction = 0.20
    elif aqi < 201:   air_risk_fraction = 0.45
    elif aqi < 301:   air_risk_fraction = 0.75
    else:             air_risk_fraction = 1.00

    water_risk_fraction = 0.0
    if ph < 5.5 or ph > 9.5 or turbidity > 40:
        water_risk_fraction = 0.6
    elif ph < 6.0 or ph > 9.0 or turbidity > 10:
        water_risk_fraction = 0.25
    elif turbidity > TURB_SAFE:
        water_risk_fraction = 0.08

    combined_risk = 1 - (1 - air_risk_fraction * zone_fraction) * (1 - water_risk_fraction * zone_fraction)
    citizens_at_risk   = int(CITY_POPULATION * combined_risk)
    vulnerable_at_risk = int(citizens_at_risk * VULNERABLE_FRACTION)

    # ── Economic Damage ──────────────────────────────────────────
    healthcare_cost    = vulnerable_at_risk * AVG_HEALTHCARE_COST_PER_PERSON
    productivity_loss  = citizens_at_risk * AVG_PRODUCTIVITY_LOSS_PER_PERSON * 0.15
    infrastructure_cost = 50_000 * (1 + aqi / 100)  # Emergency mobilization
    economic_damage = int(healthcare_cost + productivity_loss + infrastructure_cost)

    # ── Health Composite Index ───────────────────────────────────
    pm25_score = min(1.0, max(0, (pm25 - PM25_SAFE) / (250 - PM25_SAFE)))
    co2_score  = min(1.0, max(0, (co2 - CO2_SAFE) / (3000 - CO2_SAFE)))
    ph_dev     = max(0, PH_SAFE[0] - ph) + max(0, ph - PH_SAFE[1])
    ph_score   = min(1.0, ph_dev / 5.0)
    turb_score = min(1.0, max(0, turbidity / 80))
    health_index = round((pm25_score * 0.35 + co2_score * 0.25 + ph_score * 0.2 + turb_score * 0.2) * 100, 1)

    # ── Water Safety Class ───────────────────────────────────────
    if turbidity <= 1.0 and 6.5 <= ph <= 8.5:
        water_class = "A — Safe"
    elif turbidity <= 5.0 and 6.0 <= ph <= 9.0:
        water_class = "B — Caution"
    elif turbidity <= 20 or ph < 5.5 or ph > 9.5:
        water_class = "C — Unsafe"
    else:
        water_class = "D — Hazardous"

    # ── Carbon Credit Balance ─────────────────────────────────────
    # Penalty for excess CO2 and PM2.5 above safe thresholds
    co2_excess = max(0, co2 - CO2_SAFE)
    pm_excess  = max(0, pm25 - PM25_SAFE)
    carbon_penalty = (co2_excess / 100) + (pm_excess / 10)
    carbon_credit = round(max(-100, 100 - carbon_penalty * zone_fraction), 1)

    # ── Recovery Time Estimate ───────────────────────────────────
    base_recovery = 2
    recovery_time = round(base_recovery + (health_index / 100) * 46)   # 2–48 hours

    # ── Hospital Load Prediction (Advanced) ──────────────────────
    # Probability of ICU admission for vulnerable population
    icu_rate = 0.05 if health_index > 80 else (0.02 if health_index > 50 else 0.005)
    hospital_load = int(vulnerable_at_risk * icu_rate)

    # ── Carbon Market Simulation ──────────────────────────────────
    market_price = 45.0 + math.sin(pm25/10) * 15 # Volatile pricing
    carbon_valuation = round(carbon_credit * market_price, 2)

    return {
        "citizens_at_risk":    citizens_at_risk,
        "vulnerable_at_risk":  vulnerable_at_risk,
        "health_index":        health_index,
        "aqi":                 aqi,
        "economic_damage_usd": economic_damage,
        "carbon_credit":       carbon_credit,
        "carbon_valuation":    carbon_valuation,
        "hospital_load":       hospital_load,
        "water_safety_class":  water_class,
        "air_risk_fraction":   round(air_risk_fraction * 100, 1),
        "water_risk_fraction": round(water_risk_fraction * 100, 1),
        "recovery_time_hours": recovery_time,
    }

def _map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
