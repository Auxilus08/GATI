"""
Junction Configuration, Live State, Signal-Timing, and Override Endpoints.

Design: every endpoint is parameterised by junction_id.
Adding junction #51 means dropping a YAML in config/junctions/ — zero code change.
"""
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from central.api.schemas.telemetry_schema import (
    JunctionStateSummary,
    OverrideCommandRequest,
    OverrideAuditRecord,
    SignalTimingResponse,
    EmergencyOverrideRequest,
)
from central.api.state_store import junction_store
from config.settings import load_all_junction_configs, load_junction_config

logger = logging.getLogger("central.api.junctions")
router = APIRouter(prefix="/junctions", tags=["Junctions"])


# ─────────────────────────────────────────────────────────────
# Junction Registry — config-driven, not code-driven
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[JunctionStateSummary], summary="List all configured junctions")
async def list_junctions():
    """
    Returns every junction defined in config/junctions/*.yaml.
    Augments config metadata with live state (risk, phase) when available.
    No code change required to add a new junction — just add a YAML file.
    """
    configs = load_all_junction_configs()
    result = []
    for jid, cfg in configs.items():
        jstate = junction_store.get(jid)
        snap = jstate.latest_snapshot if jstate else None
        result.append(JunctionStateSummary(
            junction_id=jid,
            name=cfg.name,
            corridor_id=cfg.corridor_id,
            coordinates=cfg.coordinates.model_dump() if cfg.coordinates else None,
            approaches_count=len(cfg.approaches),
            phases_count=len(cfg.phases),
            risk_score=snap.risk_score if snap else 0.0,
            risk_category=snap.risk_category if snap else "OPTIMAL",
            active_phase_id=snap.signal.recommended_phase_id if snap else 1,
            emergency_active=snap.emergency_active if snap else False,
            last_seen_timestamp=snap.timestamp if snap else None,
        ))
    return result


@router.get("/{junction_id}", summary="Get full junction config and live state")
async def get_junction_detail(junction_id: str):
    """Full junction geometry configuration plus current live state if available."""
    try:
        cfg = load_junction_config(junction_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Junction '{junction_id}' not configured")

    jstate = junction_store.get(junction_id)
    snap = jstate.latest_snapshot if jstate else None

    return {
        "config": cfg.model_dump(),
        "live_state": {
            "active_phase_id": snap.signal.recommended_phase_id if snap else None,
            "risk_score": snap.risk_score if snap else None,
            "risk_category": snap.risk_category if snap else None,
            "emergency_active": snap.emergency_active if snap else None,
            "last_seen_timestamp": snap.timestamp if snap else None,
        },
    }


@router.get("/{junction_id}/state", summary="Current live state snapshot")
async def get_junction_state(junction_id: str):
    """Current signal phase, pressures, approach queues, risk score."""
    jstate = junction_store.get(junction_id)
    if not jstate or not jstate.latest_snapshot:
        raise HTTPException(status_code=404, detail=f"No live data yet for junction '{junction_id}'")
    snap = jstate.latest_snapshot
    return {
        "junction_id": junction_id,
        "timestamp": snap.timestamp,
        "signal": snap.signal.__dict__,
        "approaches": {k: v.__dict__ for k, v in snap.approaches.items()},
        "risk_score": snap.risk_score,
        "risk_category": snap.risk_category,
        "emergency_active": snap.emergency_active,
    }


# ─────────────────────────────────────────────────────────────
# Signal Timing — current vs. Max-Pressure recommended
# ─────────────────────────────────────────────────────────────

@router.get("/{junction_id}/signal-timing", summary="Current vs. Max-Pressure recommended signal timing")
async def get_signal_timing(junction_id: str):
    """
    Returns what the current signal is doing (as reported by the last telemetry)
    vs. what Max-Pressure recommends, enabling before/after comparison in the dashboard.
    """
    jstate = junction_store.get(junction_id)
    if not jstate or not jstate.latest_snapshot:
        raise HTTPException(status_code=404, detail=f"No live data yet for junction '{junction_id}'")
    snap = jstate.latest_snapshot
    sig = snap.signal
    return {
        "junction_id": junction_id,
        "timestamp": snap.timestamp,
        "current": {
            "phase_id": sig.current_phase_id,
            "green_sec": sig.fixed_time_green_sec,
            "mode": "FIXED_TIME",
        },
        "recommended": {
            "phase_id": sig.recommended_phase_id,
            "decision_reason": sig.decision_reason,
            "elapsed_green_sec": round(sig.elapsed_green_sec, 1),
            "pressures": sig.pressures,
            "mode": "MAX_PRESSURE",
        },
        "is_switch_recommended": sig.is_switch,
        "override_active": sig.override_active,
        "operator_id": sig.operator_id,
    }


# ─────────────────────────────────────────────────────────────
# Override — LOCK / RELEASE with audit trail
# ─────────────────────────────────────────────────────────────

@router.post("/{junction_id}/override", summary="Issue a phase lock or release command")
async def issue_override(junction_id: str, cmd: OverrideCommandRequest):
    """
    Lock a signal phase (for VIP convoy, emergency, manual intervention) or release it.
    Every action is logged to the junction's JSONL audit trail.

    NOTE: No authentication in the demo build. Production would require
    JWT + RBAC roles for traffic police and ICCC operators (see DECISIONS.md).
    """
    jstate = junction_store.get_or_create(junction_id)

    if cmd.action.upper() == "LOCK":
        if cmd.phase_id is None:
            raise HTTPException(status_code=422, detail="phase_id is required for LOCK action")
        event = jstate.override_manager.lock_phase(
            phase_id=cmd.phase_id,
            operator_id=cmd.operator_id,
            reason=cmd.reason,
            duration_sec=min(cmd.duration_seconds, 300.0),  # safety ceiling
        )
        return {
            "status": "LOCK_ENGAGED",
            "junction_id": junction_id,
            "override_id": event.override_id,
            "phase_id": event.phase_id,
            "operator_id": event.operator_id,
            "duration_sec": event.duration_sec,
            "applied_until": event.applied_until,
            "reason": event.reason,
        }

    elif cmd.action.upper() == "RELEASE":
        event = jstate.override_manager.release_override(
            operator_id=cmd.operator_id,
            reason=cmd.reason,
        )
        if event is None:
            return {"status": "NO_ACTIVE_OVERRIDE", "junction_id": junction_id}
        return {
            "status": "OVERRIDE_RELEASED",
            "junction_id": junction_id,
            "override_id": event.override_id,
            "operator_id": event.operator_id,
            "reason": event.reason,
        }

    else:
        raise HTTPException(status_code=422, detail=f"Unknown action '{cmd.action}'. Use LOCK or RELEASE.")


@router.get("/{junction_id}/override/status", summary="Active override status")
async def get_override_status(junction_id: str):
    """Check if a manual phase override is currently active for a junction."""
    jstate = junction_store.get_or_create(junction_id)
    active = jstate.override_manager.active_override
    if active is None:
        return {"junction_id": junction_id, "override_active": False}
    now = time.time()
    remaining = max(0.0, round((active.applied_until or now) - now, 1))
    return {
        "junction_id": junction_id,
        "override_active": True,
        "override_id": active.override_id,
        "phase_id": active.phase_id,
        "operator_id": active.operator_id,
        "reason": active.reason,
        "duration_sec": active.duration_sec,
        "remaining_sec": remaining,
    }


@router.get("/{junction_id}/override/audit", summary="Override audit trail")
async def get_override_audit(junction_id: str, limit: int = 20):
    """Return the last N override events for governance/accountability."""
    jstate = junction_store.get_or_create(junction_id)
    records = jstate.get_override_audit_tail(n=limit)
    return {"junction_id": junction_id, "audit_records": records, "total": len(records)}


# ─────────────────────────────────────────────────────────────
# Legacy emergency override (backward-compatible)
# ─────────────────────────────────────────────────────────────

@router.post("/override/emergency", summary="[Legacy] Emergency vehicle phase lock")
async def trigger_emergency_override(request: EmergencyOverrideRequest):
    """Backward-compatible emergency override endpoint used by older integrations."""
    jstate = junction_store.get_or_create(request.junction_id)
    event = jstate.override_manager.lock_phase(
        phase_id=request.phase_id,
        operator_id=request.authorized_by,
        reason=request.reason,
        duration_sec=float(request.duration_seconds),
    )
    return {
        "status": "OVERRIDE_COMMAND_ISSUED",
        "junction_id": request.junction_id,
        "target_phase": event.phase_id,
        "duration_seconds": event.duration_sec,
        "override_id": event.override_id,
    }
