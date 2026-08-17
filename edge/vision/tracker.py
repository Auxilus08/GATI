"""
ByteTrack Multi-Object Tracking & Velocity Estimation Module.

Maintains vehicle track identities across video frames, maintains trajectory history,
and estimates per-vehicle speed (km/h) based on spatial movement vectors and camera calibration.
"""

from collections import deque
from dataclasses import dataclass, field
import math
import time
from typing import Deque, Dict, List, Optional, Tuple


@dataclass
class TrackPoint:
    x: float
    y: float
    timestamp: float


@dataclass
class TrackState:
    track_id: int
    vehicle_type: str
    confidence: float
    history: Deque[TrackPoint] = field(default_factory=lambda: deque(maxlen=30))
    current_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    current_speed_kmh: float = 0.0
    smoothed_speed_kmh: float = 0.0
    is_stationary: bool = True
    approach_id: Optional[str] = None
    last_updated: float = field(default_factory=time.time)


class VelocityEstimator:
    """
    Computes real-world vehicle velocities from pixel-space trajectory vectors.
    Uses calibrated pixel-to-meter scaling factors and temporal differentiation.
    """

    def __init__(
        self,
        meters_per_pixel: float = 0.05,
        stationary_threshold_kmh: float = 3.0,
        speed_smoothing_alpha: float = 0.35,
    ):
        self.meters_per_pixel = meters_per_pixel
        self.stationary_threshold_kmh = stationary_threshold_kmh
        self.speed_smoothing_alpha = speed_smoothing_alpha

    def estimate_speed(
        self,
        history: Deque[TrackPoint],
        current_time: float,
        meters_per_pixel_override: Optional[float] = None,
    ) -> Tuple[float, float, bool]:
        """
        Calculates instantaneous and smoothed speed in km/h.
        Returns: (instantaneous_kmh, smoothed_kmh, is_stationary)
        """
        if len(history) < 2:
            return 0.0, 0.0, True

        m_per_px = meters_per_pixel_override or self.meters_per_pixel

        # Use past window of ~0.3 - 0.5 seconds for robust velocity estimation
        p_latest = history[-1]
        p_prev = history[0]

        dt = p_latest.timestamp - p_prev.timestamp
        if dt <= 0.01:
            return 0.0, 0.0, True

        dx = p_latest.x - p_prev.x
        dy = p_latest.y - p_prev.y
        pixel_dist = math.sqrt(dx * dx + dy * dy)
        meters_dist = pixel_dist * m_per_px

        # Speed = (meters / sec) * 3.6 -> km/h
        speed_kmh = (meters_dist / dt) * 3.6

        # Cap realistic urban speed to 120 km/h to prevent optical glitch outliers
        speed_kmh = min(120.0, speed_kmh)

        is_stationary = speed_kmh < self.stationary_threshold_kmh
        return round(speed_kmh, 1), round(speed_kmh, 1), is_stationary


class ByteTrackerManager:
    """
    Multi-Object Track Manager interfacing with ByteTrack detections.
    Maintains persistent track records, trajectories, and physical velocities.
    """

    def __init__(
        self,
        meters_per_pixel: float = 0.05,
        max_lost_seconds: float = 2.0,
        track_history_len: int = 30,
    ):
        self.meters_per_pixel = meters_per_pixel
        self.max_lost_seconds = max_lost_seconds
        self.track_history_len = track_history_len
        self.velocity_estimator = VelocityEstimator(meters_per_pixel=meters_per_pixel)
        self.tracks: Dict[int, TrackState] = {}

    def update_track(
        self,
        track_id: int,
        vehicle_type: str,
        confidence: float,
        bbox: Tuple[int, int, int, int],
        timestamp: float,
        approach_id: Optional[str] = None,
        meters_per_pixel: Optional[float] = None,
    ) -> TrackState:
        """Update or create a track state with latest frame detection."""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0

        if track_id not in self.tracks:
            self.tracks[track_id] = TrackState(
                track_id=track_id,
                vehicle_type=vehicle_type,
                confidence=confidence,
                history=deque(maxlen=self.track_history_len),
                current_bbox=bbox,
                approach_id=approach_id,
                last_updated=timestamp,
            )

        track = self.tracks[track_id]
        track.vehicle_type = vehicle_type
        track.confidence = confidence
        track.current_bbox = bbox
        track.approach_id = approach_id
        track.last_updated = timestamp

        track.history.append(TrackPoint(x=center_x, y=center_y, timestamp=timestamp))

        # Compute speed
        m_px = meters_per_pixel or self.meters_per_pixel
        inst_speed, _, is_stat = self.velocity_estimator.estimate_speed(
            track.history, current_time=timestamp, meters_per_pixel_override=m_px
        )

        alpha = self.velocity_estimator.speed_smoothing_alpha
        track.current_speed_kmh = inst_speed
        track.smoothed_speed_kmh = round(alpha * inst_speed + (1 - alpha) * track.smoothed_speed_kmh, 1)
        track.is_stationary = is_stat

        return track

    def purge_lost_tracks(self, current_time: float):
        """Remove tracks that have not been observed for longer than max_lost_seconds."""
        dead_ids = [
            tid
            for tid, tstate in self.tracks.items()
            if (current_time - tstate.last_updated) > self.max_lost_seconds
        ]
        for tid in dead_ids:
            del self.tracks[tid]

    def get_active_tracks(self) -> List[TrackState]:
        """Return list of currently active tracks."""
        return list(self.tracks.values())
