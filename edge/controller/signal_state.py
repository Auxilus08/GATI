"""
Signal Phase State Machine & Safety Guardrails.
Enforces Indian road safety standards: minimum green, maximum green, yellow clearance, and all-red intervals.
"""
import time
from enum import Enum
from typing import Optional, Dict, Any
from config.settings import SignalGuardrails


class SignalPhaseState(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ALL_RED = "ALL_RED"


class SignalControllerState:
    """Maintains active phase, elapsed time, and transition safety locks."""

    def __init__(self, guardrails: SignalGuardrails, initial_phase_id: int = 1):
        self.guardrails = guardrails
        self.active_phase_id = initial_phase_id
        self.pending_phase_id: Optional[int] = None
        self.current_state = SignalPhaseState.GREEN
        self.phase_start_time = time.time()
        self.state_start_time = time.time()
        self.manual_override: bool = False
        self.emergency_override: bool = False

    @property
    def elapsed_phase_time(self) -> float:
        return time.time() - self.phase_start_time

    @property
    def elapsed_state_time(self) -> float:
        return time.time() - self.state_start_time

    def can_transition_phase(self) -> bool:
        """Check if minimum green has elapsed and not currently in clearance transition."""
        if self.current_state != SignalPhaseState.GREEN:
            return False
        if self.emergency_override:
            # Still respect minimum 5s green even in emergency for safety
            return self.elapsed_phase_time >= 5.0
        return self.elapsed_phase_time >= self.guardrails.min_green_seconds

    def request_phase_change(self, target_phase_id: int, is_emergency: bool = False) -> bool:
        """Request a transition to a new phase."""
        if target_phase_id == self.active_phase_id and self.current_state == SignalPhaseState.GREEN:
            return False

        if not self.can_transition_phase() and not is_emergency:
            return False

        self.pending_phase_id = target_phase_id
        self.current_state = SignalPhaseState.YELLOW
        self.state_start_time = time.time()
        self.emergency_override = is_emergency
        return True

    def tick(self) -> Dict[str, any]:
        """Advance time step and process clearance transitions."""
        now = time.time()
        elapsed = now - self.state_start_time

        if self.current_state == SignalPhaseState.YELLOW:
            if elapsed >= self.guardrails.amber_seconds:
                self.current_state = SignalPhaseState.ALL_RED
                self.state_start_time = now
        elif self.current_state == SignalPhaseState.ALL_RED:
            if elapsed >= self.guardrails.all_red_seconds:
                self.active_phase_id = self.pending_phase_id or self.active_phase_id
                self.pending_phase_id = None
                self.current_state = SignalPhaseState.GREEN
                self.state_start_time = now
                self.phase_start_time = now

        return {
            "active_phase_id": self.active_phase_id,
            "state": self.current_state.value,
            "elapsed_phase_sec": round(self.elapsed_phase_time, 1),
            "emergency_active": self.emergency_override,
        }
