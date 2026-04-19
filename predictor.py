"""
EcoSentinel AI — Predictive Trend Engine
Uses rolling-window linear regression on sensor history
to forecast values 30 minutes into the future.
No heavy ML dependencies — pure Python math.
"""
import math
from collections import deque

WINDOW = 20  # Number of readings to use for regression

class TrendPredictor:
    def __init__(self):
        self.buffers = {
            "pm25": deque(maxlen=WINDOW),
            "co2":  deque(maxlen=WINDOW),
            "ph":   deque(maxlen=WINDOW),
            "turb": deque(maxlen=WINDOW),
        }

    def push(self, pm25, co2, ph, turb):
        self.buffers["pm25"].append(pm25)
        self.buffers["co2"].append(co2)
        self.buffers["ph"].append(ph)
        self.buffers["turb"].append(turb)

    def _linreg(self, values):
        """Simple OLS linear regression, returns (slope, intercept)."""
        n = len(values)
        if n < 3:
            return 0.0, values[-1] if values else 0.0
        xs = list(range(n))
        ys = list(values)
        xm = sum(xs) / n
        ym = sum(ys) / n
        num = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
        den = sum((x - xm) ** 2 for x in xs)
        slope = num / den if den else 0.0
        intercept = ym - slope * xm
        return slope, intercept

    def forecast(self, steps_ahead=10):
        """
        Forecast values `steps_ahead` ticks into the future.
        At 3s/tick, 10 steps = 30 seconds ahead.
        Returns dict with forecasted values and trend directions.
        """
        result = {}
        for key, buf in self.buffers.items():
            if not buf:
                result[key] = {"forecast": None, "trend": "stable", "confidence": 0}
                continue
            slope, intercept = self._linreg(buf)
            future_x = len(buf) + steps_ahead
            forecast_val = slope * future_x + intercept

            # Clamp to realistic ranges
            clamps = {
                "pm25": (0, 500),
                "co2":  (350, 5000),
                "ph":   (0, 14),
                "turb": (0, 100),
            }
            lo, hi = clamps.get(key, (0, 9999))
            forecast_val = max(lo, min(hi, forecast_val))

            # Trend direction
            pct_change = (slope * steps_ahead / (buf[-1] + 1e-9)) * 100
            if pct_change > 5:   trend = "rising"
            elif pct_change < -5: trend = "falling"
            else:                 trend = "stable"

            # Confidence (R² proxy)
            n = len(buf)
            if n > 3:
                ys = list(buf)
                ym = sum(ys) / n
                ss_res = sum((y - (slope * i + intercept)) ** 2 for i, y in enumerate(ys))
                ss_tot = sum((y - ym) ** 2 for y in ys)
                r2 = 1 - ss_res / (ss_tot + 1e-9)
                confidence = round(max(0, min(1, r2)) * 100, 1)
            else:
                confidence = 50

            result[key] = {
                "current":    round(buf[-1], 2),
                "forecast":   round(forecast_val, 2),
                "trend":      trend,
                "slope":      round(slope, 4),
                "confidence": confidence,
                "pct_change": round(pct_change, 1),
            }
        return result


# Singleton for use in app.py
predictor = TrendPredictor()
