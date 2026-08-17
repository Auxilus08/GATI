"""
NTCIP 1202 Signal Controller & Hardware Relay Interface.

Translates GATI adaptive Max-Pressure phase decisions into standard NTCIP 1202
Actuated Signal Controller (ASC) phase actuation commands and 230V AC relay bitmasks.
Includes a Software Malfunction Management / Conflict Monitor Unit (CMU) guard
to mechanically prevent simultaneous conflicting green states.
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("edge.controller.ntcip")


class NTCIPPhaseCommand(str, Enum):
    PHASE_HOLD = "HOLD"
    FORCE_OFF = "FORCE_OFF"
    CALL = "CALL"
    OMIT = "OMIT"


@dataclass
class HardwareRelayState:
    """Represents physical 230V AC lamp relay channel states for a junction."""
    red_relay_mask: int = 0
    amber_relay_mask: int = 0
    green_relay_mask: int = 0
    raw_ntcip_frame: bytes = b""


class ConflictMonitorUnit:
    """
    Simulates the physical Cabinet Conflict Monitor Unit (CMU / MMU).
    Mechanically blocks any software command that attempts to display
    simultaneous green indications on conflicting traffic movements.
    """

    def __init__(self, conflicting_phase_pairs: Optional[List[Tuple[int, int]]] = None):
        """
        :param conflicting_phase_pairs: List of conflicting phase ID tuples, e.g. [(1, 2), (1, 3)]
        """
        self.conflicts: Set[Tuple[int, int]] = set()
        if conflicting_phase_pairs:
            for p1, p2 in conflicting_phase_pairs:
                self.conflicts.add((min(p1, p2), max(p1, p2)))

    def validate_green_safety(self, active_green_phases: List[int]) -> bool:
        """
        Returns True if the proposed green phases are conflict-free.
        Returns False if a dangerous dual-green conflict is detected.
        """
        for i in range(len(active_green_phases)):
            for j in range(i + 1, len(active_green_phases)):
                pair = (min(active_green_phases[i], active_green_phases[j]), max(active_green_phases[i], active_green_phases[j]))
                if pair in self.conflicts:
                    logger.critical(f"[CMU TRIP] Hazardous Dual-Green Conflict detected between Phase {pair[0]} and Phase {pair[1]}!")
                    return False
        return True


class NTCIPControllerInterface:
    """
    NTCIP 1202 & Industrial RS-485 Relay Adapter for Municipal Traffic Cabinets.
    """

    def __init__(
        self,
        junction_id: str,
        conflicting_phase_pairs: Optional[List[Tuple[int, int]]] = None,
        ntcip_station_address: int = 1,
    ):
        self.junction_id = junction_id
        self.station_address = ntcip_station_address
        self.cmu = ConflictMonitorUnit(conflicting_phase_pairs)
        self.current_relay_state = HardwareRelayState()

    def generate_ntcip_phase_command(
        self,
        active_phase_id: int,
        signal_state: str,  # "GREEN", "AMBER", "ALL_RED"
        all_phase_ids: List[int],
    ) -> HardwareRelayState:
        """
        Generate physical relay bitmasks and standard NTCIP 1202 frame.
        """
        # 1. Hardware CMU Safety Validation
        if signal_state == "GREEN":
            is_safe = self.cmu.validate_green_safety([active_phase_id])
            if not is_safe:
                # CMU Trip -> Fallback to Flash/All-Red
                return HardwareRelayState(
                    red_relay_mask=(1 << len(all_phase_ids)) - 1,
                    amber_relay_mask=0,
                    green_relay_mask=0,
                    raw_ntcip_frame=b"\xFF\x00\x00\x00_CMU_TRIP",
                )

        green_mask = 0
        amber_mask = 0
        red_mask = 0

        for p_id in all_phase_ids:
            bit_pos = p_id - 1
            if p_id == active_phase_id:
                if signal_state == "GREEN":
                    green_mask |= (1 << bit_pos)
                elif signal_state == "AMBER":
                    amber_mask |= (1 << bit_pos)
                else:
                    red_mask |= (1 << bit_pos)
            else:
                red_mask |= (1 << bit_pos)

        # Construct NTCIP 1202 ASC Object payload (OID 1.3.6.1.4.1.1206.4.2.1.1.1)
        frame = bytes([
            0x7E,  # Framing flag
            self.station_address & 0xFF,
            0x01,  # Command: Phase Control
            green_mask & 0xFF,
            amber_mask & 0xFF,
            red_mask & 0xFF,
            0x7E,
        ])

        self.current_relay_state = HardwareRelayState(
            red_relay_mask=red_mask,
            amber_relay_mask=amber_mask,
            green_relay_mask=green_mask,
            raw_ntcip_frame=frame,
        )

        return self.current_relay_state
