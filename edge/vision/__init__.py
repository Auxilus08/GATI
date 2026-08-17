"""
GATI Edge Vision Pipeline.
Provides quantized object detection, multi-object tracking (ByteTrack),
Indian PCU queue calculation, approach-level metrics, and structured telemetry logging.
"""

from dataclasses import dataclass, field
from importlib import import_module
from typing import Dict, List, Optional, Tuple

from edge.vision.taxonomy import IndianTrafficClass, IndianTrafficTaxonomy, IRC_PCU_WEIGHTS


@dataclass
class TrackedVehicle:
    track_id: int
    vehicle_type: str  # two_wheeler, auto_rickshaw, car, bus, truck, cycle, pedestrian, cart, emergency_vehicle
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    lane_id: Optional[int] = None
    speed_kmh: Optional[float] = None
    is_emergency: bool = False


@dataclass
class ApproachQueueMetrics:
    approach_id: str
    vehicle_counts: Dict[str, int] = field(default_factory=dict)
    total_pcu: float = 0.0
    queue_length_meters: float = 0.0
    average_speed_kmh: float = 0.0
    emergency_vehicle_detected: bool = False
    emergency_vehicle_count: int = 0
    confidence_score: float = 1.0

_LAZY_EXPORTS = {
    "ByteTrackerManager": ("edge.vision.tracker", "ByteTrackerManager"),
    "TrackState": ("edge.vision.tracker", "TrackState"),
    "VelocityEstimator": ("edge.vision.tracker", "VelocityEstimator"),
    "PCUEngine": ("edge.vision.pcu_engine", "PCUEngine"),
    "YOLODetector": ("edge.vision.detector", "YOLODetector"),
    "ApproachROI": ("edge.vision.detector", "ApproachROI"),
    "TrafficVideoPipeline": ("edge.vision.video_pipeline", "TrafficVideoPipeline"),
    "StructuredTelemetryWriter": ("edge.vision.video_pipeline", "StructuredTelemetryWriter"),
}


def __getattr__(name: str):
    """Lazy-load heavy vision exports so API-only deployments avoid OpenCV imports."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _LAZY_EXPORTS[name]
    attr = getattr(import_module(module_name), attr_name)
    globals()[name] = attr
    return attr

__all__ = [
    "TrackedVehicle",
    "ApproachQueueMetrics",
    "IndianTrafficClass",
    "IndianTrafficTaxonomy",
    "IRC_PCU_WEIGHTS",
    "ByteTrackerManager",
    "TrackState",
    "VelocityEstimator",
    "PCUEngine",
    "YOLODetector",
    "ApproachROI",
    "TrafficVideoPipeline",
    "StructuredTelemetryWriter",
]
