"""
Corridor Coordination & Green Wave Endpoints.
Dynamically loads corridor configuration from settings rather than hardcoding junction IDs.
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from central.coordinator.green_wave import CorridorGreenWaveCoordinator
from central.api.schemas.telemetry_schema import GreenWaveRouteRequest
from config.settings import load_all_junction_configs, load_global_settings

logger = logging.getLogger("central.api.corridors")
router = APIRouter(prefix="/corridors", tags=["Corridors"])

# Build corridor coordinators dynamically from junction configs
# Each junction with a corridor_id is grouped into its corridor.
# No hardcoded junction IDs — new junctions join corridors via their YAML.
_coordinators: Dict[str, CorridorGreenWaveCoordinator] = {}


def _get_or_build_coordinators() -> Dict[str, CorridorGreenWaveCoordinator]:
    """Lazy-build corridor coordinators from junction YAML configs."""
    global _coordinators
    if _coordinators:
        return _coordinators

    configs = load_all_junction_configs()
    # Group junctions by corridor_id
    corridor_junctions: Dict[str, List[str]] = {}
    for jid, cfg in configs.items():
        if cfg.corridor_id:
            corridor_junctions.setdefault(cfg.corridor_id, []).append(jid)

    for corridor_id, jids in corridor_junctions.items():
        coord = CorridorGreenWaveCoordinator(corridor_id=corridor_id)
        # Build inter-junction distance map (default 500m if not specified)
        distances: Dict[str, float] = {}
        for i in range(len(jids) - 1):
            key = f"{jids[i]}->{jids[i + 1]}"
            distances[key] = 500.0  # TODO: load from junction YAML geometry when available
        coord.register_corridor(sequence=jids, distances_m=distances)
        _coordinators[corridor_id] = coord

    logger.info(f"[Corridors] Loaded {len(_coordinators)} corridor(s): {list(_coordinators.keys())}")
    return _coordinators


@router.get("/", summary="List all arterial corridors")
async def list_corridors():
    """List all corridors derived from junction configs (config-driven, not hardcoded)."""
    coords = _get_or_build_coordinators()
    return [
        {
            "corridor_id": cid,
            "junction_sequence": coord.junctions_sequence,
            "junction_count": len(coord.junctions_sequence),
            "speed_limit_kmh": coord.speed_limit_kmh,
        }
        for cid, coord in coords.items()
    ]


@router.post("/green-wave/plan", summary="Compute green wave start offsets for a corridor")
async def plan_green_wave(request: GreenWaveRouteRequest):
    """
    Compute optimal phase start offsets for a green wave progression along a corridor.
    Offsets are calculated from inter-junction distances and target travel speed.
    """
    coords = _get_or_build_coordinators()
    coord = coords.get(request.corridor_id)
    if coord is None:
        raise HTTPException(
            status_code=404,
            detail=f"Corridor '{request.corridor_id}' not found. "
                   f"Available: {list(coords.keys())}",
        )
    offsets = coord.compute_green_wave_offsets(target_speed_kmh=request.target_speed_kmh)
    return {
        "corridor_id": request.corridor_id,
        "target_speed_kmh": request.target_speed_kmh,
        "junction_sequence": coord.junctions_sequence,
        "junction_offsets_seconds": offsets,
    }


@router.get("/{corridor_id}", summary="Get corridor detail")
async def get_corridor(corridor_id: str):
    coords = _get_or_build_coordinators()
    coord = coords.get(corridor_id)
    if coord is None:
        raise HTTPException(status_code=404, detail=f"Corridor '{corridor_id}' not found")
    return {
        "corridor_id": corridor_id,
        "junction_sequence": coord.junctions_sequence,
        "speed_limit_kmh": coord.speed_limit_kmh,
        "green_wave_offsets_35kmh": coord.compute_green_wave_offsets(target_speed_kmh=35.0),
    }
