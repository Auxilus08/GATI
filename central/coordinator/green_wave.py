"""
Arterial Corridor Green Wave Coordinator.
Computes coordination offsets along linear arterial corridors (e.g., Wardha Road in Nagpur)
to enable green wave progression and emergency vehicle express routing without stopping at intermediate signals.
"""
from typing import Dict, List, Any


class CorridorGreenWaveCoordinator:
    """Synchronizes traffic signal offsets along an arterial corridor."""

    def __init__(self, corridor_id: str, speed_limit_kmh: float = 40.0):
        self.corridor_id = corridor_id
        self.speed_limit_kmh = speed_limit_kmh
        self.junctions_sequence: List[str] = []
        self.inter_junction_distances_m: Dict[str, float] = {}

    def register_corridor(self, sequence: List[str], distances_m: Dict[str, float]):
        """
        Define corridor order and inter-junction distances.
        e.g. ['NGP_J01_SITABULDI', 'NGP_J02_VARIETIES'] with distance 500m.
        """
        self.junctions_sequence = sequence
        self.inter_junction_distances_m = distances_m

    def compute_green_wave_offsets(self, target_speed_kmh: float = 35.0) -> Dict[str, float]:
        """
        Calculates recommended start offset in seconds for each downstream junction.
        Offset = Distance / Speed.
        """
        offsets: Dict[str, float] = {}
        speed_mps = (target_speed_kmh * 1000.0) / 3600.0
        cumulative_sec = 0.0

        if not self.junctions_sequence:
            return offsets

        offsets[self.junctions_sequence[0]] = 0.0

        for i in range(len(self.junctions_sequence) - 1):
            curr_j = self.junctions_sequence[i]
            next_j = self.junctions_sequence[i + 1]
            pair_key = f"{curr_j}->{next_j}"
            dist = self.inter_junction_distances_m.get(pair_key, 600.0)
            travel_time = dist / max(1.0, speed_mps)
            cumulative_sec += travel_time
            offsets[next_j] = round(cumulative_sec, 1)

        return offsets
