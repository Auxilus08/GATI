"""
GATI Edge Vision Pipeline.
Provides quantized object detection, multi-lane tracking, Indian PCU queue calculation,
and emergency vehicle (Ambulance/Fire) priority recognition.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict


@dataclass
class TrackedVehicle:
    track_id: int
    vehicle_type: str  # two_wheeler, auto_rickshaw, car, bus, truck, light_commercial
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
