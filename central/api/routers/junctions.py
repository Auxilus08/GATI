"""
Junction configuration & management endpoints.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from config.settings import load_all_junction_configs, load_junction_config
from central.api.schemas.telemetry_schema import EmergencyOverrideRequest

router = APIRouter(prefix="/junctions", tags=["Junctions"])

# Active manual overrides
manual_overrides: Dict[str, Dict[str, Any]] = {}


@router.get("/")
async def list_junctions():
    """List all configured junctions in the city."""
    configs = load_all_junction_configs()
    return [
        {
            "junction_id": c.junction_id,
            "name": c.name,
            "corridor_id": c.corridor_id,
            "coordinates": c.coordinates.model_dump() if c.coordinates else None,
            "approaches_count": len(c.approaches),
            "phases_count": len(c.phases),
        }
        for c in configs.values()
    ]


@router.get("/{junction_id}")
async def get_junction_details(junction_id: str):
    """Get complete geometry and configuration for a specific junction."""
    try:
        cfg = load_junction_config(junction_id)
        return cfg.model_dump()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Junction configuration not found")


@router.post("/override/emergency")
async def trigger_emergency_override(request: EmergencyOverrideRequest):
    """
    Traffic Police / ICCC manual green override for emergency vehicle or VIP corridor.
    """
    manual_overrides[request.junction_id] = {
        "phase_id": request.phase_id,
        "duration_seconds": request.duration_seconds,
        "reason": request.reason,
        "authorized_by": request.authorized_by,
        "active": True,
    }
    return {
        "status": "OVERRIDE_COMMAND_ISSUED",
        "junction_id": request.junction_id,
        "target_phase": request.phase_id,
        "duration_seconds": request.duration_seconds,
    }
