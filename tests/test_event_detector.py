"""
Unit Tests for Edge Safety Event Detector (Accident & Ambulance Detection).
"""

import base64
import time
import numpy as np
import pytest

from edge.vision.event_detector import EdgeEventDetector, SafetyEventPacket
from edge.vision.tracker import TrackPoint, TrackState


def test_ambulance_detection_and_debounce():
    detector = EdgeEventDetector(
        junction_id="NGP_J01_SITABULDI",
        accident_debounce_frames=5,
        ambulance_debounce_frames=3,
        cooldown_sec=30.0,
    )

    class MockTrack:
        id = 101
        vehicle_type = "ambulance"
        speed = 45.0
        bbox = (100, 100, 80, 120)
        history = []
        label = "🚑 Ambulance #101"

    tracks = [MockTrack()]

    # Frame 1: Pending, not emitted
    events = detector.process_tracks(tracks, raw_frame=None, current_time=1000.0)
    assert len(events) == 0

    # Frame 2: Pending, not emitted
    events = detector.process_tracks(tracks, raw_frame=None, current_time=1000.1)
    assert len(events) == 0

    # Frame 3: Debounce satisfied -> Emitted!
    events = detector.process_tracks(tracks, raw_frame=None, current_time=1000.2)
    assert len(events) == 1
    evt = events[0]
    assert evt.event_type == "ambulance_detected"
    assert evt.track_id == 101
    assert evt.snapshot_jpeg_base64 is None  # Zero image bandwidth for ambulance


def test_accident_detection_and_snapshot_compression():
    detector = EdgeEventDetector(
        junction_id="NGP_J01_SITABULDI",
        accident_debounce_frames=4,
        cooldown_sec=30.0,
        snapshot_max_width=480,
        snapshot_jpeg_quality=60,
    )

    # Synthetic 720p frame
    synthetic_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    synthetic_frame[200:400, 300:500] = [0, 0, 255]  # Red vehicle box

    class MockAccidentTrack:
        id = 202
        vehicle_type = "two_wheeler"
        speed = 0.0
        # Overturned two-wheeler: Width is 120, Height is 40 -> Aspect Ratio 3.0 (abnormal for 2W)
        bbox = (200, 200, 120, 40)
        history = [
            TrackPoint(x=200, y=100, timestamp=1000.0),
            TrackPoint(x=200, y=150, timestamp=1000.3),
            TrackPoint(x=200, y=200, timestamp=1000.6),
            TrackPoint(x=200, y=200, timestamp=1000.9),
        ]
        label = "🏍 Motorcycle #202"

    tracks = [MockAccidentTrack()]

    # Run 3 frames -> Not emitted
    for i in range(3):
        events = detector.process_tracks(tracks, raw_frame=synthetic_frame, current_time=1000.0 + i * 0.1)
        assert len(events) == 0

    # 4th frame -> Debounce threshold reached!
    events = detector.process_tracks(tracks, raw_frame=synthetic_frame, current_time=1000.4)
    assert len(events) == 1
    evt = events[0]
    assert evt.event_type == "accident_suspected"
    assert evt.track_id == 202
    assert evt.snapshot_jpeg_base64 is not None

    # Verify snapshot size constraint <= 20 KB
    decoded_bytes = base64.b64decode(evt.snapshot_jpeg_base64)
    size_kb = len(decoded_bytes) / 1024.0
    assert size_kb <= 20.0, f"Snapshot size {size_kb:.1f} KB exceeded 20 KB limit"


def test_cooldown_suppression():
    detector = EdgeEventDetector(
        junction_id="NGP_J01_SITABULDI",
        accident_debounce_frames=2,
        ambulance_debounce_frames=2,
        cooldown_sec=10.0,
    )

    class MockAmbulance:
        id = 999
        vehicle_type = "ambulance"
        speed = 50.0
        bbox = (100, 100, 80, 120)
        history = []
        label = "🚑 Ambulance #999"

    tracks = [MockAmbulance()]

    # Frame 1 & 2 -> Emitted
    detector.process_tracks(tracks, current_time=1000.0)
    events = detector.process_tracks(tracks, current_time=1000.1)
    assert len(events) == 1

    # Frame 3 & 4 within 10s cooldown -> Suppressed
    events = detector.process_tracks(tracks, current_time=1001.0)
    assert len(events) == 0
    events = detector.process_tracks(tracks, current_time=1002.0)
    assert len(events) == 0

    # Frame after 10s cooldown -> Emits again if candidate persists
    events = detector.process_tracks(tracks, current_time=1011.0)
    events = detector.process_tracks(tracks, current_time=1011.1)
    assert len(events) == 1
