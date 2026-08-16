"""
Nagpur Multi-Junction Traffic & Telemetry Simulator.
Generates realistic heterogeneous Indian traffic conditions across ~50-100 junctions,
calculates adaptive Max-Pressure signal decisions, and pushes live telemetry packets to the central API.
"""
import time
import random
import threading
from typing import Dict, List
from config.settings import load_all_junction_configs, load_global_settings
from edge.vision import ApproachQueueMetrics
from edge.controller.signal_state import SignalControllerState, SignalPhaseState
from edge.controller.max_pressure import MaxPressureController
from edge.telemetry.edge_client import EdgeTelemetryClient


class SimulatedJunctionRunner:
    """Runs a single simulated edge junction."""

    def __init__(self, junction_config, global_settings, central_url: str):
        self.config = junction_config
        self.settings = global_settings
        self.controller_state = SignalControllerState(global_settings.signal_guardrails)
        self.mp_controller = MaxPressureController(junction_config, global_settings.max_pressure)
        self.telemetry_client = EdgeTelemetryClient(junction_config.junction_id, central_url)

        # Baseline traffic levels per approach
        self.base_pcu = {app.id: random.uniform(10.0, 35.0) for app in junction_config.approaches}

    def step(self):
        """Simulate 1 step of traffic arrival, queue changes, and signal actuation."""
        # 1. Update traffic arrivals
        approach_metrics: Dict[str, ApproachQueueMetrics] = {}
        for app in self.config.approaches:
            # Fluctuate traffic randomly
            delta = random.uniform(-2.0, 3.5)
            # If current phase is green on this approach, queue discharges
            active_phase = next((p for p in self.config.phases if p.phase_id == self.controller_state.active_phase_id), None)
            is_green = (
                self.controller_state.current_state == SignalPhaseState.GREEN
                and active_phase is not None
                and app.id in active_phase.active_approaches
            )

            if is_green:
                delta -= random.uniform(4.0, 7.0)

            curr_pcu = max(2.0, self.base_pcu[app.id] + delta)
            self.base_pcu[app.id] = curr_pcu

            # Occasional emergency vehicle (1% chance)
            has_emergency = random.random() < 0.01

            approach_metrics[app.id] = ApproachQueueMetrics(
                approach_id=app.id,
                total_pcu=round(curr_pcu, 1),
                vehicle_counts={
                    "two_wheeler": int(curr_pcu * 0.8),
                    "auto_rickshaw": int(curr_pcu * 0.3),
                    "car": int(curr_pcu * 0.4),
                    "bus": 1 if curr_pcu > 20 else 0,
                },
                queue_length_meters=round(curr_pcu * 6.0, 1),
                average_speed_kmh=round(max(8.0, 40.0 - (curr_pcu * 0.6)), 1),
                emergency_vehicle_detected=has_emergency,
                emergency_vehicle_count=1 if has_emergency else 0,
            )

        # 2. Tick state machine
        state_info = self.controller_state.tick()

        # 3. If green, run Max-Pressure decision
        if self.controller_state.current_state == SignalPhaseState.GREEN:
            best_phase_id = self.mp_controller.select_best_phase(
                approach_metrics=approach_metrics,
                current_phase_id=self.controller_state.active_phase_id,
                elapsed_green_sec=self.controller_state.elapsed_phase_time,
                min_green_sec=self.settings.signal_guardrails.min_green_seconds,
                max_green_sec=self.settings.signal_guardrails.max_green_seconds,
            )
            if best_phase_id != self.controller_state.active_phase_id:
                self.controller_state.request_phase_change(best_phase_id)

        # 4. Compute phase pressures for telemetry
        pressures = self.mp_controller.compute_phase_pressures(approach_metrics)

        # 5. Build and send telemetry
        packet = self.telemetry_client.build_telemetry_packet(
            active_phase_id=self.controller_state.active_phase_id,
            state=self.controller_state.current_state.value,
            pressures=pressures,
            approach_metrics=approach_metrics,
            emergency_active=any(m.emergency_vehicle_detected for m in approach_metrics.values()),
        )
        self.telemetry_client.send_telemetry(packet)


class CityTrafficSimulator:
    """Manages multi-junction simulation loop."""

    def __init__(self, central_url: str = "http://127.0.0.1:8000"):
        self.settings = load_global_settings()
        self.junction_configs = load_all_junction_configs()
        self.central_url = central_url
        self.runners: List[SimulatedJunctionRunner] = []
        self.is_running = False

        for jc in self.junction_configs.values():
            self.runners.append(SimulatedJunctionRunner(jc, self.settings, central_url))

    def run_loop(self, interval_sec: float = 3.0):
        """Simulate periodic tick across all junctions."""
        self.is_running = True
        print(f"[SIMULATOR] Starting GATI traffic simulation across {len(self.runners)} junctions...")
        while self.is_running:
            for runner in self.runners:
                runner.step()
            time.sleep(interval_sec)

    def start_background(self):
        t = threading.Thread(target=self.run_loop, daemon=True)
        t.start()
        return t


if __name__ == "__main__":
    sim = CityTrafficSimulator()
    sim.run_loop()
