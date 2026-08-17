"""
Human Operator Signal Override & Governance Audit Manager.

Provides a safe, auditable hook for traffic police officers or ICCC operators
to manually lock a phase (e.g. VIP convoy, special event, road incident)
or release control back to the autonomous Max-Pressure algorithm.
"""

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional, Union
import uuid

logger = logging.getLogger("edge.override")


@dataclass
class OverrideEvent:
    override_id: str
    junction_id: str
    phase_id: int
    operator_id: str
    action: str  # "LOCK", "RELEASE", "TIMEOUT"
    timestamp: float
    reason: str
    duration_sec: Optional[float] = None
    applied_until: Optional[float] = None


class OverrideManager:
    """
    Manages manual phase overrides with strict audit logging for municipal oversight.
    """

    def __init__(
        self,
        junction_id: str,
        audit_log_path: Optional[Union[str, Path]] = None,
        max_override_duration_sec: float = 300.0,  # Default 5-minute safety ceiling
    ):
        self.junction_id = junction_id
        self.max_override_duration_sec = max_override_duration_sec
        self.audit_log_path = Path(audit_log_path) if audit_log_path else None
        self.active_override: Optional[OverrideEvent] = None
        self.audit_history: List[OverrideEvent] = []

        if self.audit_log_path:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def lock_phase(
        self,
        phase_id: int,
        operator_id: str,
        reason: str,
        duration_sec: Optional[float] = None,
    ) -> OverrideEvent:
        """
        Engage a manual lock on a specific signal phase.
        Overrides autonomous Max-Pressure until released or timeout occurs.
        """
        now = time.time()
        effective_duration = min(
            duration_sec or self.max_override_duration_sec,
            self.max_override_duration_sec,
        )
        applied_until = now + effective_duration

        event = OverrideEvent(
            override_id=str(uuid.uuid4())[:8],
            junction_id=self.junction_id,
            phase_id=phase_id,
            operator_id=operator_id,
            action="LOCK",
            timestamp=now,
            reason=reason,
            duration_sec=effective_duration,
            applied_until=applied_until,
        )

        self.active_override = event
        self._record_event(event)
        logger.info(
            f"[AUDIT] Phase {phase_id} LOCKED by operator '{operator_id}' for {effective_duration}s. Reason: {reason}"
        )
        return event

    def release_override(self, operator_id: str, reason: str = "Manual release") -> Optional[OverrideEvent]:
        """Release any active manual phase lock and return to autonomous control."""
        if not self.active_override:
            return None

        now = time.time()
        event = OverrideEvent(
            override_id=self.active_override.override_id,
            junction_id=self.junction_id,
            phase_id=self.active_override.phase_id,
            operator_id=operator_id,
            action="RELEASE",
            timestamp=now,
            reason=reason,
            duration_sec=round(now - self.active_override.timestamp, 1),
            applied_until=None,
        )

        self.active_override = None
        self._record_event(event)
        logger.info(f"[AUDIT] Phase override RELEASED by operator '{operator_id}'. Reason: {reason}")
        return event

    def check_override_status(self, current_time: Optional[float] = None) -> Optional[int]:
        """
        Checks if a manual override is active. If expired, automatically releases and audits.
        Returns: active overridden phase_id or None.
        """
        if not self.active_override:
            return None

        now = current_time or time.time()
        if self.active_override.applied_until and now >= self.active_override.applied_until:
            # Auto-timeout release for safety
            logger.warning(
                f"[AUDIT] Phase {self.active_override.phase_id} lock TIMED OUT after {self.active_override.duration_sec}s. Reverting to autonomous Max-Pressure."
            )
            timeout_event = OverrideEvent(
                override_id=self.active_override.override_id,
                junction_id=self.junction_id,
                phase_id=self.active_override.phase_id,
                operator_id="SYSTEM_AUTO_TIMEOUT",
                action="TIMEOUT",
                timestamp=now,
                reason="Automatic safety timeout expired",
                duration_sec=self.active_override.duration_sec,
            )
            self.active_override = None
            self._record_event(timeout_event)
            return None

        return self.active_override.phase_id

    def _record_event(self, event: OverrideEvent):
        """Append event to in-memory history and structured JSONL audit file."""
        self.audit_history.append(event)
        if self.audit_log_path:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                record = {
                    "override_id": event.override_id,
                    "junction_id": event.junction_id,
                    "phase_id": event.phase_id,
                    "operator_id": event.operator_id,
                    "action": event.action,
                    "timestamp": round(event.timestamp, 3),
                    "reason": event.reason,
                    "duration_sec": event.duration_sec,
                }
                f.write(json.dumps(record) + "\n")
