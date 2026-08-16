"""
Telemetry ingestion endpoints.
Receives lightweight JSON packets from junction edge nodes and broadcasts to ICCC dashboards.
"""
from typing import Dict, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from central.api.schemas.telemetry_schema import JunctionTelemetryReport
from central.api.websocket_manager import WebSocketManager
from central.analytics.forecaster import QueueForecaster
from central.analytics.anomaly_detector import AnomalyDetector
from central.analytics.risk_index import JunctionRiskEngine

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

# In-memory live store for fast lookups
latest_telemetry: Dict[str, Dict[str, Any]] = {}
forecaster = QueueForecaster()
anomaly_detector = AnomalyDetector()
ws_manager = WebSocketManager()


@router.post("/report")
async def report_telemetry(report: JunctionTelemetryReport):
    """Receive telemetry packet from a junction edge unit."""
    data = report.model_dump()
    jid = report.junction_id
    latest_telemetry[jid] = data

    # Update analytics & check anomalies
    total_pcu = sum(app.total_pcu for app in report.approaches.values())
    pcu_list = [app.total_pcu for app in report.approaches.values()]
    max_pcu = max(pcu_list) if pcu_list else 0.0
    min_pcu = min(pcu_list) if pcu_list else 0.0
    avg_speed = (
        sum(app.avg_speed_kmh for app in report.approaches.values()) / max(1, len(report.approaches))
    )

    # Risk evaluation
    risk_info = JunctionRiskEngine.calculate_risk(
        total_pcu=total_pcu,
        max_approach_pcu=max_pcu,
        min_approach_pcu=min_pcu,
        avg_speed_kmh=avg_speed,
        emergency_active=report.emergency_active,
    )
    latest_telemetry[jid]["risk"] = risk_info

    for app_id, app_data in report.approaches.items():
        forecaster.update(f"{jid}:{app_id}", app_data.total_pcu)

    # Broadcast to live operators
    await ws_manager.broadcast({
        "type": "TELEMETRY_UPDATE",
        "junction_id": jid,
        "data": latest_telemetry[jid],
    })

    return {"status": "success", "junction_id": jid, "risk": risk_info}


@router.post("/batch")
async def report_telemetry_batch(reports: List[JunctionTelemetryReport]):
    """Receive buffered batch of telemetry packets from a recovered edge connection."""
    for report in reports:
        latest_telemetry[report.junction_id] = report.model_dump()
    return {"status": "success", "processed_count": len(reports)}


@router.get("/latest")
async def get_all_latest():
    """Retrieve the latest telemetry snapshot across all active city junctions."""
    return latest_telemetry


@router.get("/latest/{junction_id}")
async def get_junction_latest(junction_id: str):
    """Retrieve latest telemetry for a single junction."""
    return latest_telemetry.get(junction_id, {})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time ICCC operator stream."""
    await ws_manager.connect(websocket)
    try:
        # Send current state snapshot immediately upon connect
        await websocket.send_json({
            "type": "INITIAL_SNAPSHOT",
            "data": latest_telemetry,
        })
        while True:
            # Keepalive / handle client pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
