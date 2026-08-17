"""
Real-Time Traffic Incident & Stalled Vehicle Detector.

Identifies road incidents, vehicle breakdowns, and junction blockages strictly from
real tracked trajectory movement vectors (near-zero displacement over time threshold).
"""

from dataclasses import dataclass, field
import logging
import math
import time
from typing import Dict, List, Optional, Tuple
import uuid

from edge.vision import TrackedVehicle

logger = logging.getLogger("central.incident")


@dataclass
class IncidentAlert:
    incident_id: str
    track_id: int
    vehicle_type: str
    incident_type: str  # "STALLED_VEHICLE", "JUNCTION_GRIDLOCK_BLOCKAGE", "ABNORMAL_STOPPAGE"
    severity: str        # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    stationary_duration_sec: float
    location_xy: Tuple[float, float]
    bbox: Tuple[int, int, int, int]
    approach_id: Optional[str]
    timestamp: float
    description: str


class IncidentDetector:
    """
    Monitors tracked object displacement to detect stalled vehicles and incidents.
    """

    def __init__(
        self,
        stalled_threshold_sec: float = 20.0,  # Stalled duration threshold
        min_displacement_meters: float = 1.5, # Near-zero displacement ceiling
        meters_per_pixel: float = 0.05,
    ):
        self.stalled_threshold_sec = stalled_threshold_sec
        self.min_displacement_meters = min_displacement_meters
        self.meters_per_pixel = meters_per_pixel

        # Track history state: track_id -> dict(first_seen, last_seen, anchor_pos, last_pos, stationary_start)
        self.vehicle_states: Dict[int, dict] = {}
        self.active_incidents: Dict[int, IncidentAlert] = {}
        self.incident_history: List[IncidentAlert] = []

    def update_frame(
        self,
        tracked_vehicles: List[TrackedVehicle],
        timestamp: float,
        approach_id: Optional[str] = None,
        is_intersection_box: bool = False,
    ) -> List[IncidentAlert]:
        """
        Process current frame detections and return any newly detected or ongoing incident alerts.
        """
        current_tids = set()
        newly_flagged: List[IncidentAlert] = []

        for v in tracked_vehicles:
            tid = v.track_id
            current_tids.add(tid)

            cx = (v.bbox[0] + v.bbox[2]) / 2.0
            cy = (v.bbox[1] + v.bbox[3]) / 2.0

            if tid not in self.vehicle_states:
                self.vehicle_states[tid] = {
                    "first_seen": timestamp,
                    "anchor_pos": (cx, cy),
                    "last_pos": (cx, cy),
                    "stationary_start": timestamp,
                    "vehicle_type": v.vehicle_type,
                    "bbox": v.bbox,
                    "approach_id": approach_id,
                }
                continue

            state = self.vehicle_states[tid]
            state["last_pos"] = (cx, cy)
            state["bbox"] = v.bbox
            if approach_id:
                state["approach_id"] = approach_id

            # Calculate displacement from anchor position
            dx = (cx - state["anchor_pos"][0]) * self.meters_per_pixel
            dy = (cy - state["anchor_pos"][1]) * self.meters_per_pixel
            disp_m = math.sqrt(dx * dx + dy * dy)

            if disp_m > self.min_displacement_meters:
                # Vehicle moved: reset anchor position and stationary counter
                state["anchor_pos"] = (cx, cy)
                state["stationary_start"] = timestamp
                if tid in self.active_incidents:
                    # Vehicle has recovered / cleared
                    logger.info(f"Incident on track {tid} CLEARED (vehicle resumed movement).")
                    del self.active_incidents[tid]
            else:
                # Vehicle is stationary or near-zero displacement
                stat_duration = timestamp - state["stationary_start"]

                if stat_duration >= self.stalled_threshold_sec:
                    # Determine severity based on location and duration
                    if is_intersection_box or stat_duration >= 45.0:
                        severity = "CRITICAL" if stat_duration >= 60.0 else "HIGH"
                        inc_type = "JUNCTION_GRIDLOCK_BLOCKAGE" if is_intersection_box else "STALLED_VEHICLE"
                    elif stat_duration >= 30.0:
                        severity = "MEDIUM"
                        inc_type = "STALLED_VEHICLE"
                    else:
                        severity = "LOW"
                        inc_type = "ABNORMAL_STOPPAGE"

                    desc = (
                        f"Track #{tid} ({v.vehicle_type}) stationary for {stat_duration:.1f}s "
                        f"(displacement {disp_m:.2f}m < {self.min_displacement_meters}m)"
                    )

                    alert = IncidentAlert(
                        incident_id=str(uuid.uuid4())[:8],
                        track_id=tid,
                        vehicle_type=v.vehicle_type,
                        incident_type=inc_type,
                        severity=severity,
                        stationary_duration_sec=round(stat_duration, 1),
                        location_xy=(round(cx, 1), round(cy, 1)),
                        bbox=v.bbox,
                        approach_id=state.get("approach_id"),
                        timestamp=round(timestamp, 3),
                        description=desc,
                    )

                    self.active_incidents[tid] = alert
                    newly_flagged.append(alert)
                    self.incident_history.append(alert)

        # Cleanup disappeared tracks
        lost_tids = [tid for tid in self.vehicle_states if tid not in current_tids]
        for tid in lost_tids:
            del self.vehicle_states[tid]
            if tid in self.active_incidents:
                del self.active_incidents[tid]

        return newly_flagged

    def get_active_incidents(self) -> List[IncidentAlert]:
        """Return list of active ongoing incidents."""
        return list(self.active_incidents.values())
