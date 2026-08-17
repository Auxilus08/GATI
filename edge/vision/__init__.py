"""
GATI Edge Vision Pipeline.
Provides quantized object detection, multi-object tracking (ByteTrack),
Indian PCU queue calculation, approach-level metrics, and structured telemetry logging.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from edge.vision.taxonomy import IndianTrafficClass, IndianTrafficTaxonomy, IRC_PCU_WEIGHTS
from edge.vision.tracker import ByteTrackerManager, TrackState, VelocityEstimator


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


from edge.vision.pcu_engine import PCUEngine
from edge.vision.detector import YOLODetector, ApproachROI
from edge.vision.video_pipeline import TrafficVideoPipeline, StructuredTelemetryWriter

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
