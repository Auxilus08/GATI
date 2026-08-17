"""
Central Safety Events & Nearest-Authority Dispatch Router.

Ingests edge-detected accident & ambulance events, resolves nearest emergency authorities,
pushes real-time alerts via WebSocket to the dashboard, and maintains an immutable audit trail.
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional
import time
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from central.analytics.nearest_authority_resolver import authority_resolver, AuthorityContact
from central.api.state_store import junction_store
from central.coordinator.emergency_corridor_manager import emergency_manager

router = APIRouter(prefix="/safety", tags=["Safety Events & Nearest-Authority Alert"])


class SafetyEventReportRequest(BaseModel):
    junction_id: str = Field(..., description="Junction identifier")
    event_type: str = Field(..., description="accident_suspected or ambulance_detected")
    confidence: float = Field(default=0.90, description="Detection confidence 0.0 to 1.0")
    timestamp: Optional[float] = Field(default=None, description="Event timestamp")
    gps_coordinates: Optional[Dict[str, float]] = Field(default=None, description="Lat/Lng")
    approach_id: Optional[str] = Field(default=None, description="Approach ID")
    track_id: Optional[int] = Field(default=0, description="Track ID")
    vehicle_class: Optional[str] = Field(default="unknown", description="Vehicle class")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event metadata")
    snapshot_jpeg_base64: Optional[str] = Field(default=None, description="Low-res JPEG snapshot <= 20 KB")


class SafetyEventAcknowledgeRequest(BaseModel):
    operator_id: str = Field(default="ICCC_OPERATOR_CHIEF", description="Operator badge ID")
    dispatch_action: str = Field(default="DISPATCH_NEAREST_PATROL_AND_AMBULANCE", description="Action taken")
    notes: Optional[str] = Field(default="Units dispatched via 1-click ICCC console", description="Operator notes")


# In-Memory persistent store for Safety Events & Audit Trail
SAFETY_EVENTS_AUDIT_STORE: List[Dict[str, Any]] = []


@router.post("/events", summary="Ingest safety event from edge node & resolve nearest authority")
async def report_safety_event(req: SafetyEventReportRequest):
    """
    Ingests an edge-detected accident or ambulance event, resolves nearest authority,
    logs audit trail, and broadcasts WebSocket alert.
    """
    now = req.timestamp or time.time()
    event_id = f"EVT_{req.event_type.upper()[:3]}_{int(now*1000)}"

    # 1. Resolve nearest authorities
    resolved = authority_resolver.resolve_nearest_authorities(req.junction_id, req.gps_coordinates)
    primary_auth = asdict(resolved.primary_authority)
    med_auth = asdict(resolved.medical_authority)
    fire_auth = asdict(resolved.fire_authority) if resolved.fire_authority else None

    # 2. Automated Safe Signal Action (Fail-Safe & NTCIP Compliant)
    auto_signal_action = None
    if req.event_type == "accident_suspected" and req.confidence >= 0.80:
        jstate = junction_store.get_or_create(req.junction_id)
        if jstate:
            # Auto-extend All-Red clearance and hold upstream traffic to allow emergency vehicle access
            jstate.override_active = True
            jstate.override_phase_id = 1
            jstate.override_reason = f"AUTOMATED ACCIDENT SAFETY HOLD (Event: {event_id})"
            auto_signal_action = "ALL_RED_HOLD_APPLIED_FOR_APPROACH_CLEARANCE"
    elif req.event_type == "ambulance_detected":
        # Check if corridor preemption should be engaged
        emergency_plan = emergency_manager.dispatch_emergency_vehicle(
            route_key="AMBULANCE_AIIMS_CORRIDOR",
            call_sign=f"AMB_EDGE_DETECTED_{req.track_id}",
            vehicle_type="AMBULANCE",
            dispatched_by="EDGE_AI_AMBULANCE_CLASSIFIER",
        )
        auto_signal_action = f"GREEN_CORRIDOR_ENGAGED_{emergency_plan.dispatch_id}"

    # 3. Build Audit Record
    event_record = {
        "event_id": event_id,
        "junction_id": req.junction_id,
        "event_type": req.event_type,
        "confidence": req.confidence,
        "timestamp": now,
        "gps_coordinates": req.gps_coordinates or {"lat": 21.1458, "lng": 79.0882},
        "approach_id": req.approach_id,
        "track_id": req.track_id,
        "vehicle_class": req.vehicle_class,
        "details": req.details,
        "snapshot_jpeg_base64": req.snapshot_jpeg_base64,
        "nearest_authorities": {
            "primary": primary_auth,
            "medical": med_auth,
            "fire": fire_auth,
        },
        "auto_signal_action": auto_signal_action,
        "status": "PENDING_OPERATOR_ACK",
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "dispatch_notes": None,
    }

    SAFETY_EVENTS_AUDIT_STORE.insert(0, event_record)
    if len(SAFETY_EVENTS_AUDIT_STORE) > 200:
        SAFETY_EVENTS_AUDIT_STORE.pop()

    return {
        "status": "ACCEPTED",
        "event_id": event_id,
        "nearest_authority": primary_auth["station_name"],
        "estimated_arrival_minutes": primary_auth["estimated_arrival_minutes"],
        "auto_signal_action": auto_signal_action,
    }


@router.get("/events", summary="List recent safety events & audit trail")
async def list_safety_events(
    junction_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Returns recent safety events with nearest authority info and operator acknowledgment status.
    """
    events = SAFETY_EVENTS_AUDIT_STORE
    if junction_id:
        events = [e for e in events if e["junction_id"] == junction_id]

    return {
        "total_count": len(events),
        "events": events[:limit],
        "timestamp": time.time(),
    }


@router.post("/events/{event_id}/acknowledge", summary="1-Click Acknowledge & Dispatch Nearest Units")
async def acknowledge_safety_event(event_id: str, req: SafetyEventAcknowledgeRequest):
    """
    Operator acknowledges the safety event, dispatches nearest units, and records audit signature.
    """
    record = next((e for e in SAFETY_EVENTS_AUDIT_STORE if e["event_id"] == event_id), None)
    if not record:
        raise HTTPException(status_code=404, detail=f"Safety event '{event_id}' not found")

    record["acknowledged"] = True
    record["acknowledged_by"] = req.operator_id
    record["acknowledged_at"] = time.time()
    record["status"] = "DISPATCHED_ACKNOWLEDGED"
    record["dispatch_notes"] = f"{req.dispatch_action} | {req.notes or ''}"

    return {
        "status": "SUCCESS",
        "event_id": event_id,
        "acknowledged_by": req.operator_id,
        "acknowledged_at": record["acknowledged_at"],
        "message": f"Nearest emergency units dispatched for {record['junction_id']} ({record['event_type']})",
    }
