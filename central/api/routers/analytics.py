"""
City-wide analytics, predictive congestion forecasts, and risk metrics API.
"""
from typing import Dict, Any, List
from fastapi import APIRouter
from central.api.routers.telemetry import latest_telemetry, forecaster, anomaly_detector

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/city-summary")
async def get_city_summary():
    """Aggregate real-time metrics across all active junctions."""
    total_active_junctions = len(latest_telemetry)
    total_city_pcu = 0.0
    high_risk_count = 0
    emergency_active_count = 0

    for jid, data in latest_telemetry.items():
        risk_info = data.get("risk", {})
        if risk_info.get("category") == "HIGH_RISK":
            high_risk_count += 1
        if data.get("emergency_active"):
            emergency_active_count += 1
        for app in data.get("approaches", {}).values():
            total_city_pcu += app.get("total_pcu", 0.0)

    return {
        "active_junctions": total_active_junctions,
        "total_city_pcu": round(total_city_pcu, 1),
        "high_risk_junctions": high_risk_count,
        "active_emergencies": emergency_active_count,
        "system_health": "OPTIMAL" if high_risk_count <= 3 else "CONGESTION_ALERT",
    }


@router.get("/forecast/{junction_id}/{approach_id}")
async def get_approach_forecast(junction_id: str, approach_id: str, steps: int = 5):
    """Get 5-step ahead predicted PCU queue length."""
    key = f"{junction_id}:{approach_id}"
    predictions = forecaster.forecast(key, steps_ahead=steps)
    return {
        "junction_id": junction_id,
        "approach_id": approach_id,
        "predicted_pcu_steps": predictions,
    }
