"""
Telemetry Ingestion & Real-Time State Endpoints.

This router is the primary data-ingestion gate. Edge units POST to /report;
the router pipelines the payload in-process through:
  MaxPressureController → AnalyticsEngine → JunctionRiskEngine
and updates JunctionStateStore, then pushes the updated snapshot to all
WebSocket subscribers.

Deliberately thin: all business logic lives in the modules above.
"""

import asyncio
import contextlib
import logging
import os
import time
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from central.analytics.risk_index import JunctionRiskEngine
from central.api.schemas.telemetry_schema import ApproachTelemetrySchema, JunctionTelemetryReport
from central.api.state_store import (
    ApproachLiveState,
    JunctionLiveSnapshot,
    SignalTimingState,
    junction_store,
)
from central.api.websocket_manager import WebSocketManager
from edge.vision import ApproachQueueMetrics

logger = logging.getLogger("central.api.telemetry")

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])
ws_manager = WebSocketManager()
_vercel_demo_seeded = False
_dummy_feed_task: asyncio.Task | None = None
_dummy_feed_tick = 0


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _build_approach_metrics(report: JunctionTelemetryReport) -> Dict[str, ApproachQueueMetrics]:
    """Convert ingested telemetry schema into the internal ApproachQueueMetrics objects."""
    metrics: Dict[str, ApproachQueueMetrics] = {}
    for app_id, app in report.approaches.items():
        metrics[app_id] = ApproachQueueMetrics(
            approach_id=app_id,
            vehicle_counts=app.vehicle_counts,
            total_pcu=app.total_pcu,
            queue_length_meters=app.queue_length_m,
            average_speed_kmh=app.avg_speed_kmh,
            emergency_vehicle_detected=app.emergency,
            emergency_vehicle_count=1 if app.emergency else 0,
        )
    return metrics


def _snapshot_from_report(
    report: JunctionTelemetryReport,
    risk_info: Dict[str, Any],
    signal: SignalTimingState,
    analytics_summary: Dict[str, Any],
) -> JunctionLiveSnapshot:
    """Build a JunctionLiveSnapshot from the ingested telemetry + computed state."""
    approaches: Dict[str, ApproachLiveState] = {}
    for app_id, app in report.approaches.items():
        approaches[app_id] = ApproachLiveState(
            approach_id=app_id,
            total_pcu=app.total_pcu,
            queue_length_m=app.queue_length_m,
            avg_speed_kmh=app.avg_speed_kmh,
            vehicle_counts=app.vehicle_counts,
            emergency=app.emergency,
        )
    return JunctionLiveSnapshot(
        junction_id=report.junction_id,
        timestamp=report.timestamp,
        signal=signal,
        approaches=approaches,
        risk_score=risk_info.get("risk_score", 0.0),
        risk_category=risk_info.get("category", "OPTIMAL"),
        emergency_active=report.emergency_active,
        analytics=analytics_summary,
    )


async def _seed_vercel_demo_telemetry_if_needed():
    """Seed first-request demo telemetry on Vercel, where no simulator runs."""
    global _vercel_demo_seeded
    if _vercel_demo_seeded or os.getenv("VERCEL") != "1":
        return
    if not junction_store.all_junction_ids():
        junction_store.prewarm()
    if any(junction_store.get(jid).latest_snapshot for jid in junction_store.all_junction_ids()):
        _vercel_demo_seeded = True
        return

    await seed_dummy_telemetry(samples=5)

    _vercel_demo_seeded = True


async def seed_dummy_telemetry(samples: int = 1) -> None:
    """Populate every configured junction with deterministic demo telemetry.

    The feed intentionally enters through ``report_telemetry`` so every
    downstream contract (latest state, signal timing, forecasts, risk and
    comparison history) exercises the exact same path as a real edge unit.
    """
    global _dummy_feed_tick
    if not junction_store.all_junction_ids():
        junction_store.prewarm()

    interval = junction_store._settings.system.telemetry_interval_sec
    start_time = time.time() - max(0, samples - 1) * interval
    for sample in range(samples):
        tick = _dummy_feed_tick
        timestamp = start_time + sample * interval
        for junction_index, junction_id in enumerate(junction_store.all_junction_ids()):
            jstate = junction_store.get(junction_id)
            if not jstate:
                continue
            approaches = {}
            for approach_index, approach in enumerate(jstate.config.approaches):
                wave = (junction_index * 7 + approach_index * 5 + tick * 3) % 29
                total_pcu = 11.0 + wave
                approaches[approach.id] = ApproachTelemetrySchema(
                    total_pcu=round(total_pcu, 1),
                    vehicle_counts={
                        "two_wheeler": int(total_pcu * 0.78),
                        "auto_rickshaw": int(total_pcu * 0.22),
                        "car": int(total_pcu * 0.46),
                        "bus": 1 if total_pcu >= 28 else 0,
                        "truck": 1 if total_pcu >= 34 else 0,
                    },
                    queue_length_m=round(total_pcu * 5.5, 1),
                    avg_speed_kmh=round(max(10.0, 43.0 - total_pcu * 0.62), 1),
                    emergency=False,
                )
            phases = jstate.config.phases or []
            active_phase = phases[(tick + junction_index) % len(phases)].phase_id if phases else 1
            await report_telemetry(JunctionTelemetryReport(
                junction_id=junction_id,
                timestamp=timestamp,
                active_phase_id=active_phase,
                signal_state="GREEN",
                pressures={active_phase: round(sum(item.total_pcu for item in approaches.values()), 1)},
                approaches=approaches,
                emergency_active=False,
                elapsed_green_sec=12.0 + (tick % 28),
            ))
        _dummy_feed_tick += 1


async def _run_dummy_telemetry_feed() -> None:
    """Continuously refresh the local demo feed at the configured cadence."""
    interval = junction_store._settings.system.telemetry_interval_sec
    while True:
        await asyncio.sleep(interval)
        await seed_dummy_telemetry()


async def start_dummy_telemetry_feed() -> bool:
    """Seed and stream local demo data unless explicitly disabled by env var."""
    global _dummy_feed_task
    enabled = os.getenv("GATI_ENABLE_DUMMY_FEED", "1").lower() not in {"0", "false", "off"}
    if not enabled or os.getenv("VERCEL") == "1":
        return False
    await seed_dummy_telemetry(samples=5)
    _dummy_feed_task = asyncio.create_task(_run_dummy_telemetry_feed(), name="gati-dummy-telemetry")
    logger.info("[Telemetry] Local dummy feed enabled for %d junctions", len(junction_store.all_junction_ids()))
    return True


async def stop_dummy_telemetry_feed() -> None:
    """Cancel the local background feed cleanly during API shutdown."""
    global _dummy_feed_task
    if _dummy_feed_task:
        _dummy_feed_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _dummy_feed_task
        _dummy_feed_task = None


# ─────────────────────────────────────────────────────────────
# Ingestion endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/report", summary="Ingest real-time telemetry from one edge unit")
async def report_telemetry(report: JunctionTelemetryReport):
    """
    Receive a telemetry packet from a junction edge unit.
    Pipelines through MaxPressureController + AnalyticsEngine in-process,
    updates JunctionStateStore, and broadcasts via WebSocket.
    """
    jid = report.junction_id
    jstate = junction_store.get_or_create(jid)

    # 1. Build approach metrics for controller & analytics
    approach_metrics = _build_approach_metrics(report)

    # 2. Max-Pressure controller decision
    decision = jstate.controller.evaluate_decision(
        approach_metrics=approach_metrics,
        current_phase_id=jstate._current_phase_id,
        elapsed_green_sec=jstate.elapsed_green_sec,
        current_time=report.timestamp,
    )
    jstate.update_phase(decision.recommended_phase_id)

    signal = SignalTimingState(
        current_phase_id=report.active_phase_id,
        recommended_phase_id=decision.recommended_phase_id,
        decision_reason=decision.decision_reason,
        elapsed_green_sec=decision.elapsed_green_sec,
        is_switch=decision.is_switch,
        pressures=decision.pressures,
        override_active=decision.override_active,
        operator_id=decision.operator_id,
        fixed_time_phase_id=1,          # simple round-robin baseline for comparison
        fixed_time_green_sec=30.0,
    )

    # 3. Analytics engine (forecasting + incident detection + live risk)
    analytics_result = jstate.analytics_engine.process_telemetry_step(
        timestamp=report.timestamp,
        approach_metrics=approach_metrics,
        tracked_vehicles=[],   # Frame-level vehicles not available in bare telemetry packets
    )
    jstate.latest_analytics = analytics_result

    # Compact analytics summary for WebSocket payload (avoid huge nested objects)
    analytics_summary: Dict[str, Any] = {
        "forecasts": {
            k: {
                "current_pcu": v.current_pcu,
                "forecast_10min_pcu": v.forecast_10min_pcu,
                "forecast_30min_pcu": v.forecast_30min_pcu,
                "trend_direction": v.trend_direction,
            }
            for k, v in analytics_result.forecasts.items()
        },
        "active_incidents": len(analytics_result.active_incidents),
        "approach_risks": {
            k: {
                "live_risk_score": v.live_risk_score,
                "risk_level": v.risk_level,
            }
            for k, v in analytics_result.approach_risks.items()
        },
    }

    # 4. Junction Risk Index (composite 0-100 score for operator HUD)
    pcu_list = [a.total_pcu for a in report.approaches.values()]
    risk_info = JunctionRiskEngine.calculate_risk(
        total_pcu=sum(pcu_list),
        max_approach_pcu=max(pcu_list) if pcu_list else 0.0,
        min_approach_pcu=min(pcu_list) if pcu_list else 0.0,
        avg_speed_kmh=(
            sum(a.avg_speed_kmh for a in report.approaches.values()) / max(1, len(report.approaches))
        ),
        emergency_active=report.emergency_active,
    )

    # 5. Update state store
    snapshot = _snapshot_from_report(report, risk_info, signal, analytics_summary)
    jstate.latest_snapshot = snapshot

    # Keep rolling telemetry history (last 200 samples)
    jstate.telemetry_history.append(report.model_dump())
    if len(jstate.telemetry_history) > 200:
        jstate.telemetry_history.pop(0)

    # 6. Broadcast updated snapshot to WS subscribers
    ws_payload = {
        "type": "TELEMETRY_UPDATE",
        "junction_id": jid,
        "timestamp": report.timestamp,
        "signal": {
            "current_phase_id": signal.current_phase_id,
            "recommended_phase_id": signal.recommended_phase_id,
            "decision_reason": signal.decision_reason,
            "elapsed_green_sec": round(signal.elapsed_green_sec, 1),
            "is_switch": signal.is_switch,
            "pressures": signal.pressures,
            "override_active": signal.override_active,
        },
        "approaches": {
            k: {
                "total_pcu": v.total_pcu,
                "queue_length_m": v.queue_length_m,
                "avg_speed_kmh": v.avg_speed_kmh,
                "emergency": v.emergency,
            }
            for k, v in snapshot.approaches.items()
        },
        "risk": risk_info,
        "analytics": analytics_summary,
        "emergency_active": report.emergency_active,
    }
    await ws_manager.broadcast_junction(jid, ws_payload)

    # Broadcast alerts if there are active incidents
    if analytics_result.active_incidents:
        alert_payload = {
            "type": "INCIDENT_ALERT",
            "junction_id": jid,
            "timestamp": report.timestamp,
            "incidents": [
                {
                    "track_id": inc.track_id,
                    "vehicle_type": inc.vehicle_type,
                    "severity": inc.severity,
                    "description": inc.description,
                    "stationary_duration_sec": inc.stationary_duration_sec,
                }
                for inc in analytics_result.active_incidents
            ],
        }
        await ws_manager.broadcast_alerts(alert_payload)

    return {
        "status": "ok",
        "junction_id": jid,
        "recommended_phase": decision.recommended_phase_id,
        "decision_reason": decision.decision_reason,
        "risk": risk_info,
    }


@router.post("/batch", summary="Ingest buffered batch from a reconnecting edge unit")
async def report_telemetry_batch(reports: List[JunctionTelemetryReport]):
    """
    Accept a batch of buffered telemetry packets from an edge unit recovering
    from a network outage. Processed sequentially (oldest-first) so the
    analytics rolling buffers stay consistent.
    """
    results = []
    for report in sorted(reports, key=lambda r: r.timestamp):
        result = await report_telemetry(report)
        results.append({"junction_id": report.junction_id, "status": result["status"]})
    return {"status": "ok", "processed": len(results), "results": results}


# ─────────────────────────────────────────────────────────────
# REST state endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/latest", summary="Latest telemetry snapshot for all active junctions")
async def get_all_latest():
    """Aggregate latest state for every junction currently in the store."""
    await _seed_vercel_demo_telemetry_if_needed()
    out = {}
    for jid in junction_store.all_junction_ids():
        jstate = junction_store.get(jid)
        if jstate and jstate.latest_snapshot:
            snap = jstate.latest_snapshot
            out[jid] = {
                "junction_id": jid,
                "timestamp": snap.timestamp,
                "active_phase_id": snap.signal.recommended_phase_id,
                "risk_score": snap.risk_score,
                "risk_category": snap.risk_category,
                "emergency_active": snap.emergency_active,
                "approaches": {
                    k: {"total_pcu": v.total_pcu, "queue_length_m": v.queue_length_m}
                    for k, v in snap.approaches.items()
                },
            }
    return out


@router.get("/latest/{junction_id}", summary="Latest telemetry snapshot for one junction")
async def get_junction_latest(junction_id: str):
    """Retrieve the latest full state snapshot for a specific junction."""
    await _seed_vercel_demo_telemetry_if_needed()
    jstate = junction_store.get(junction_id)
    if not jstate or not jstate.latest_snapshot:
        return {"junction_id": junction_id, "status": "no_data"}
    snap = jstate.latest_snapshot
    return {
        "junction_id": junction_id,
        "timestamp": snap.timestamp,
        "signal": {
            "current_phase_id": snap.signal.current_phase_id,
            "recommended_phase_id": snap.signal.recommended_phase_id,
            "decision_reason": snap.signal.decision_reason,
            "elapsed_green_sec": round(snap.signal.elapsed_green_sec, 1),
            "pressures": snap.signal.pressures,
            "override_active": snap.signal.override_active,
        },
        "approaches": {
            k: {
                "total_pcu": v.total_pcu,
                "queue_length_m": v.queue_length_m,
                "avg_speed_kmh": v.avg_speed_kmh,
                "vehicle_counts": v.vehicle_counts,
                "emergency": v.emergency,
            }
            for k, v in snap.approaches.items()
        },
        "risk_score": snap.risk_score,
        "risk_category": snap.risk_category,
        "emergency_active": snap.emergency_active,
        "analytics": snap.analytics,
    }


# ─────────────────────────────────────────────────────────────
# WebSocket endpoints
# ─────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_global(websocket: WebSocket):
    """
    Global WebSocket stream — receives every junction's telemetry updates.
    Used by the city-wide dashboard map view.
    """
    await ws_manager.connect_global(websocket)
    try:
        # Send current snapshot of all junctions immediately on connect
        all_snap = {}
        for jid in junction_store.all_junction_ids():
            jstate = junction_store.get(jid)
            if jstate and jstate.latest_snapshot:
                all_snap[jid] = jstate.latest_snapshot.__dict__
        await websocket.send_json({"type": "INITIAL_SNAPSHOT", "data": all_snap})
        while True:
            # Keep connection alive; handle client pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@router.websocket("/ws/{junction_id}")
async def websocket_junction(websocket: WebSocket, junction_id: str):
    """
    Per-junction WebSocket stream — receives only that junction's updates.
    Used by the single-junction detail panel in the dashboard.
    """
    await ws_manager.connect_junction(websocket, junction_id)
    try:
        jstate = junction_store.get(junction_id)
        if jstate and jstate.latest_snapshot:
            await websocket.send_json({
                "type": "INITIAL_SNAPSHOT",
                "junction_id": junction_id,
                "data": jstate.latest_snapshot.__dict__,
            })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, junction_id)
