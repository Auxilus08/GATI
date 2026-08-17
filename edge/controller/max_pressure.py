"""
Max-Pressure Adaptive Signal Control Algorithm.

Calculates upstream vs downstream queue differentials (pressure) per movement phase
and selects the maximal pressure phase subject to minimum/maximum green bounds
and human operator overrides.
"""

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple
from config.settings import JunctionConfig, MaxPressureConfig, SignalGuardrails
from edge.vision import ApproachQueueMetrics
from edge.controller.override_manager import OverrideManager

logger = logging.getLogger("edge.max_pressure")


@dataclass
class ControllerDecision:
    recommended_phase_id: int
    current_phase_id: int
    decision_reason: str  # "MAX_PRESSURE", "MIN_GREEN_HOLD", "MAX_GREEN_EXCEEDED", "EMERGENCY_OVERRIDE", "OPERATOR_OVERRIDE"
    pressures: Dict[int, float]
    elapsed_green_sec: float
    is_switch: bool
    override_active: bool = False
    operator_id: Optional[str] = None


class MaxPressureController:
    """
    Max-Pressure Traffic Signal Optimizer with Safety Guardrails & Human Override Hook.
    Pressure for a phase = Sum(Upstream Approach PCU Queue - Downstream PCU Queue) * Priority Multipliers.
    """

    def __init__(
        self,
        junction_config: JunctionConfig,
        mp_config: MaxPressureConfig,
        guardrails: Optional[SignalGuardrails] = None,
        override_manager: Optional[OverrideManager] = None,
    ):
        self.config = junction_config
        self.mp_config = mp_config
        self.guardrails = guardrails or SignalGuardrails()
        self.override_manager = override_manager or OverrideManager(junction_id=junction_config.junction_id)
        self.smoothed_pressures: Dict[int, float] = {p.phase_id: 0.0 for p in junction_config.phases}
        self.phase_cycle_count: Dict[int, int] = {p.phase_id: 0 for p in junction_config.phases}

    def compute_phase_pressures(
        self,
        approach_metrics: Dict[str, ApproachQueueMetrics],
        downstream_metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[int, float]:
        """
        Compute pressure score for each phase based on current approach PCU and downstream spillback.
        Pressure(Phase) = Sum_approaches(Upstream_PCU - 0.3 * Downstream_PCU) * Emergency_Multiplier
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

                # Downstream spillback resistance
                app_conf = next((a for a in self.config.approaches if a.id == app_id), None)
                if app_conf and app_conf.downstream_junction_id:
                    phase_pcu_out += downstream.get(app_conf.downstream_junction_id, 0.0)

            # Net queue pressure
            raw_pressure = max(0.0, (phase_pcu_in - 0.3 * phase_pcu_out)) * emergency_boost

            # Exponential smoothing for phase stability (alpha * current + (1 - alpha) * prev)
            prev_smoothed = self.smoothed_pressures.get(phase.phase_id, 0.0)
            alpha = self.mp_config.pressure_smoothing_alpha
            smoothed = alpha * raw_pressure + (1.0 - alpha) * prev_smoothed
            self.smoothed_pressures[phase.phase_id] = smoothed
            pressures[phase.phase_id] = round(smoothed, 2)

        return pressures

    def evaluate_decision(
        self,
        approach_metrics: Dict[str, ApproachQueueMetrics],
        current_phase_id: int,
        elapsed_green_sec: float,
        current_time: Optional[float] = None,
        downstream_metrics: Optional[Dict[str, float]] = None,
    ) -> ControllerDecision:
        """
        Evaluate full control logic at the current decision step.
        Returns a ControllerDecision containing recommended phase, rationale, and diagnostics.
        """
        pressures = self.compute_phase_pressures(approach_metrics, downstream_metrics)

        # 1. Check Human Operator Override Hook (Top Priority)
        overridden_phase = self.override_manager.check_override_status(current_time=current_time)
        if overridden_phase is not None:
            op_event = self.override_manager.active_override
            op_id = op_event.operator_id if op_event else "OPERATOR"
            return ControllerDecision(
                recommended_phase_id=overridden_phase,
                current_phase_id=current_phase_id,
                decision_reason=f"OPERATOR_OVERRIDE (Locked by {op_id})",
                pressures=pressures,
                elapsed_green_sec=elapsed_green_sec,
                is_switch=(overridden_phase != current_phase_id),
                override_active=True,
                operator_id=op_id,
            )

        # 2. Failure Mode: Low Detection Confidence (Adverse Weather / Fog / Dust / Occlusion)
        # If mean confidence is degraded, hold last safe state or switch to fixed cycle safely
        approach_confidences = [
            getattr(m, "confidence_score", 1.0)
            for m in approach_metrics.values()
            if hasattr(m, "confidence_score")
        ]
        if approach_confidences and (sum(approach_confidences) / len(approach_confidences)) < 0.40:
            logger.warning("Low detection confidence detected (< 0.40). Holding current signal state for safety.")
            return ControllerDecision(
                recommended_phase_id=current_phase_id,
                current_phase_id=current_phase_id,
                decision_reason="LOW_CONFIDENCE_HOLD (Degraded Vision)",
                pressures=pressures,
                elapsed_green_sec=elapsed_green_sec,
                is_switch=False,
            )

        # 3. Failure Mode: All-Approaches Gridlock (Total Saturation Fallback to Fixed-Time Plan)
        # When all approaches are heavily queued (> 25 PCU), Max-Pressure differentials become unstable.
        # Controller safely degrades to round-robin fixed-time allocation.
        all_saturated = (
            len(approach_metrics) >= len(self.config.approaches)
            and all(m.total_pcu >= 25.0 for m in approach_metrics.values())
        )
        if all_saturated and elapsed_green_sec >= self.guardrails.min_green_seconds:
            # Advance to next cyclical phase deterministically
            phase_ids = [p.phase_id for p in self.config.phases]
            if current_phase_id in phase_ids:
                curr_idx = phase_ids.index(current_phase_id)
                next_phase = phase_ids[(curr_idx + 1) % len(phase_ids)]
            else:
                next_phase = phase_ids[0]

            if elapsed_green_sec >= 30.0:  # 30s fixed green per approach during gridlock
                return ControllerDecision(
                    recommended_phase_id=next_phase,
                    current_phase_id=current_phase_id,
                    decision_reason="GRIDLOCK_FALLBACK_FIXED_TIME",
                    pressures=pressures,
                    elapsed_green_sec=elapsed_green_sec,
                    is_switch=True,
                )

        # 4. Check Emergency Vehicle Detection (Autonomous Priority Override)
        for phase in self.config.phases:
            for app_id in phase.active_approaches:
                metric = approach_metrics.get(app_id)
                if metric and metric.emergency_vehicle_detected:
                    if phase.phase_id != current_phase_id:
                        # Allow immediate switch to emergency phase after minimal 5s clearance
                        if elapsed_green_sec >= 5.0:
                            return ControllerDecision(
                                recommended_phase_id=phase.phase_id,
                                current_phase_id=current_phase_id,
                                decision_reason="EMERGENCY_PRIORITY_OVERRIDE",
                                pressures=pressures,
                                elapsed_green_sec=elapsed_green_sec,
                                is_switch=True,
                            )

        min_green = self.guardrails.min_green_seconds
        max_green = self.guardrails.max_green_seconds

        # 5. Minimum Green Guardrail: prevent rapid phase fluttering
        if elapsed_green_sec < min_green:
            return ControllerDecision(
                recommended_phase_id=current_phase_id,
                current_phase_id=current_phase_id,
                decision_reason="MIN_GREEN_HOLD",
                pressures=pressures,
                elapsed_green_sec=elapsed_green_sec,
                is_switch=False,
            )

        # 6. Maximum Green Guardrail: prevent cross-street starvation
        if elapsed_green_sec >= max_green:
            other_phases = {k: v for k, v in pressures.items() if k != current_phase_id}
            best_other_phase = max(other_phases, key=other_phases.get) if other_phases else current_phase_id
            return ControllerDecision(
                recommended_phase_id=best_other_phase,
                current_phase_id=current_phase_id,
                decision_reason="MAX_GREEN_EXCEEDED",
                pressures=pressures,
                elapsed_green_sec=elapsed_green_sec,
                is_switch=(best_other_phase != current_phase_id),
            )

        # 5. Autonomous Max-Pressure Selection
        best_phase_id = max(pressures, key=pressures.get)
        current_pressure = pressures.get(current_phase_id, 0.0)
        best_pressure = pressures.get(best_phase_id, 0.0)

        # Hysteresis margin: require at least 15% higher pressure to switch phase to avoid jitter
        if best_phase_id != current_phase_id and best_pressure > (current_pressure * 1.15):
            return ControllerDecision(
                recommended_phase_id=best_phase_id,
                current_phase_id=current_phase_id,
                decision_reason="MAX_PRESSURE_SWITCH",
                pressures=pressures,
                elapsed_green_sec=elapsed_green_sec,
                is_switch=True,
            )

        return ControllerDecision(
            recommended_phase_id=current_phase_id,
            current_phase_id=current_phase_id,
            decision_reason="MAX_PRESSURE_HOLD",
            pressures=pressures,
            elapsed_green_sec=elapsed_green_sec,
            is_switch=False,
        )

    def select_best_phase(
        self,
        approach_metrics: Dict[str, ApproachQueueMetrics],
        current_phase_id: int,
        elapsed_green_sec: float,
        min_green_sec: Optional[float] = None,
        max_green_sec: Optional[float] = None,
        downstream_metrics: Optional[Dict[str, float]] = None,
    ) -> int:
        """Backward-compatible wrapper returning best phase ID."""
        decision = self.evaluate_decision(
            approach_metrics=approach_metrics,
            current_phase_id=current_phase_id,
            elapsed_green_sec=elapsed_green_sec,
            downstream_metrics=downstream_metrics,
        )
        return decision.recommended_phase_id
