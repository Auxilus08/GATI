"""
GATI Configuration Loader & Settings Management.
Reads global defaults from default_config.yaml and per-junction parameters
from the config/junctions directory to prevent hardcoding junction values in logic.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

CONFIG_DIR = Path(__file__).parent
JUNCTIONS_DIR = CONFIG_DIR / "junctions"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default_config.yaml"


class ApproachConfig(BaseModel):
    id: str
    name: str
    direction: str
    camera_source: str
    lanes: int = 2
    saturation_flow_pcu_hr: int = 1500
    downstream_junction_id: Optional[str] = None


class PhaseConfig(BaseModel):
    phase_id: int
    name: str
    active_approaches: List[str]
    conflicting_phases: List[int] = Field(default_factory=list)


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class JunctionConfig(BaseModel):
    junction_id: str
    name: str
    corridor_id: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    approaches: List[ApproachConfig]
    phases: List[PhaseConfig]


class PCUWeights(BaseModel):
    two_wheeler: float = 0.5
    auto_rickshaw: float = 0.8
    car: float = 1.0
    bus: float = 3.0
    truck: float = 3.0
    light_commercial: float = 1.5
    bicycle: float = 0.2


class SignalGuardrails(BaseModel):
    min_green_seconds: float = 15.0
    max_green_seconds: float = 60.0
    amber_seconds: float = 4.0
    all_red_seconds: float = 2.0
    pedestrian_clearance_sec: float = 12.0


class MaxPressureConfig(BaseModel):
    pressure_smoothing_alpha: float = 0.3
    min_phase_hold_sec: float = 15.0
    priority_override_multiplier: float = 5.0


class AnalyticsConfig(BaseModel):
    congestion_threshold_pcu: float = 45.0
    anomaly_zscore_threshold: float = 2.5
    forecasting_horizon_minutes: int = 15


class SystemConfig(BaseModel):
    city_name: str = "Nagpur"
    target_junction_count: int = 100
    telemetry_interval_sec: float = 3.0
    environment: str = "development"


class GlobalSettings(BaseSettings):
    system: SystemConfig = Field(default_factory=SystemConfig)
    pcu_weights: PCUWeights = Field(default_factory=PCUWeights)
    signal_guardrails: SignalGuardrails = Field(default_factory=SignalGuardrails)
    max_pressure: MaxPressureConfig = Field(default_factory=MaxPressureConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)

    central_api_host: str = "127.0.0.1"
    central_api_port: int = 8000
    central_api_url: str = "http://127.0.0.1:8000"


def load_global_settings(config_path: Path = DEFAULT_CONFIG_PATH) -> GlobalSettings:
    """Load system global configuration from YAML file."""
    if not config_path.exists():
        return GlobalSettings()
    with open(config_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}
    return GlobalSettings(**raw_data)


def load_junction_config(junction_id_or_file: str) -> JunctionConfig:
    """
    Load specific junction configuration by junction ID or file name.
    Avoids hardcoding geometry in algorithmic code.
    """
    if junction_id_or_file.endswith(".yaml") or junction_id_or_file.endswith(".yml"):
        filepath = JUNCTIONS_DIR / junction_id_or_file
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return JunctionConfig(**data)

    # 1. Try filename search
    candidates = list(JUNCTIONS_DIR.glob(f"*{junction_id_or_file.lower()}*.yaml"))
    if not candidates:
        # 2. Search inside all yaml files by matching junction_id or name
        all_juncs = load_all_junction_configs()
        if junction_id_or_file in all_juncs:
            return all_juncs[junction_id_or_file]
        # Partial match
        for jid, jc in all_juncs.items():
            if junction_id_or_file.lower() in jid.lower() or junction_id_or_file.lower() in jc.name.lower():
                return jc
        raise FileNotFoundError(f"No junction config found for ID: {junction_id_or_file}")

    filepath = candidates[0]
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return JunctionConfig(**data)


def load_all_junction_configs() -> Dict[str, JunctionConfig]:
    """Scan individual and catalogued junction YAML definitions in config/junctions."""
    junctions: Dict[str, JunctionConfig] = {}
    if JUNCTIONS_DIR.exists():
        for yaml_file in JUNCTIONS_DIR.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                # A file may define one junction or a city catalogue under ``junctions``.
                # This keeps operational geometry data portable without duplicating boilerplate.
                entries = data.get("junctions", []) if isinstance(data, dict) and "junctions" in data else [data]
                for entry in entries:
                    jc = JunctionConfig(**entry)
                    junctions[jc.junction_id] = jc
            except Exception as e:
                print(f"[WARN] Failed to load junction config {yaml_file}: {e}")
    return junctions
