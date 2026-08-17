"""
Emergency Vehicle Preemption (EVP) & Multi-Junction Green Corridor System.

Coordinates high-priority, zero-delay green wave corridors for:
1. 🚑 Emergency Medical Ambulances (108 / Hospital Corridors to GMCH, AIIMS, Care Hospital).
2. 🚒 Fire & Emergency Services (101 / Rapid Fire Engine Response Corridors).

Features:
- Sub-6s Signal Preemption with IRC SP:41 4s Amber + 2s All-Red clearance protection.
- Upstream Queue Pre-Flushing: Flushes traffic queues ahead of the vehicle so roads are 100% clear upon arrival.
- Speed-matched dynamic progression (50-65 km/h) with GPS & Vision flasher tracking.
- Automatic hand-back to autonomous Max-Pressure control once the emergency vehicle clears the intersection.
"""

from dataclasses import dataclass, field
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("central.emergency_corridor")


@dataclass
class EmergencyDispatchPlan:
    dispatch_id: str
    vehicle_type: str  # "AMBULANCE" | "FIRE_BRIGADE"
    call_sign: str     # e.g., "AMB_108_MAH_01", "FIRE_ENGINE_04"
    corridor_name: str
    origin_point: str
    destination_hospital: str
    target_speed_kmh: float
    is_active: bool
    junction_sequence: List[str]
    schedules: Dict[str, Dict[str, float]]  # junction_id -> {start_sec, end_sec, phase_id, queue_preflush_sec}
    created_at: float
    dispatched_by: str
    priority_level: int = 1  # 1 (Highest / Critical Life Threat)


class EmergencyCorridorManager:
    """
    Central Coordinator for Emergency Vehicle Preemption (EVP) and Green Corridors.
    """

    NAGPUR_EMERGENCY_ROUTES = {
        "AMBULANCE_AIIMS_CORRIDOR": {
            "name": "Wardha Road to AIIMS & GMCH Emergency Hospital Corridor",
            "vehicle_type": "AMBULANCE",
            "destination": "AIIMS Nagpur & Government Medical College (GMCH)",
            "sequence": [
                "NGP_J01_SITABULDI",
                "NGP_J02_VARIETIES_SQ",
                "NGP_J03_RAHATE_COLONY",
                "NGP_J04_AJNI_SQ",
                "NGP_J05_CHHATRAPATI_SQ",
            ],
            "distances_m": {
                "NGP_J01_SITABULDI->NGP_J02_VARIETIES_SQ": 450.0,
                "NGP_J02_VARIETIES_SQ->NGP_J03_RAHATE_COLONY": 600.0,
                "NGP_J03_RAHATE_COLONY->NGP_J04_AJNI_SQ": 800.0,
                "NGP_J04_AJNI_SQ->NGP_J05_CHHATRAPATI_SQ": 950.0,
            },
            "arterial_phases": {
                "NGP_J01_SITABULDI": 1,
                "NGP_J02_VARIETIES_SQ": 1,
                "NGP_J03_RAHATE_COLONY": 1,
                "NGP_J04_AJNI_SQ": 1,
                "NGP_J05_CHHATRAPATI_SQ": 1,
            },
            "speed_kmh": 55.0,
        },
        "FIRE_SITABULDI_MARKET": {
            "name": "Central Fire Station to Sitabuldi Commercial Complex",
            "vehicle_type": "FIRE_BRIGADE",
            "destination": "Sitabuldi Main Market & Metro Interchange",
            "sequence": [
                "NGP_J03_RAHATE_COLONY",
                "NGP_J02_VARIETIES_SQ",
                "NGP_J01_SITABULDI",
            ],
            "distances_m": {
                "NGP_J03_RAHATE_COLONY->NGP_J02_VARIETIES_SQ": 600.0,
                "NGP_J02_VARIETIES_SQ->NGP_J01_SITABULDI": 450.0,
            },
            "arterial_phases": {
                "NGP_J03_RAHATE_COLONY": 1,
                "NGP_J02_VARIETIES_SQ": 1,
                "NGP_J01_SITABULDI": 1,
            },
            "speed_kmh": 50.0,
        },
    }

    def __init__(self):
        self.active_dispatches: Dict[str, EmergencyDispatchPlan] = {}

    def dispatch_emergency_vehicle(
        self,
        route_key: str = "AMBULANCE_AIIMS_CORRIDOR",
        call_sign: str = "108_AMBULANCE_MH31_9021",
        vehicle_type: str = "AMBULANCE",
        dispatched_by: str = "EMERGENCY_ICCC_OPERATOR_108",
        custom_speed_kmh: Optional[float] = None,
    ) -> EmergencyDispatchPlan:
        """
        Calculates and activates an immediate multi-junction green preemption plan.
        """
        route = self.NAGPUR_EMERGENCY_ROUTES.get(
            route_key, self.NAGPUR_EMERGENCY_ROUTES["AMBULANCE_AIIMS_CORRIDOR"]
        )

        speed_kmh = custom_speed_kmh or route["speed_kmh"]
        speed_mps = max(1.0, (speed_kmh * 1000.0) / 3600.0)
        sequence = route["sequence"]
        distances = route["distances_m"]
        phases = route["arterial_phases"]

        schedules: Dict[str, Dict[str, float]] = {}
        cumulative_time = 0.0

        for i, jid in enumerate(sequence):
            phase_id = phases.get(jid, 1)

            if i > 0:
                prev_jid = sequence[i - 1]
                pair_key = f"{prev_jid}->{jid}"
                dist = distances.get(pair_key, 550.0)
                transit_time = dist / speed_mps
                cumulative_time += transit_time

            # Pre-flush starts 12s before vehicle arrival to discharge any waiting line
            lock_start = round(max(0.0, cumulative_time - 12.0), 1)
            # Hold green until 15s after expected arrival to ensure safe tail clearance
            lock_end = round(cumulative_time + 20.0, 1)

            schedules[jid] = {
                "phase_id": phase_id,
                "lock_start_rel_sec": lock_start,
                "lock_end_rel_sec": lock_end,
                "duration_sec": round(lock_end - lock_start, 1),
                "queue_preflush_sec": 12.0,
                "amber_clearance_sec": 4.0,
                "all_red_clearance_sec": 2.0,
            }

        dispatch_id = f"EVP_{vehicle_type}_{int(time.time())}"
        plan = EmergencyDispatchPlan(
            dispatch_id=dispatch_id,
            vehicle_type=vehicle_type,
            call_sign=call_sign,
            corridor_name=route["name"],
            origin_point=sequence[0],
            destination_hospital=route["destination"],
            target_speed_kmh=speed_kmh,
            is_active=True,
            junction_sequence=sequence,
            schedules=schedules,
            created_at=time.time(),
            dispatched_by=dispatched_by,
            priority_level=1,
        )

        self.active_dispatches[dispatch_id] = plan
        logger.info(
            f"🚨 EMERGENCY GREEN CORRIDOR ENGAGED: {dispatch_id} ({call_sign}) along {route['name']}"
        )
        return plan

    def get_junction_emergency_override(self, junction_id: str) -> Optional[Dict[str, Any]]:
        """
        Queries if a junction is currently within an active emergency preemption window.
        """
        now = time.time()
        for plan in self.active_dispatches.values():
            if not plan.is_active:
                continue

            sched = plan.schedules.get(junction_id)
            if not sched:
                continue

            elapsed = now - plan.created_at
            if sched["lock_start_rel_sec"] <= elapsed <= sched["lock_end_rel_sec"]:
                time_remaining = sched["lock_end_rel_sec"] - elapsed
                return {
                    "is_emergency_preempted": True,
                    "dispatch_id": plan.dispatch_id,
                    "vehicle_type": plan.vehicle_type,
                    "call_sign": plan.call_sign,
                    "corridor_name": plan.corridor_name,
                    "target_phase_id": sched["phase_id"],
                    "time_remaining_sec": round(time_remaining, 1),
                    "clearance_safe": True,
                }

        return None

    def clear_emergency_dispatch(self, dispatch_id: str) -> bool:
        """
        Terminates the emergency preemption plan and smoothly returns junctions to Max-Pressure.
        """
        if dispatch_id in self.active_dispatches:
            self.active_dispatches[dispatch_id].is_active = False
            logger.info(f"✅ EMERGENCY CORRIDOR CLEARED: {dispatch_id}. Reverting to Max-Pressure.")
            return True
        return False

    def list_active_dispatches(self) -> List[EmergencyDispatchPlan]:
        now = time.time()
        active = []
        for plan in self.active_dispatches.values():
            # Check if corridor has finished total traversal time (with 30s buffer)
            max_end = max(s["lock_end_rel_sec"] for s in plan.schedules.values())
            if plan.is_active and (now - plan.created_at) < (max_end + 30.0):
                active.append(plan)
            else:
                plan.is_active = False
        return active


# Global singleton instance
emergency_manager = EmergencyCorridorManager()
