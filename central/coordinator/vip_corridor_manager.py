"""
VIP Motorcade & Emergency Convoy Dynamic Green-Wave Progression Engine.

Calculates traveling green wave offsets across sequential arterial junctions
(e.g., Sitabuldi -> Varieties -> Rahate -> Ajni -> Chhatrapati along Wardha Road),
locks arterial green splits sequentially with convoy velocity tracking, and
smoothly transitions back to autonomous Max-Pressure once the convoy passes.
"""

from dataclasses import dataclass
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("central.vip_corridor")


@dataclass
class CorridorConvoyPlan:
    plan_id: str
    corridor_id: str
    target_speed_kmh: float
    convoy_active: bool
    junction_schedules: Dict[str, Dict[str, float]]  # junction_id -> {lock_start_sec, lock_end_sec, phase_id}
    created_timestamp: float
    operator_id: str
    reason: str


class VIPCorridorManager:
    """
    Coordinates multi-junction green corridors for VIP motorcades and emergency convoys.
    """

    def __init__(self):
        self.active_plans: Dict[str, CorridorConvoyPlan] = {}

    def create_convoy_progression_plan(
        self,
        corridor_id: str,
        junction_sequence: List[str],
        inter_junction_distances_m: Dict[str, float],
        arterial_phase_id_map: Dict[str, int],
        target_speed_kmh: float = 40.0,
        convoy_window_sec: float = 45.0,
        operator_id: str = "POLICE_COMMISSIONER_ICCC",
        reason: str = "VIP Motorcade Express Clearance",
    ) -> CorridorConvoyPlan:
        """
        Calculates sequential phase lock times for all junctions along the corridor.
        """
        speed_mps = max(1.0, (target_speed_kmh * 1000.0) / 3600.0)
        schedules: Dict[str, Dict[str, float]] = {}
        cumulative_time = 0.0

        for i, junc_id in enumerate(junction_sequence):
            phase_id = arterial_phase_id_map.get(junc_id, 1)

            if i > 0:
                prev_junc = junction_sequence[i - 1]
                pair_key = f"{prev_junc}->{junc_id}"
                dist = inter_junction_distances_m.get(pair_key, 500.0)
                transit_time = dist / speed_mps
                cumulative_time += transit_time

            # Window starts slightly before arrival and holds for convoy length
            lock_start = round(max(0.0, cumulative_time - 10.0), 1)
            lock_end = round(cumulative_time + convoy_window_sec, 1)

            schedules[junc_id] = {
                "phase_id": phase_id,
                "lock_start_rel_sec": lock_start,
                "lock_end_rel_sec": lock_end,
                "duration_sec": round(lock_end - lock_start, 1),
            }

        plan_id = f"VIP_{corridor_id}_{int(time.time())}"
        plan = CorridorConvoyPlan(
            plan_id=plan_id,
            corridor_id=corridor_id,
            target_speed_kmh=target_speed_kmh,
            convoy_active=True,
            junction_schedules=schedules,
            created_timestamp=time.time(),
            operator_id=operator_id,
            reason=reason,
        )

        self.active_plans[plan_id] = plan
        logger.info(f"[VIP Green Wave] Created convoy plan {plan_id} for {len(junction_sequence)} junctions along {corridor_id}")
        return plan

    def get_junction_override_directive(
        self,
        plan_id: str,
        junction_id: str,
        current_time: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a specific junction should currently lock its arterial green phase for the convoy.
        """
        plan = self.active_plans.get(plan_id)
        if not plan or not plan.convoy_active:
            return None

        now = current_time or time.time()
        elapsed = now - plan.created_timestamp
        sched = plan.junction_schedules.get(junction_id)

        if sched and sched["lock_start_rel_sec"] <= elapsed <= sched["lock_end_rel_sec"]:
            return {
                "action": "LOCK",
                "phase_id": sched["phase_id"],
                "reason": f"VIP Green Wave ({plan.reason})",
                "operator_id": plan.operator_id,
                "remaining_sec": round(sched["lock_end_rel_sec"] - elapsed, 1),
            }
        return None
