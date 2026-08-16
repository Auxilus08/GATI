"""
Composite Junction Risk Index (JRI).
Calculates an auditable, multi-factor safety & congestion risk score (0 to 100) for municipal traffic management.
Factors:
1. Queue Saturation Ratio (0-40 pts)
2. Approach Imbalance & Cross-traffic Starvation (0-25 pts)
3. Average Speed Drop (0-20 pts)
4. Emergency Vehicle Presence & Delay (0-15 pts)
"""
from typing import Dict, Any


class JunctionRiskEngine:
    """Calculates real-time 0-100 Risk Index for traffic police operators."""

    @staticmethod
    def calculate_risk(
        total_pcu: float,
        saturation_pcu: float = 80.0,
        max_approach_pcu: float = 0.0,
        min_approach_pcu: float = 0.0,
        avg_speed_kmh: float = 35.0,
        emergency_active: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluate composite risk score and category.
        """
        # 1. Saturation Factor (max 40 pts)
        sat_ratio = min(1.0, total_pcu / max(1.0, saturation_pcu))
        sat_score = sat_ratio * 40.0

        # 2. Imbalance Factor (max 25 pts)
        imbalance = max(0.0, max_approach_pcu - min_approach_pcu)
        imbalance_score = min(25.0, (imbalance / 20.0) * 25.0)

        # 3. Speed Degradation Factor (max 20 pts)
        # Assumes normal free-flow is 40 km/h
        speed_score = max(0.0, min(20.0, ((40.0 - max(0.0, avg_speed_kmh)) / 40.0) * 20.0))

        # 4. Emergency Factor (max 15 pts)
        emergency_score = 15.0 if emergency_active else 0.0

        total_risk = min(100.0, sat_score + imbalance_score + speed_score + emergency_score)

        if total_risk >= 75.0:
            category = "HIGH_RISK"
            action = "Police Intervention / Green Wave Recommended"
        elif total_risk >= 45.0:
            category = "MODERATE"
            action = "Adaptive Phase Extension Active"
        else:
            category = "OPTIMAL"
            action = "Normal Max-Pressure Operation"

        return {
            "risk_score": round(total_risk, 1),
            "category": category,
            "recommended_action": action,
            "breakdown": {
                "saturation": round(sat_score, 1),
                "imbalance": round(imbalance_score, 1),
                "speed_drop": round(speed_score, 1),
                "emergency": round(emergency_score, 1),
            },
        }
