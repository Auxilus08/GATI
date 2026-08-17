"""
Pydantic Schemas for GATI Telemetry, Junction Controls, Analytics, and WebSocket API.
All schemas are thin data contracts — no business logic here.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Ingestion Schemas (Edge → Central)
# ─────────────────────────────────────────────────────────────

class ApproachTelemetrySchema(BaseModel):
    total_pcu: float = 0.0
    vehicle_counts: Dict[str, int] = Field(default_factory=dict)
    queue_length_m: float = 0.0
    avg_speed_kmh: float = 0.0
    emergency: bool = False


class JunctionTelemetryReport(BaseModel):
    """
    Lightweight telemetry packet sent from each edge unit to the central API.
    Field names intentionally flat to minimise per-packet serialization cost.
    """
    junction_id: str
    timestamp: float
    active_phase_id: int = 1
    signal_state: str = "GREEN"   # GREEN | AMBER | ALL_RED
    pressures: Dict[int, float] = Field(default_factory=dict)
    approaches: Dict[str, ApproachTelemetrySchema] = Field(default_factory=dict)
    emergency_active: bool = False
    elapsed_green_sec: float = 0.0


# ─────────────────────────────────────────────────────────────
# Override / Control Schemas (Operator → Central)
# ─────────────────────────────────────────────────────────────

class OverrideCommandRequest(BaseModel):
    """
    Issue a manual phase lock or release for a junction.
    NOTE: No authentication in the demo build; production would require
    JWT + RBAC roles for traffic police operators (explicitly flagged as
    FUTURE WORK in DECISIONS.md).
    """
    action: str                              # "LOCK" | "RELEASE"
    phase_id: Optional[int] = None           # Required for LOCK
    duration_seconds: float = 60.0           # Max 300s, enforced by OverrideManager
    reason: str = "Manual operator control"
    operator_id: str = "ICCC_OPERATOR_01"


class EmergencyOverrideRequest(BaseModel):
    """Legacy schema kept for backward compatibility with existing corridor router."""
    junction_id: str
    phase_id: int
    duration_seconds: int = 45
    reason: str = "Ambulance Priority Corridor"
    authorized_by: str = "ICCC_Operator_01"


class GreenWaveRouteRequest(BaseModel):
    corridor_id: str
    start_junction_id: str
    target_speed_kmh: float = 35.0


# ─────────────────────────────────────────────────────────────
# Response Schemas (Central → Dashboard)
# ─────────────────────────────────────────────────────────────

class SignalTimingResponse(BaseModel):
    """Current vs. Max-Pressure recommended signal timing for a junction."""
    junction_id: str
    timestamp: float
    current_phase_id: int
    recommended_phase_id: int
    decision_reason: str
    elapsed_green_sec: float
    is_switch: bool
    pressures: Dict[int, float]
    override_active: bool
    operator_id: Optional[str] = None
    # Fixed-time baseline for before/after comparison
    fixed_time_phase_id: int
    fixed_time_green_sec: float


class ApproachForecastSchema(BaseModel):
    approach_id: str
    current_pcu: float
    current_queue_meters: float
    forecast_10min_pcu: float
    forecast_15min_pcu: float
    forecast_30min_pcu: float
    forecast_10min_queue_m: float
    forecast_30min_queue_m: float
    trend_direction: str
    trend_slope_pcu_per_min: float
    forecast_trajectory_pcu: List[float]


class ForecastResponse(BaseModel):
    junction_id: str
    timestamp: float
    forecasts: Dict[str, ApproachForecastSchema]


class IncidentAlertSchema(BaseModel):
    incident_id: str
    track_id: int
    vehicle_type: str
    incident_type: str
    severity: str
    stationary_duration_sec: float
    location_xy: List[float]
    approach_id: Optional[str] = None
    timestamp: float
    description: str


class IncidentResponse(BaseModel):
    junction_id: str
    active_incidents: List[IncidentAlertSchema]
    resolved_count: int = 0


class ApproachRiskSchema(BaseModel):
    approach_id: str
    live_risk_score: float
    risk_level: str
    speed_variance: float
    hard_braking_count: int
    near_miss_count: int
    average_speed_kmh: float
    active_vehicle_count: int
    contributing_factors: List[str]
    timestamp: float


class LiveRiskResponse(BaseModel):
    junction_id: str
    timestamp: float
    approach_risks: Dict[str, ApproachRiskSchema]
    junction_risk_score: float
    junction_risk_category: str


class ComparisonSummaryResponse(BaseModel):
    junction_id: str
    evaluation_period_sec: float
    fixed_avg_wait_sec: float
    mp_avg_wait_sec: float
    wait_time_reduction_pct: float
    fixed_avg_queue_m: float
    mp_avg_queue_m: float
    queue_reduction_pct: float
    estimated_fuel_saved_liters: float
    co2_reduction_kg: float
    total_timesteps: int


class OverrideAuditRecord(BaseModel):
    override_id: str
    junction_id: str
    phase_id: int
    operator_id: str
    action: str
    timestamp: float
    reason: str
    duration_sec: Optional[float] = None


class JunctionStateSummary(BaseModel):
    """Compact junction listing item."""
    junction_id: str
    name: str
    corridor_id: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    approaches_count: int
    phases_count: int
    risk_score: float = 0.0
    risk_category: str = "OPTIMAL"
    active_phase_id: int = 1
    emergency_active: bool = False
    last_seen_timestamp: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    city: str
    active_junctions: int
    configured_junctions: int
    uptime_sec: float
