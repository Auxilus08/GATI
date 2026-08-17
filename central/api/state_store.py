"""
GATI Junction State Store.

Central in-memory registry of per-junction runtime state.
Key design: `Dict[junction_id, JunctionRuntimeState]` — adding a new junction
means dropping a YAML file in config/junctions/; zero code change.

Multi-junction extensibility is achieved by lazy-init:
  store.get_or_create("NGP_J99_NEW") discovers and loads the YAML automatically.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import (
    GlobalSettings,
    JunctionConfig,
    load_all_junction_configs,
    load_global_settings,
    load_junction_config,
)
from edge.controller.max_pressure import MaxPressureController
from edge.controller.override_manager import OverrideEvent, OverrideManager
from central.analytics.analytics_engine import AnalyticsEngine, AnalyticsBatchResult

logger = logging.getLogger("central.state_store")

# Audit logs are written alongside the repo locally, but serverless hosts like
# Vercel only allow runtime writes in the temp directory.
AUDIT_LOG_DIR = (
    Path(tempfile.gettempdir()) / "gati" / "audit_logs"
    if os.getenv("VERCEL")
    else Path(__file__).resolve().parent.parent.parent / "scratch" / "audit_logs"
)


@dataclass
class ApproachLiveState:
    """Snapshot of a single approach at the most recent telemetry step."""
    approach_id: str
    total_pcu: float = 0.0
    queue_length_m: float = 0.0
    avg_speed_kmh: float = 0.0
    vehicle_counts: Dict[str, int] = field(default_factory=dict)
    emergency: bool = False


@dataclass
class SignalTimingState:
    """Current vs. Max-Pressure recommended signal timing."""
    current_phase_id: int = 1
    recommended_phase_id: int = 1
    decision_reason: str = "STARTUP"
    elapsed_green_sec: float = 0.0
    is_switch: bool = False
    pressures: Dict[int, float] = field(default_factory=dict)
    override_active: bool = False
    operator_id: Optional[str] = None
    # Fixed-time baseline comparison (from configured cycle)
    fixed_time_phase_id: int = 1
    fixed_time_green_sec: float = 30.0


@dataclass
class JunctionLiveSnapshot:
    """Full real-time state snapshot broadcast via WebSocket and served by REST."""
    junction_id: str
    timestamp: float
    signal: SignalTimingState
    approaches: Dict[str, ApproachLiveState]
    risk_score: float = 0.0
    risk_category: str = "OPTIMAL"
    emergency_active: bool = False
    analytics: Optional[Dict[str, Any]] = None   # latest AnalyticsBatchResult summary


class JunctionRuntimeState:
    """
    All runtime state for one junction. One instance per configured junction.
    Created lazily by JunctionStateStore.get_or_create().
    """

    def __init__(self, config: JunctionConfig, settings: GlobalSettings):
        self.config = config
        self.junction_id = config.junction_id
        self.settings = settings

        # Signal controller (MaxPressure) — one per junction, stateful
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.override_manager = OverrideManager(
            junction_id=config.junction_id,
            audit_log_path=AUDIT_LOG_DIR / f"{config.junction_id}_overrides.jsonl",
            max_override_duration_sec=300.0,
        )
        self.controller = MaxPressureController(
            junction_config=config,
            mp_config=settings.max_pressure,
            guardrails=settings.signal_guardrails,
            override_manager=self.override_manager,
        )

        # Analytics engine — one per junction, stateful rolling buffers
        self.analytics_engine = AnalyticsEngine(
            stalled_threshold_sec=20.0,
            sample_interval_sec=settings.system.telemetry_interval_sec,
        )

        # In-memory live snapshot (reset on each telemetry report)
        self.latest_snapshot: Optional[JunctionLiveSnapshot] = None
        self.latest_analytics: Optional[AnalyticsBatchResult] = None

        # Phase timing tracker (wall-clock elapsed green for current phase)
        self._current_phase_id: int = config.phases[0].phase_id if config.phases else 1
        self._phase_start_time: float = time.time()

        # Rolling history for comparison / anomaly context
        self.telemetry_history: List[Dict[str, Any]] = []  # last 200 raw reports
        logger.info(f"[StateStore] Initialized JunctionRuntimeState for {config.junction_id}")

    @property
    def elapsed_green_sec(self) -> float:
        return time.time() - self._phase_start_time

    def update_phase(self, new_phase_id: int):
        if new_phase_id != self._current_phase_id:
            self._current_phase_id = new_phase_id
            self._phase_start_time = time.time()

    def get_override_audit_tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return last N override audit events."""
        events = self.override_manager.audit_history[-n:]
        return [
            {
                "override_id": e.override_id,
                "junction_id": e.junction_id,
                "phase_id": e.phase_id,
                "operator_id": e.operator_id,
                "action": e.action,
                "timestamp": e.timestamp,
                "reason": e.reason,
                "duration_sec": e.duration_sec,
            }
            for e in events
        ]


class JunctionStateStore:
    """
    Singleton registry of all active junction runtime states.

    Multi-junction extensibility:
    - New junction → add a YAML to config/junctions/ → get_or_create() handles the rest.
    - The store never has junction IDs baked in; it discovers them from the filesystem.
    """

    def __init__(self):
        self._store: Dict[str, JunctionRuntimeState] = {}
        self._settings: GlobalSettings = load_global_settings()

    def prewarm(self):
        """Load all configured junctions at startup to avoid first-request latency."""
        configs = load_all_junction_configs()
        for jid, cfg in configs.items():
            self.get_or_create(jid, cfg)
        logger.info(f"[StateStore] Pre-warmed {len(self._store)} junction(s): {list(self._store.keys())}")

    def get_or_create(
        self,
        junction_id: str,
        config: Optional[JunctionConfig] = None,
    ) -> JunctionRuntimeState:
        """Return existing runtime state or create a new one from config."""
        if junction_id not in self._store:
            if config is None:
                try:
                    config = load_junction_config(junction_id)
                except FileNotFoundError:
                    # Unknown junction: create a minimal stub config so ingestion doesn't fail
                    logger.warning(
                        f"[StateStore] No YAML config for junction '{junction_id}'. "
                        f"Creating stub state. Add a YAML to config/junctions/ for full functionality."
                    )
                    from config.settings import PhaseConfig, ApproachConfig
                    config = JunctionConfig(
                        junction_id=junction_id,
                        name=junction_id,
                        approaches=[
                            ApproachConfig(id="APP_DEFAULT", name="Default", direction="N", camera_source="")
                        ],
                        phases=[PhaseConfig(phase_id=1, name="Phase 1", active_approaches=["APP_DEFAULT"])],
                    )
            self._store[junction_id] = JunctionRuntimeState(config, self._settings)
        return self._store[junction_id]

    def get(self, junction_id: str) -> Optional[JunctionRuntimeState]:
        return self._store.get(junction_id)

    def all_junction_ids(self) -> List[str]:
        """All junction IDs currently in the store."""
        return list(self._store.keys())

    def all_snapshots(self) -> Dict[str, Optional[JunctionLiveSnapshot]]:
        return {jid: state.latest_snapshot for jid, state in self._store.items()}


# Module-level singleton — imported by routers
junction_store = JunctionStateStore()
