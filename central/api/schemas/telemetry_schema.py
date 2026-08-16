"""
Pydantic Schemas for GATI Telemetry, Junction Controls, and Analytics API.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ApproachTelemetrySchema(BaseModel):
    total_pcu: float
    vehicle_counts: Dict[str, int] = Field(default_factory=dict)
    queue_length_m: float = 0.0
    avg_speed_kmh: float = 0.0
    emergency: bool = False


class JunctionTelemetryReport(BaseModel):
    junction_id: str
    timestamp: float
    active_phase_id: int
    signal_state: str  # GREEN, YELLOW, ALL_RED
    pressures: Dict[int, float] = Field(default_factory=dict)
    approaches: Dict[str, ApproachTelemetrySchema]
    emergency_active: bool = False


class EmergencyOverrideRequest(BaseModel):
    junction_id: str
    phase_id: int
    duration_seconds: int = 45
    reason: str = "Ambulance Priority Corridor"
    authorized_by: str = "ICCC_Operator_01"


class GreenWaveRouteRequest(BaseModel):
    corridor_id: str
    start_junction_id: str
    target_speed_kmh: float = 35.0
