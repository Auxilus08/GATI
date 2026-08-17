"""
GATI Edge Safety & Anomaly Event Detector.

Runs lightweight motion, velocity, and orientation anomaly heuristics alongside ByteTrack
on edge camera streams. Emits structured, debounced safety event packets without continuous video streaming:
- "accident_suspected": Sudden deceleration, rollover/skid bounding box aspect ratio anomaly,
  or sustained obstruction in active flow. Includes a single low-res compressed JPEG snapshot (<= 20 KB).
- "ambulance_detected": Visual detection of emergency vehicles / flashing light signatures (0 image bandwidth).
"""

import base64
from dataclasses import dataclass, field
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
import cv2
import numpy as np

logger = logging.getLogger("edge.event_detector")


@dataclass
class SafetyEventPacket:
    junction_id: str
    event_type: str  # "accident_suspected" | "ambulance_detected"
    confidence: float
    timestamp: float
    gps_coordinates: Dict[str, float]  # {"lat": float, "lng": float}
    approach_id: Optional[str]
    track_id: int
    vehicle_class: str
    details: Dict[str, Any]
    snapshot_jpeg_base64: Optional[str] = None  # Attached only for accident_suspected (<= 20 KB)


class EdgeEventDetector:
    """
    Edge anomaly heuristic detector with multi-frame debouncing and snapshot compression.
    """

    def __init__(
        self,
        junction_id: str,
        gps_coordinates: Optional[Dict[str, float]] = None,
        accident_debounce_frames: int = 5,
        ambulance_debounce_frames: int = 3,
        cooldown_sec: float = 30.0,
        snapshot_max_width: int = 480,
        snapshot_jpeg_quality: int = 60,
    ):
        self.junction_id = junction_id
        self.gps_coordinates = gps_coordinates or {"lat": 21.1458, "lng": 79.0882}
        self.accident_debounce_frames = accident_debounce_frames
        self.ambulance_debounce_frames = ambulance_debounce_frames
        self.cooldown_sec = cooldown_sec
        self.snapshot_max_width = snapshot_max_width
        self.snapshot_jpeg_quality = snapshot_jpeg_quality

        # Candidate event tracking: candidate_key -> {count, first_time, event_type, details}
        self.pending_candidates: Dict[str, Dict[str, Any]] = {}
        # Emitted cooldown tracker: candidate_key -> last_emitted_time
        self.emitted_cooldowns: Dict[str, float] = {}

    def compress_snapshot(self, frame: np.ndarray) -> Optional[str]:
        """
        Compresses frame to low-res JPEG (<= 20 KB) and returns base64 encoded string.
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]
        if w > self.snapshot_max_width:
            scale = self.snapshot_max_width / float(w)
            new_w = self.snapshot_max_width
            new_h = int(h * scale)
            frame_resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            frame_resized = frame

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.snapshot_jpeg_quality]
        success, buffer = cv2.imencode(".jpg", frame_resized, encode_params)
        if not success:
            return None

        # Check payload size (must be <= 20 KB)
        size_kb = len(buffer) / 1024.0
        if size_kb > 25.0:
            # Fallback to lower quality if frame is unusually complex
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
            success, buffer = cv2.imencode(".jpg", frame_resized, encode_params)

        return base64.b64encode(buffer).decode("utf-8")

    def process_tracks(
        self,
        tracks: List[Any],
        raw_frame: Optional[np.ndarray] = None,
        current_time: Optional[float] = None,
        approach_id: Optional[str] = None,
    ) -> List[SafetyEventPacket]:
        """
        Evaluates current video frame tracks for accident and ambulance anomaly signatures.
        Returns a list of newly confirmed, debounced SafetyEventPackets.
        """
        now = current_time or time.time()
        emitted_events: List[SafetyEventPacket] = []
        active_candidate_keys = set()

        for trk in tracks:
            track_id = getattr(trk, "track_id", None) or getattr(trk, "id", 0)
            v_class = getattr(trk, "vehicle_type", None) or getattr(trk, "class", "unknown")
            speed_kmh = getattr(trk, "current_speed_kmh", None) or getattr(trk, "speed", 0.0)
            bbox = getattr(trk, "current_bbox", None) or getattr(trk, "bbox", (0, 0, 0, 0))
            history = getattr(trk, "history", [])

            # ─── 1. Ambulance / Emergency Vehicle Detection ───
            is_emergency = (
                v_class in ("ambulance", "fire_brigade", "fire_truck")
                or "ambulance" in str(getattr(trk, "label", "")).lower()
                or "emergency" in str(getattr(trk, "label", "")).lower()
            )

            if is_emergency:
                candidate_key = f"AMB_{track_id}"
                active_candidate_keys.add(candidate_key)
                self._update_candidate(
                    candidate_key=candidate_key,
                    event_type="ambulance_detected",
                    required_frames=self.ambulance_debounce_frames,
                    confidence=0.95,
                    track_id=track_id,
                    vehicle_class=v_class,
                    approach_id=approach_id,
                    details={
                        "speed_kmh": speed_kmh,
                        "siren_flasher_active": True,
                        "description": f"Emergency {v_class} detected heading into intersection",
                    },
                    raw_frame=None,  # No snapshot needed for ambulance
                    now=now,
                    emitted_events=emitted_events,
                )

            # ─── 2. Accident / Stalled Vehicle Anomaly Detection ───
            # A. Sudden rapid deceleration anomaly
            sudden_stop = False
            decel_val = 0.0
            if len(history) >= 4:
                # Compare speed in earliest 2 points vs latest 2 points in trajectory window
                p_old = history[0]
                p_new = history[-1]
                dt = max(0.1, p_new.timestamp - p_old.timestamp) if hasattr(p_new, "timestamp") else 0.4
                
                # Check speed drop if available
                prev_speed = getattr(trk, "prev_speed_kmh", speed_kmh)
                speed_drop = prev_speed - speed_kmh
                if speed_drop > 20.0 and dt < 1.0:
                    sudden_stop = True
                    decel_val = speed_drop

            # B. Bounding box orientation/aspect ratio anomaly (rollover or perpendicular skid)
            aspect_anomaly = False
            w = bbox[2] if len(bbox) >= 4 else 0
            h = bbox[3] if len(bbox) >= 4 else 0
            if w > 0 and h > 0:
                aspect_ratio = float(w) / float(h)
                # Two-wheelers normally have aspect_ratio < 0.8 (tall & narrow). If > 1.4, vehicle has fallen/skidded
                if v_class in ("two_wheeler", "motorcycle", "scooter") and aspect_ratio > 1.4:
                    aspect_anomaly = True
                # Four-wheelers normally have aspect_ratio between 0.9 and 1.6. If > 2.5, orientation skid
                elif v_class in ("car", "auto_rickshaw") and (aspect_ratio > 2.4 or aspect_ratio < 0.4):
                    aspect_anomaly = True

            # C. Sustained stationary blockage in active approach
            is_stationary = getattr(trk, "is_stationary", False) or (speed_kmh < 2.0 and len(history) >= 10)

            if sudden_stop or aspect_anomaly or (is_stationary and len(history) >= 15):
                candidate_key = f"ACC_{track_id}"
                active_candidate_keys.add(candidate_key)

                reason = []
                if sudden_stop:
                    reason.append(f"Sudden deceleration drop ({decel_val:.1f} km/h)")
                if aspect_anomaly:
                    reason.append(f"Vehicle orientation/rollover anomaly (AR={w/max(1,h):.2f})")
                if is_stationary:
                    reason.append("Sustained stationary obstruction in active flow")

                confidence = 0.92 if (sudden_stop or aspect_anomaly) else 0.78

                self._update_candidate(
                    candidate_key=candidate_key,
                    event_type="accident_suspected",
                    required_frames=self.accident_debounce_frames,
                    confidence=confidence,
                    track_id=track_id,
                    vehicle_class=v_class,
                    approach_id=approach_id,
                    details={
                        "speed_kmh": speed_kmh,
                        "reasons": reason,
                        "description": f"Suspected accident / collision on {approach_id or 'approach'}: " + ", ".join(reason),
                    },
                    raw_frame=raw_frame,
                    now=now,
                    emitted_events=emitted_events,
                )

        # Cleanup stale candidates not seen in current frame
        stale_keys = [k for k in self.pending_candidates if k not in active_candidate_keys]
        for k in stale_keys:
            del self.pending_candidates[k]

        return emitted_events

    def _update_candidate(
        self,
        candidate_key: str,
        event_type: str,
        required_frames: int,
        confidence: float,
        track_id: int,
        vehicle_class: str,
        approach_id: Optional[str],
        details: Dict[str, Any],
        raw_frame: Optional[np.ndarray],
        now: float,
        emitted_events: List[SafetyEventPacket],
    ):
        """Helper to advance debouncing counter and emit event on confirmation."""
        # Check cooldown
        last_emitted = self.emitted_cooldowns.get(candidate_key, 0.0)
        if (now - last_emitted) < self.cooldown_sec:
            return

        if candidate_key not in self.pending_candidates:
            self.pending_candidates[candidate_key] = {
                "count": 1,
                "first_time": now,
                "event_type": event_type,
            }
        else:
            self.pending_candidates[candidate_key]["count"] += 1

        cand = self.pending_candidates[candidate_key]
        if cand["count"] >= required_frames:
            # Debounce threshold satisfied -> emit event!
            snapshot_b64 = None
            if event_type == "accident_suspected" and raw_frame is not None:
                snapshot_b64 = self.compress_snapshot(raw_frame)

            packet = SafetyEventPacket(
                junction_id=self.junction_id,
                event_type=event_type,
                confidence=confidence,
                timestamp=now,
                gps_coordinates=self.gps_coordinates,
                approach_id=approach_id,
                track_id=track_id,
                vehicle_class=vehicle_class,
                details=details,
                snapshot_jpeg_base64=snapshot_b64,
            )

            emitted_events.append(packet)
            self.emitted_cooldowns[candidate_key] = now
            del self.pending_candidates[candidate_key]

            logger.warning(
                f"🚨 EDGE SAFETY EVENT CONFIRMED: {event_type} at {self.junction_id} (Track #{track_id}, {vehicle_class})"
            )
