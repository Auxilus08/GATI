"""
Corridor Coordination & Green Wave API Endpoints.
"""
from typing import Dict, Any, List
from fastapi import APIRouter
from central.coordinator.green_wave import CorridorGreenWaveCoordinator
from central.api.schemas.telemetry_schema import GreenWaveRouteRequest

router = APIRouter(prefix="/corridors", tags=["Corridors"])

# Default Nagpur Wardha Road corridor coordinator
wardha_road_coord = CorridorGreenWaveCoordinator(corridor_id="CORR_WARDHA_RD")
wardha_road_coord.register_corridor(
    sequence=["NGP_J01_SITABULDI", "NGP_J02_VARIETIES"],
    distances_m={"NGP_J01_SITABULDI->NGP_J02_VARIETIES": 650.0},
)


@router.get("/")
async def list_corridors():
    """List arterial corridors configured for green wave sync."""
    return [
        {
            "corridor_id": "CORR_WARDHA_RD",
            "name": "Wardha Road Arterial (Sitabuldi to Airport)",
            "junction_sequence": wardha_road_coord.junctions_sequence,
            "speed_limit_kmh": wardha_road_coord.speed_limit_kmh,
        }
    ]


@router.post("/green-wave/plan")
async def plan_green_wave(request: GreenWaveRouteRequest):
    """Compute green wave start offsets for a corridor."""
    offsets = wardha_road_coord.compute_green_wave_offsets(target_speed_kmh=request.target_speed_kmh)
    return {
        "corridor_id": request.corridor_id,
        "target_speed_kmh": request.target_speed_kmh,
        "junction_offsets_seconds": offsets,
    }
