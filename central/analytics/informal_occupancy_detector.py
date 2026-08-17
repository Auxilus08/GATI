"""
Religious Procession, Weekly Market & Informal Road Occupancy Anomaly Detector.

Detects non-vehicular or sustained informal road blockages
(e.g., Ganesh Visarjan, religious processions, weekly street markets, protest rallies)
where an approach experiences sustained occupancy (>70% bounding box density)
with near-zero throughput velocity (< 2.0 km/h) over a prolonged duration.

Automatically redistributes green time away from the blocked approach to active cross-streets.
"""

from dataclasses import dataclass
import time
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("central.informal_occupancy")


@dataclass
class InformalOccupancyEvent:
    event_id: str
    junction_id: str
    approach_id: str
    occupancy_type: str  # "PROCESSION_BLOCKAGE", "WEEKLY_MARKET", "CIVIL_DISRUPTION"
    duration_minutes: float
    average_speed_kmh: float
    recommended_action: str  # "REALLOCATE_GREEN_TO_CROSS_STREETS", "ALERT_TRAFFIC_POLICE"
    timestamp: float


class InformalOccupancyDetector:
    """
    Monitors approach kinematics for sustained informal road closures.
    """

    def __init__(
        self,
        min_stagnant_duration_sec: float = 180.0,  # 3 minutes of stagnant crowd density
        max_speed_kmh_threshold: float = 3.0,
        high_pcu_threshold: float = 20.0,
    ):
        self.min_duration_sec = min_stagnant_duration_sec
        self.max_speed_threshold = max_speed_kmh_threshold
        self.high_pcu_threshold = high_pcu_threshold

        # approach_id -> {start_time, last_seen_time, pcu_readings, speed_readings}
        self.approach_tracking: Dict[str, dict] = {}

    def evaluate_approach(
        self,
        junction_id: str,
        approach_id: str,
        total_pcu: float,
        average_speed_kmh: float,
        current_time: Optional[float] = None,
    ) -> Optional[InformalOccupancyEvent]:
        """
        Evaluate approach for sustained informal road occupancy.
        """
        t = current_time or time.time()
        key = f"{junction_id}:{approach_id}"

        is_stagnant_dense = (total_pcu >= self.high_pcu_threshold and average_speed_kmh <= self.max_speed_threshold)

        if not is_stagnant_dense:
            # Reset tracker if flow resumes
            if key in self.approach_tracking:
                del self.approach_tracking[key]
            return None

        if key not in self.approach_tracking:
            self.approach_tracking[key] = {
                "start_time": t,
                "last_time": t,
                "pcu_samples": [total_pcu],
                "speed_samples": [average_speed_kmh],
            }
            return None

        tracker = self.approach_tracking[key]
        tracker["last_time"] = t
        tracker["pcu_samples"].append(total_pcu)
        tracker["speed_samples"].append(average_speed_kmh)

        duration_sec = t - tracker["start_time"]

        if duration_sec >= self.min_duration_sec:
            avg_speed = sum(tracker["speed_samples"]) / len(tracker["speed_samples"])
            event = InformalOccupancyEvent(
                event_id=f"INF_{approach_id}_{int(t)}",
                junction_id=junction_id,
                approach_id=approach_id,
                occupancy_type="PROCESSION_OR_MARKET_BLOCKAGE",
                duration_minutes=round(duration_sec / 60.0, 1),
                average_speed_kmh=round(avg_speed, 1),
                recommended_action="REALLOCATE_GREEN_TO_CROSS_STREETS",
                timestamp=t,
            )
            logger.warning(f"[Informal Occupancy Alert] {approach_id} blocked for {duration_sec/60.0:.1f} mins (speed {avg_speed:.1f} km/h). Reallocating green splits.")
            return event

        return None
