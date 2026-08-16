"""
Indian Standard PCU (Passenger Car Unit) & Queue Engine.
Converts heterogeneous Indian traffic mix (two-wheelers, auto-rickshaws, cars, buses)
into unified PCU queue pressures according to IRC / MoRTH standards.
"""
from typing import Dict, List
from config.settings import PCUWeights
from edge.vision import ApproachQueueMetrics, TrackedVehicle


class PCUEngine:
    """Calculates PCU equivalents and approach queue pressures."""

    def __init__(self, weights: PCUWeights):
        self.weights = weights

    def get_weight(self, vehicle_type: str) -> float:
        """Return IRC PCU weight for a recognized vehicle class."""
        type_clean = vehicle_type.lower().replace("-", "_").replace(" ", "_")
        weight_map = {
            "two_wheeler": self.weights.two_wheeler,
            "motorcycle": self.weights.two_wheeler,
            "scooter": self.weights.two_wheeler,
            "auto_rickshaw": self.weights.auto_rickshaw,
            "auto": self.weights.auto_rickshaw,
            "car": self.weights.car,
            "bus": self.weights.bus,
            "truck": self.weights.truck,
            "heavy_commercial": self.weights.truck,
            "light_commercial": self.weights.light_commercial,
            "van": self.weights.light_commercial,
            "bicycle": self.weights.bicycle,
        }
        return weight_map.get(type_clean, 1.0)

    def calculate_approach_metrics(
        self,
        approach_id: str,
        tracked_vehicles: List[TrackedVehicle],
        avg_speed_kmh: float = 0.0,
    ) -> ApproachQueueMetrics:
        """Compute aggregate counts, PCU total, and emergency flags for an approach."""
        counts: Dict[str, int] = {}
        total_pcu = 0.0
        emergency_count = 0

        for v in tracked_vehicles:
            counts[v.vehicle_type] = counts.get(v.vehicle_type, 0) + 1
            total_pcu += self.get_weight(v.vehicle_type)
            if v.is_emergency:
                emergency_count += 1

        # Approximation: 1 PCU in stationary/slow queue occupies ~6 meters of lane space
        queue_len_meters = total_pcu * 6.0

        return ApproachQueueMetrics(
            approach_id=approach_id,
            vehicle_counts=counts,
            total_pcu=round(total_pcu, 2),
            queue_length_meters=round(queue_len_meters, 1),
            average_speed_kmh=round(avg_speed_kmh, 1),
            emergency_vehicle_detected=(emergency_count > 0),
            emergency_vehicle_count=emergency_count,
        )
