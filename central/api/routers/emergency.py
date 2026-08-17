"""
Emergency Vehicle Preemption (EVP) & Green Corridor REST Router.
"""

from typing import Any, Dict, List, Optional
import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from central.coordinator.emergency_corridor_manager import emergency_manager
from central.api.state_store import junction_store

router = APIRouter(prefix="/emergency", tags=["Emergency Vehicle Preemption"])


class EmergencyDispatchRequest(BaseModel):
    route_key: str = Field(default="AMBULANCE_AIIMS_CORRIDOR", description="Preset route identifier")
    call_sign: str = Field(default="108_AMBULANCE_MH31_9021", description="Vehicle call sign / number plate")
    vehicle_type: str = Field(default="AMBULANCE", description="AMBULANCE or FIRE_BRIGADE")
    dispatched_by: str = Field(default="EMERGENCY_ICCC_OPERATOR_108", description="Operator / Dispatcher ID")
    target_speed_kmh: Optional[float] = Field(default=55.0, description="Target corridor speed in km/h")


@router.get("/routes", summary="List pre-configured emergency routes in Nagpur")
async def list_emergency_routes():
    """
    Returns available emergency medical and fire green corridor routes across Nagpur.
    """
    routes = []
    for key, val in emergency_manager.NAGPUR_EMERGENCY_ROUTES.items():
        routes.append({
            "route_key": key,
            "name": val["name"],
            "vehicle_type": val["vehicle_type"],
            "destination": val["destination"],
            "sequence": val["sequence"],
            "junction_count": len(val["sequence"]),
            "default_speed_kmh": val["speed_kmh"],
        })
    return {"routes": routes}


@router.post("/dispatch", summary="Engage multi-junction emergency green corridor")
async def dispatch_emergency_corridor(req: EmergencyDispatchRequest):
    """
    Triggers an immediate Emergency Vehicle Preemption (EVP) Green Corridor
    across sequential junctions for an Ambulance or Fire Brigade.
    """
    try:
        plan = emergency_manager.dispatch_emergency_vehicle(
            route_key=req.route_key,
            call_sign=req.call_sign,
            vehicle_type=req.vehicle_type,
            dispatched_by=req.dispatched_by,
            custom_speed_kmh=req.target_speed_kmh,
        )

        # Notify active junctions in the state store
        for jid, sched in plan.schedules.items():
            jstate = junction_store.get(jid)
            if jstate:
                logger_msg = f"🚨 Emergency {req.vehicle_type} preemption scheduled on Phase {sched['phase_id']}"
                # Pre-apply override if start is 0
                if sched["lock_start_rel_sec"] == 0:
                    jstate.override_active = True
                    jstate.override_phase_id = sched["phase_id"]
                    jstate.override_reason = f"EMERGENCY {req.vehicle_type} PREEMPTION: {req.call_sign}"

        return {
            "status": "ENGAGED",
            "dispatch_id": plan.dispatch_id,
            "vehicle_type": plan.vehicle_type,
            "call_sign": plan.call_sign,
            "corridor_name": plan.corridor_name,
            "destination": plan.destination_hospital,
            "junction_sequence": plan.junction_sequence,
            "schedules": plan.schedules,
            "created_at": plan.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch emergency corridor: {str(e)}")


@router.get("/active", summary="List currently active emergency green corridors")
async def list_active_emergencies():
    """
    Returns all active emergency corridors with remaining green wave traversal times.
    """
    active = emergency_manager.list_active_dispatches()
    now = time.time()

    return {
        "active_count": len(active),
        "active_corridors": [
            {
                "dispatch_id": p.dispatch_id,
                "vehicle_type": p.vehicle_type,
                "call_sign": p.call_sign,
                "corridor_name": p.corridor_name,
                "destination": p.destination_hospital,
                "elapsed_sec": round(now - p.created_at, 1),
                "is_active": p.is_active,
                "junction_sequence": p.junction_sequence,
                "schedules": p.schedules,
            }
            for p in active
        ],
        "timestamp": now,
    }


@router.post("/clear/{dispatch_id}", summary="Clear emergency corridor & revert to Max-Pressure")
async def clear_emergency(dispatch_id: str):
    """
    Releases the emergency preemption plan back to autonomous Max-Pressure traffic control.
    """
    success = emergency_manager.clear_emergency_dispatch(dispatch_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dispatch '{dispatch_id}' not found or already inactive")

    return {
        "status": "CLEARED",
        "dispatch_id": dispatch_id,
        "message": "Emergency green corridor terminated. Reverted to Adaptive Max-Pressure.",
    }
