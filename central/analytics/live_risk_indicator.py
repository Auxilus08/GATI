"""
Live Approach Safety & Risk Indicator (Real Tracked Data Only).

Computes real-time dynamic conflict risk (0 to 100) per approach using Surrogate Safety Measures (SSM):
1. Speed Variance across active vehicles (Flow turbulence)
2. Abrupt Deceleration ("Hard Braking") events (a < -3.5 m/s^2)
3. Near-Miss Proxies (Vehicle pairs converging with TTC < 1.5s and distance < 2.0m)

================================================================================
STRICT DATA PROVENANCE DISCLOSURE:
This module is computed SOLELY from live tracked trajectory data.
It deliberately DOES NOT use synthetic/invented historical accident records or
simulated black-spot heatmaps. Long-term historical multi-year FIR crash indexing
is explicitly marked as FUTURE WORK upon receiving verified municipal accident databases.
================================================================================
"""

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from edge.vision import TrackedVehicle


@dataclass
class HardBrakingEvent:
    track_id: int
    vehicle_type: str
    deceleration_ms2: float
    initial_speed_kmh: float
    final_speed_kmh: float
    location_xy: Tuple[float, float]
    timestamp: float


@dataclass
class NearMissEvent:
    track_id_1: int
    track_id_2: int
    distance_meters: float
    relative_speed_kmh: float
    estimated_ttc_sec: float
    timestamp: float


@dataclass
class LiveApproachRisk:
    approach_id: str
    live_risk_score: float  # 0.0 to 100.0
    risk_level: str         # "LOW", "MODERATE", "ELEVATED", "CRITICAL"
    speed_variance: float
    hard_braking_count: int
    near_miss_count: int
    average_speed_kmh: float
    active_vehicle_count: int
    timestamp: float
    contributing_factors: List[str]


class LiveRiskIndicator:
    """
    Computes real-time surrogate safety risk per approach using live trajectory kinematics.
    """

    def __init__(
        self,
        meters_per_pixel: float = 0.05,
        hard_braking_threshold_ms2: float = -3.5,  # ~12.6 km/h / sec deceleration
        near_miss_distance_m: float = 2.0,         # Abnormal spatial proximity
        near_miss_ttc_sec: float = 1.5,            # Time to collision threshold
    ):
        self.meters_per_pixel = meters_per_pixel
        self.hard_braking_threshold_ms2 = hard_braking_threshold_ms2
        self.near_miss_distance_m = near_miss_distance_m
        self.near_miss_ttc_sec = near_miss_ttc_sec

        # State tracking: track_id -> dict(prev_speed_kmh, prev_time, prev_pos)
        self.prev_tracks: Dict[int, dict] = {}
        self.rolling_hard_braking: Dict[str, List[HardBrakingEvent]] = {}
        self.rolling_near_misses: Dict[str, List[NearMissEvent]] = {}

    def analyze_approach_frame(
        self,
        approach_id: str,
        tracked_vehicles: List[TrackedVehicle],
        timestamp: float,
        window_duration_sec: float = 10.0,
    ) -> LiveApproachRisk:
        """
        Analyze vehicle kinematics on an approach for a single frame and update rolling risk.
        """
        if approach_id not in self.rolling_hard_braking:
            self.rolling_hard_braking[approach_id] = []
            self.rolling_near_misses[approach_id] = []

        # Purge rolling events older than window_duration_sec
        self.rolling_hard_braking[approach_id] = [
            e for e in self.rolling_hard_braking[approach_id] if (timestamp - e.timestamp) <= window_duration_sec
        ]
        self.rolling_near_misses[approach_id] = [
            e for e in self.rolling_near_misses[approach_id] if (timestamp - e.timestamp) <= window_duration_sec
        ]

        speeds = [v.speed_kmh for v in tracked_vehicles if v.speed_kmh is not None]
        avg_speed = float(np.mean(speeds)) if speeds else 0.0
        speed_var = float(np.var(speeds)) if len(speeds) > 1 else 0.0

        # 1. Detect Hard Braking (Abrupt Deceleration)
        for v in tracked_vehicles:
            tid = v.track_id
            cx = (v.bbox[0] + v.bbox[2]) / 2.0
            cy = (v.bbox[1] + v.bbox[3]) / 2.0
            current_spd = v.speed_kmh or 0.0

            if tid in self.prev_tracks:
                prev_spd = self.prev_tracks[tid]["speed_kmh"]
                prev_time = self.prev_tracks[tid]["timestamp"]
                dt = timestamp - prev_time

                if dt >= 0.05:
                    # Convert speed delta from km/h to m/s
                    dv_ms = (current_spd - prev_spd) / 3.6
                    accel_ms2 = dv_ms / dt

                    if accel_ms2 <= self.hard_braking_threshold_ms2 and prev_spd >= 10.0:
                        event = HardBrakingEvent(
                            track_id=tid,
                            vehicle_type=v.vehicle_type,
                            deceleration_ms2=round(accel_ms2, 2),
                            initial_speed_kmh=round(prev_spd, 1),
                            final_speed_kmh=round(current_spd, 1),
                            location_xy=(round(cx, 1), round(cy, 1)),
                            timestamp=timestamp,
                        )
                        self.rolling_hard_braking[approach_id].append(event)

            self.prev_tracks[tid] = {
                "speed_kmh": current_spd,
                "timestamp": timestamp,
                "pos": (cx, cy),
            }

        # 2. Detect Near-Miss Proxies (Inter-vehicle spatial conflict)
        n = len(tracked_vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                v1 = tracked_vehicles[i]
                v2 = tracked_vehicles[j]

                c1 = ((v1.bbox[0] + v1.bbox[2]) / 2.0, (v1.bbox[1] + v1.bbox[3]) / 2.0)
                c2 = ((v2.bbox[0] + v2.bbox[2]) / 2.0, (v2.bbox[1] + v2.bbox[3]) / 2.0)

                dx = (c1[0] - c2[0]) * self.meters_per_pixel
                dy = (c1[1] - c2[1]) * self.meters_per_pixel
                dist_m = math.sqrt(dx * dx + dy * dy)

                if dist_m <= self.near_miss_distance_m:
                    spd1 = v1.speed_kmh or 0.0
                    spd2 = v2.speed_kmh or 0.0
                    rel_speed_kmh = abs(spd1 - spd2)
                    rel_speed_ms = rel_speed_kmh / 3.6

                    # If relative speed is significant, compute Time to Collision
                    if rel_speed_ms > 1.0:
                        ttc = dist_m / rel_speed_ms
                        if ttc <= self.near_miss_ttc_sec:
                            nm_event = NearMissEvent(
                                track_id_1=v1.track_id,
                                track_id_2=v2.track_id,
                                distance_meters=round(dist_m, 2),
                                relative_speed_kmh=round(rel_speed_kmh, 1),
                                estimated_ttc_sec=round(ttc, 2),
                                timestamp=timestamp,
                            )
                            self.rolling_near_misses[approach_id].append(nm_event)

        # 3. Compute Composite Live Risk Score (0-100)
        hard_braking_count = len(self.rolling_hard_braking[approach_id])
        near_miss_count = len(self.rolling_near_misses[approach_id])

        # Sub-score 1: Speed Variance (max 30 pts) - variance > 100 (std > 10 km/h) is high turbulence
        var_score = min(30.0, (speed_var / 120.0) * 30.0)

        # Sub-score 2: Hard Braking Events (max 35 pts) - 3+ events in 10s is severe
        brake_score = min(35.0, hard_braking_count * 12.0)

        # Sub-score 3: Near Miss Conflicts (max 35 pts) - 2+ near misses is severe
        near_miss_score = min(35.0, near_miss_count * 17.5)

        total_risk = round(min(100.0, var_score + brake_score + near_miss_score), 1)

        factors = []
        if speed_var > 60.0:
            factors.append(f"High speed variance ({speed_var:.1f} (km/h)^2)")
        if hard_braking_count > 0:
            factors.append(f"{hard_braking_count} hard braking event(s)")
        if near_miss_count > 0:
            factors.append(f"{near_miss_count} critical near-miss prox(ies)")
        if not factors:
            factors.append("Smooth uniform flow")

        if total_risk >= 70.0:
            level = "CRITICAL"
        elif total_risk >= 45.0:
            level = "ELEVATED"
        elif total_risk >= 25.0:
            level = "MODERATE"
        else:
            level = "LOW"

        return LiveApproachRisk(
            approach_id=approach_id,
            live_risk_score=total_risk,
            risk_level=level,
            speed_variance=round(speed_var, 1),
            hard_braking_count=hard_braking_count,
            near_miss_count=near_miss_count,
            average_speed_kmh=round(avg_speed, 1),
            active_vehicle_count=len(tracked_vehicles),
            timestamp=round(timestamp, 3),
            contributing_factors=factors,
        )
