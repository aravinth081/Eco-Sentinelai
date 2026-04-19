import os
import requests
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SentinelAI:
    def __init__(self):
        # Default to Featherless AI
        self.provider = os.getenv("AI_PROVIDER", "featherless").lower()
        self.api_key = os.getenv("FEATHERLESS_API_KEY", "")
        self.api_url = os.getenv("AI_API_ENDPOINT", "https://api.featherless.ai/v1/chat/completions")
        
        if self.provider == "antigravity":
            # For Antigravity swap (if implemented as a separate endpoint or model name)
            self.model_name = os.getenv("ANTIGRAVITY_MODEL", "antigravity-v1")
        else:
            self.model_name = os.getenv("FEATHERLESS_MODEL", "Qwen/Qwen2.5-72B-Instruct")

    def build_system_prompt(self):
        return (
            "You are SENTINEL-CORE, the autonomous AI brain of a futuristic smart city. "
            "Your mandate is to analyze environmental telemetry and execute autonomous infrastructure protocols. "
            "You must output valid JSON only. Never explain yourself outside the JSON. "
            "You control the following departments: TRAFFIC, WATER, ENVIRONMENT, PUBLIC_SAFETY."
        )

    def generate_audit_hash(self, decision_json):
        """Creates an immutable cryptographic hash for AI accountability."""
        # Remove any existing hash to ensure consistency if re-hashing
        temp_dict = {k: v for k, v in decision_json.items() if k != "audit_hash"}
        decision_string = json.dumps(temp_dict, sort_keys=True)
        return hashlib.sha256(decision_string.encode('utf-8')).hexdigest()

    def analyze_telemetry(self, snapshot):
        """
        Main reasoning loop for anomaly detection and decision making.
        """
        user_prompt = f"""
        CITY SNAPSHOT - TIMESTAMP: {datetime.utcnow().isoformat()}Z
        DATA: {json.dumps(snapshot)}

        Analyze this telemetry holistically. If any value (PM2.5 > 100, Turbidity > 20, pH < 5 or > 9, or E.coli > 40) is critical:
        1. Generate autonomous infrastructure commands (e.g., 'Close Valve RV-102', 'Reroute Sector 7 Traffic').
        2. Generate a drone dispatch manifest with GPS coordinates based on the critical zone location.
        3. Forecast spread based on wind direction/speed.
        4. Calculate a unified Risk Score (0-100).
        5. If 'health' status indicates 'DRIFT_DETECTED', issue a sensor calibration order.

        OUTPUT JSON STRUCTURE:
        {{
          "risk_score": 0-100,
          "threat_level": "LOW|MODERATE|HIGH|CRITICAL",
          "affected_zones": ["Zone Name"],
          "infrastructure_commands": [
             {{"dept": "WATER|TRAFFIC", "action": "CLOSE|REROUTE", "details": "Specific target"}}
          ],
          "biosensor_analysis": "Explanation of E.coli or Microplastic levels",
          "calibration_orders": ["Order 1 if drift detected, else empty array"],
          "drone_dispatch": {{
             "active": true/false,
             "manifest_id": "DS-XXXX",
             "coordinates": {{"lat": float, "lng": float}},
             "reason": "Description"
          }},
          "spread_forecast": {{
             "next_affected_sector": "Sector Name",
             "eta_mins": int
          }},
          "ai_summary": "1 sentence explanation"
        }}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.build_system_prompt()},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1, # Lowered for more consistent JSON output
            "max_tokens": 1024
        }

        try:
            # Check if API key exists; otherwise return mock for demo
            if not self.api_key or "YOUR_FEATHERLESS_API_KEY" in self.api_key:
                 return self._get_mock_decision(snapshot)

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            raw_content = response.json()["choices"][0]["message"]["content"]
            
            # Clean possible markdown formatting
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()
                
            decision_data = json.loads(raw_content)
            
            # --- NEW: Add Immutable Audit Hash ---
            decision_data["audit_hash"] = self.generate_audit_hash(decision_data)
            
            return decision_data
            
        except Exception as e:
            print(f"AI Engine Error: {e}")
            return self._get_mock_decision(snapshot)

    def eco_copilot_chat(self, question, context):
        """
        NLP Interface for City Engineers.
        """
        system_msg = (
            "You are the Eco-Copilot, a professional environmental AI assistant. "
            "Use the provided city context to answer the engineer's question precisely."
        )
        
        user_msg = f"CITY CONTEXT: {json.dumps(context)}\n\nQUESTION: {question}"

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct", # Smaller/faster model for chat
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.5,
            "max_tokens": 250
        }

        try:
            if not self.api_key or "YOUR_FEATHERLESS_API_KEY" in self.api_key:
                 return "I'm currently in Demo Mode. To talk to me properly, please configure your API Key. Based on local data, the city status is STABLE."

            response = requests.post(self.api_url, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Eco-Copilot is temporarily offline: {str(e)}"

    def _get_mock_decision(self, snapshot):
        # Fallback if API fails or for demo without key
        is_critical = any(z['air']['pm25'] > 100 or z['water']['turbidity'] > 20 or z.get('water', {}).get('ecoli', 0) > 40 for z in snapshot.get('zones', {}).values())
        
        if not is_critical:
            decision = {
                "risk_score": 12,
                "threat_level": "LOW",
                "affected_zones": [],
                "infrastructure_commands": [],
                "biosensor_analysis": "Microbial levels within safe limits.",
                "calibration_orders": [],
                "drone_dispatch": {"active": False},
                "spread_forecast": {"next_affected_sector": "None", "eta_mins": 0},
                "ai_summary": "City metrics are within safe operational limits."
            }
            decision["audit_hash"] = self.generate_audit_hash(decision)
            return decision
        
        decision = {
            "risk_score": 88,
            "threat_level": "CRITICAL",
            "affected_zones": ["Industrial Sector A"],
            "infrastructure_commands": [
                {"dept": "WATER", "action": "CLOSE", "details": "Main Intake Valve RV-01"},
                {"dept": "TRAFFIC", "action": "REROUTE", "details": "Grid North-East Bypass"}
            ],
            "biosensor_analysis": "Elevated E.coli detected indicating potential bio-hazard leak.",
            "calibration_orders": ["Reset Zone-A PM2.5 Sensor Due to Drift"],
            "drone_dispatch": {
                "active": True,
                "manifest_id": "DS-9912",
                "coordinates": {"lat": 40.7128, "lng": -74.0060},
                "reason": "Detection of critical anomalies."
            },
            "spread_forecast": {
                "next_affected_sector": "Zone-B Downtown",
                "eta_mins": 15
            },
            "ai_summary": "Critical spike detected. Automated containment protocols engaged."
        }
        decision["audit_hash"] = self.generate_audit_hash(decision)
        return decision

engine = SentinelAI()