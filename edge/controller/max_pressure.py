"""
Max-Pressure Adaptive Signal Control Algorithm.
Calculates upstream vs downstream queue differentials (pressure) per movement phase
and selects the maximal pressure phase subject to minimum/maximum green bounds.
"""
from typing import Dict, List, Optional
from config.settings import JunctionConfig, MaxPressureConfig
from edge.vision import ApproachQueueMetrics


class MaxPressureController:
    """
    Max-Pressure Traffic Signal Optimizer.
    Pressure for a phase = Sum(Upstream Approach PCU Queue - Downstream PCU Queue) * Weight.
    """

    def __init__(self, junction_config: JunctionConfig, mp_config: MaxPressureConfig):
        self.config = junction_config
        self.mp_config = mp_config
        self.smoothed_pressures: Dict[int, float] = {p.phase_id: 0.0 for p in junction_config.phases}

    def compute_phase_pressures(
        self,
        approach_metrics: Dict[str, ApproachQueueMetrics],
        downstream_metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[int, float]:
        """
        Compute pressure score for each phase based on current approach PCU and downstream spillback.
        """
        downstream = downstream_metrics or {}
        pressures: Dict[int, float] = {}

        for phase in self.config.phases:
            phase_pcu_in = 0.0
            phase_pcu_out = 0.0
            emergency_boost = 1.0

            for app_id in phase.active_approaches:
                metric = approach_metrics.get(app_id)
                if metric:
                    phase_pcu_in += metric.total_pcu
                    if metric.emergency_vehicle_detected:
                        emergency_boost = max(emergency_boost, self.mp_config.priority_override_multiplier)

                # Check downstream resistance (if approach feeds into a congested downstream queue)
                app_conf = next((a for a in self.config.approaches if a.id == app_id), None)
                if app_conf and app_conf.downstream_junction_id:
                    phase_pcu_out += downstream.get(app_conf.downstream_junction_id, 0.0)

            raw_pressure = max(0.0, (phase_pcu_in - 0.3 * phase_pcu_out)) * emergency_boost

            # Exponential smoothing for phase stability
            prev_smoothed = self.smoothed_pressures.get(phase.phase_id, 0.0)
            alpha = self.mp_config.pressure_smoothing_alpha
            smoothed = alpha * raw_pressure + (1 - alpha) * prev_smoothed
            self.smoothed_pressures[phase.phase_id] = smoothed
            pressures[phase.phase_id] = round(smoothed, 2)

        return pressures

    def select_best_phase(
        self,
        approach_metrics: Dict[str, ApproachQueueMetrics],
        current_phase_id: int,
        elapsed_green_sec: float,
        min_green_sec: float = 15.0,
        max_green_sec: float = 60.0,
        downstream_metrics: Optional[Dict[str, float]] = None,
    ) -> int:
        """
        Decide whether to maintain the current phase or switch to the highest pressure phase.
        """
        pressures = self.compute_phase_pressures(approach_metrics, downstream_metrics)

        # Check for emergency override on any phase
        for phase in self.config.phases:
            for app_id in phase.active_approaches:
                metric = approach_metrics.get(app_id)
                if metric and metric.emergency_vehicle_detected:
                    return phase.phase_id

        # If minimum green has not elapsed, hold current phase
        if elapsed_green_sec < min_green_sec:
            return current_phase_id

        # If max green is exceeded, must switch to next highest non-current phase
        if elapsed_green_sec >= max_green_sec:
            other_phases = {k: v for k, v in pressures.items() if k != current_phase_id}
            if other_phases:
                return max(other_phases, key=other_phases.get)

        # Max pressure selection
        best_phase_id = max(pressures, key=pressures.get)
        return best_phase_id
