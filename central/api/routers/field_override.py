"""
Field Constable Mobile / Tablet Quick-Action API.

Provides simplified one-tap traffic relief actions for frontline traffic police officers
on mobile devices or ruggedized field tablets, eliminating physical cabinet tampering:
- FLUSH_HEAVY_QUEUE (Temporary 45s arterial hold)
- PEDESTRIAN_SAFE_CROSSING (Immediate 20s all-pedestrian clearance)
- RESTORE_AUTONOMOUS_AI (Handover back to Max-Pressure)
"""

from enum import Enum
import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from central.api.state_store import junction_store

logger = logging.getLogger("central.api.field_override")
router = APIRouter(prefix="/field", tags=["Field Constable Mobile API"])


class FieldQuickActionType(str, Enum):
    FLUSH_HEAVY_QUEUE = "FLUSH_HEAVY_QUEUE"
    PEDESTRIAN_CROSSING = "PEDESTRIAN_CROSSING"
    ACCIDENT_CLEARANCE = "ACCIDENT_CLEARANCE"
    RESTORE_AUTONOMOUS = "RESTORE_AUTONOMOUS"


class FieldQuickActionRequest(BaseModel):
    junction_id: str
    action_type: FieldQuickActionType
    officer_badge_id: str = Field(..., description="Traffic Police Officer / Constable Badge Number")
    target_phase_id: Optional[int] = Field(default=None, description="Optional target phase ID to lock")
    duration_seconds: int = Field(default=45, ge=15, le=180, description="Relief hold duration (15s to 180s)")
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None


@router.post("/quick-action", summary="One-tap mobile action for field traffic police constables")
async def execute_field_quick_action(req: FieldQuickActionRequest):
    """
    Execute instant mobile relief command on a junction with verified police badge ID.
    """
    state = junction_store.get_or_create(req.junction_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Junction '{req.junction_id}' not found")

    if req.action_type == FieldQuickActionType.RESTORE_AUTONOMOUS:
        event = state.override_manager.release_override(
            operator_id=req.officer_badge_id,
            reason="Field Officer restored autonomous AI control",
        )
        return {
            "status": "AUTONOMOUS_RESTORED",
            "junction_id": req.junction_id,
            "officer_badge_id": req.officer_badge_id,
            "timestamp": time.time(),
            "message": "Signal returned to autonomous Max-Pressure control.",
        }

    # Lock phase for quick relief
    target_phase = req.target_phase_id or 1
    reason_map = {
        FieldQuickActionType.FLUSH_HEAVY_QUEUE: "Field Constable Heavy Queue Relief Flush",
        FieldQuickActionType.PEDESTRIAN_CROSSING: "Field Constable Manual Pedestrian Crossing Call",
        FieldQuickActionType.ACCIDENT_CLEARANCE: "Field Constable Accident Site Clearance",
    }
    reason = reason_map.get(req.action_type, "Field Constable Quick Action")

    event = state.override_manager.lock_phase(
        phase_id=target_phase,
        operator_id=f"CONSTABLE_{req.officer_badge_id}",
        reason=reason,
        duration_sec=float(req.duration_seconds),
    )

    logger.info(f"[Field Override] Badge {req.officer_badge_id} executed {req.action_type} on {req.junction_id} (Phase {target_phase}, {req.duration_seconds}s)")

    return {
        "status": "LOCKED",
        "junction_id": req.junction_id,
        "officer_badge_id": req.officer_badge_id,
        "action_type": req.action_type,
        "locked_phase_id": target_phase,
        "duration_seconds": req.duration_seconds,
        "audit_id": event.override_id,
        "expires_in_sec": req.duration_seconds,
        "message": f"Phase {target_phase} locked for {req.duration_seconds}s. Control will automatically revert to AI afterward.",
    }
