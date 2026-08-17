# FLOW.md

Living description of GATI's overall flow, HLD, and LLD.
Scale target: a city like Nagpur (~50-150 signalized junctions).

## 1. One-paragraph system summary
GATI (Governance-ready AI Traffic Intelligence) is an edge-first, retrofit-ready intelligent traffic control and predictive analytics platform engineered for Indian Tier-1/Tier-2 cities like Nagpur. Operating directly with existing junction CCTV feeds, GATI runs lightweight quantized computer vision inference at the roadside edge to quantify vehicular queue lengths, classify heterogeneous Indian vehicle types (2-wheelers, auto-rickshaws, cars, buses, heavy commercial vehicles) into standardized Passenger Car Units (PCU), and detect emergency vehicles (ambulances, fire engines). Local edge controllers dynamically adjust traffic light green splits using a fail-safe Max-Pressure algorithm with strict minimum/maximum green bounds, while transmitting lightweight telemetry (~5 KB/s per junction) over standard cellular uplinks to an Integrated Command & Control Centre (ICCC) aggregation server for corridor green-waves, risk analytics, and municipal governance oversight.

## 2. High-Level Design (HLD)

### System Diagram
```text
+========================================================================+
|                              EDGE LAYER                                |
|                        (Per Junction: 1 to N)                          |
|                                                                        |
|  [Existing CCTV / ANPR]                                                |
|           | (RTSP Stream - Local LAN)                                  |
|           v                                                            |
|  [Edge Vision Worker (YOLO / MobileNet quantized)]                     |
|           | -> Detections (Class, BBoxes, Direction, Tracks)           |
|           v                                                            |
|  [Queue & PCU Engine + Priority Detector (Ambulance/VIP)]              |
|           |                                                            |
|           +-------------------------------+                            |
|           |                               |                            |
|           v                               v                            |
|  [Local Adaptive Signal]         [Edge Telemetry Client]               |
|  (Max-Pressure / Actuation)      (Batched JSON Metrics / Alerts)       |
|           |                               |                            |
|           v (Relay/NTCIP)                 v (HTTPS/WebSocket)          |
|  [Traffic Light Controller]        ~~~ Standard 4G/WAN Uplink ~~~      |
+===========================================|============================+
                                            |
+===========================================v============================+
|                          AGGREGATION LAYER                             |
|                (City Central Server / ICCC Gateway)                    |
|                                                                        |
|  [Central Ingestion API (FastAPI / WebSockets)]                        |
|           |                                                            |
|           +---> [Corridor Coordinator (Green Wave Sync)]               |
|           +---> [Congestion & Incident Forecasting (Holt-Winters)]     |
|           +---> [Time-Series & Incident Store (In-Memory / SQLite)]     |
+===========================================|============================+
                                            |
+===========================================v============================+
|                           INTERFACE LAYER                              |
|             (Traffic Police ICCC Operator Console & Dashboards)        |
|                                                                        |
|  - Real-time Junction Heatmaps & Status Grid (~100 Junctions)          |
|  - Emergency Corridor / Green Wave Overrides                           |
|  - Congestion Bottleneck & Anomaly Alerts                              |
|  - Governance & Transparency Audit Logs                                |
+========================================================================+
```

### Major Components and Their Responsibility
- **Edge Vision Worker (`edge/vision/`):** Ingests local RTSP camera streams, performs quantized object detection, multi-lane tracking, and emergency vehicle spotting at ~10-15 FPS.
- **Queue & PCU Engine (`edge/vision/pcu_engine.py`):** Converts vehicle bounding boxes and lane occupancy into Indian Traffic Standard PCU counts (Two-Wheeler: 0.5, Auto: 0.8, Car: 1.0, Bus/Truck: 3.0).
- **Edge Adaptive Signal Controller (`edge/controller/`):** Executes fail-safe Max-Pressure green time allocation with guardrails (min green 15s, max green 60s, amber 4s, all-red 2s).
- **Edge Telemetry Client (`edge/telemetry/`):** Sends compact JSON telemetry (< 5 KB/s) to the central server with offline fallback buffering.
- **Central Telemetry Ingestor & API (`central/api/`):** FastAPI async server ingesting ~20-50 req/sec from 100 junctions, maintaining live state and WebSocket broadcasting.
- **Analytics & Forecaster (`central/analytics/`):** Holt's double exponential queue smoothing, Z-score anomaly surge detection, and 0-100 Junction Risk Index.
- **Corridor Coordinator (`central/coordinator/`):** Computes dynamic green-wave offsets along high-density arterial corridors (e.g., Wardha Road in Nagpur).
- **ICCC Operator Dashboard (`frontend/`):** React dashboard for real-time junction monitoring, risk alerts, green wave planning, and manual police phase overrides.
- **Nagpur Simulation Harness (`simulation/`):** Multi-junction traffic and telemetry load generator.

### Data Flow
`Camera (RTSP) -> Edge Vision Worker -> PCU Queue Estimator -> Local Signal Actuation Controller -> Edge Telemetry Client -> (WAN / 4G JSON) -> Central Ingestor -> Analytics & Coordinator -> Operator Dashboard`

### Scale Assumptions (Nagpur-Like Scale)
- **Signalized Junction Count:** 50 – 150 junctions (baseline: 100 junctions).
- **Approaches/Cameras per Junction:** 3 to 4 approaches (avg 4 cameras per junction = ~400 total city cameras).
- **Telemetry Frequency:** 1 telemetry packet per junction every 3 to 5 seconds.
- **Expected Requests/sec at Central Server:** ~20 to 50 req/sec.
- **Central Bandwidth Consumption:** ~5 KB/s per junction -> ~500 KB/s total city-wide telemetry bandwidth.
- **Daily Telemetry Volume:** ~15-25 MB/junction/day -> ~2.5 GB/day total for 100 junctions.

## 3. Low-Level Design (LLD)

### Actual Folder / Module Layout
```text
.
├── config/
│   ├── default_config.yaml           # Global PCU weights, guardrails, thresholds
│   ├── settings.py                   # Pydantic BaseSettings & YAML loader
│   └── junctions/
│       ├── nagpur_sitabuldi.yaml     # Sitabuldi junction geometry & phases
│       └── nagpur_varieties_sq.yaml  # Varieties Square geometry & phases
├── edge/
│   ├── vision/
│   │   ├── __init__.py               # Core vision pipeline exports & dataclasses
│   │   ├── taxonomy.py               # Indian traffic taxonomy & COCO heuristic mapping
│   │   ├── tracker.py                # ByteTrack integration & per-vehicle velocity estimation
│   │   ├── detector.py               # YOLOv8 & ONNX edge detector + approach ROI queue engine
│   │   ├── export_onnx.py            # FP16/INT8 ONNX/TensorRT edge export utility
│   │   ├── video_pipeline.py         # RTSP/Video stream processor & structured logger
│   │   └── pcu_engine.py             # Indian PCU calculation engine
│   ├── controller/
│   │   ├── __init__.py               # Controller module exports
│   │   ├── signal_state.py           # Red/Amber/Green safety state machine
│   │   ├── max_pressure.py           # Max-Pressure adaptive controller & decision engine
│   │   ├── override_manager.py       # Human operator phase lock & audit log manager
│   │   └── comparison_harness.py     # Before/After fixed-time vs adaptive comparison engine
│   └── telemetry/
│       ├── __init__.py
│       └── edge_client.py            # Telemetry client with offline caching
├── scripts/
│   ├── run_traffic_pipeline.py       # Vision pipeline runner & synthetic video generator
│   └── compare_signal_performance.py # Signal performance benchmark & before/after evidence CLI
├── tests/
│   ├── __init__.py
│   ├── test_vision_pipeline.py       # Vision unit test suite
│   └── test_signal_controller.py     # Max-Pressure, override, and comparison test suite
├── central/
│   ├── api/
│   │   ├── main.py                   # FastAPI app & CORS middleware
│   │   ├── websocket_manager.py      # Live WebSocket operator connection pool
│   │   ├── schemas/
│   │   │   └── telemetry_schema.py   # Pydantic telemetry & override models
│   │   └── routers/
│   │       ├── telemetry.py          # /api/v1/telemetry/report, batch, ws
│   │       ├── junctions.py          # /api/v1/junctions/, override endpoints
│   │       ├── corridor.py           # /api/v1/corridors/ green wave endpoints
│   │       └── analytics.py          # /api/v1/analytics/ city summary & forecast
│   ├── analytics/
│   │   ├── forecaster.py             # Holt's linear queue forecaster
│   │   ├── anomaly_detector.py       # Z-score statistical surge detector
│   │   └── risk_index.py             # 0-100 Junction Risk Index evaluator
│   └── coordinator/
│       └── green_wave.py             # Arterial offset coordinator
├── simulation/
│   ├── __init__.py
│   └── city_simulator.py             # Multi-junction traffic & telemetry simulator
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── components/               # Navbar, MetricsBar, JunctionCard, CorridorView, EmergencyModal
        └── services/api.js           # REST client layer
```

### Key API Schemas & Data Shapes

- **Edge Vision Frame Telemetry (`vision_frames.jsonl`):**
```json
{
  "junction_id": "NGP_J01_SITABULDI",
  "frame_idx": 45,
  "timestamp": 1723800003.0,
  "vehicle_count": 5,
  "vehicles": [
    {
      "track_id": 1,
      "class": "car",
      "confidence": 0.92,
      "bbox": [260, 280, 310, 340],
      "speed_kmh": 22.4,
      "is_emergency": false
    },
    {
      "track_id": 2,
      "class": "auto_rickshaw",
      "confidence": 0.86,
      "bbox": [320, 310, 360, 360],
      "speed_kmh": 14.1,
      "is_emergency": false
    }
  ],
  "approaches": {
    "APP_NORTH": {
      "total_pcu": 7.4,
      "queue_length_m": 44.4,
      "avg_speed_kmh": 18.2,
      "emergency": false
    }
  }
}
```

- **Edge Vision Window Telemetry (`vision_windows.jsonl` / `vision_windows.csv`):**
```json
{
  "junction_id": "NGP_J01_SITABULDI",
  "timestamp": 1723800003.0,
  "approaches": {
    "APP_NORTH": {
      "approach_id": "APP_NORTH",
      "timestamp": 1723800003.0,
      "total_pcu": 14.5,
      "queue_length_meters": 87.0,
      "average_speed_kmh": 24.5,
      "vehicle_counts": {
        "two_wheeler": 12,
        "auto_rickshaw": 4,
        "car": 5,
        "bus": 1,
        "truck": 0,
        "cycle": 1,
        "pedestrian": 2,
        "cart": 0
      },
      "emergency_vehicle_detected": false,
      "emergency_vehicle_count": 0
    }
  }
}
```

- **Human Operator Override Audit Record (`override_audit.jsonl`):**
```json
{
  "override_id": "8f3b12a9",
  "junction_id": "NGP_J01_SITABULDI",
  "phase_id": 2,
  "operator_id": "POLICE_ICCC_402",
  "action": "LOCK",
  "timestamp": 1723800120.0,
  "reason": "VIP Motorcade Clearance",
  "duration_sec": 120.0
}
```

- **Signal Controller Comparison Summary Schema (`comparison_summary.json`):**
```json
{
  "junction_id": "NGP_J01_SITABULDI",
  "duration_sec": 300.0,
  "total_timesteps": 100,
  "fixed_total_delay_pcu_sec": 14200.0,
  "fixed_avg_queue_m": 48.2,
  "fixed_peak_queue_m": 112.0,
  "fixed_avg_wait_sec": 42.5,
  "mp_total_delay_pcu_sec": 9850.0,
  "mp_avg_queue_m": 32.8,
  "mp_peak_queue_m": 68.0,
  "mp_avg_wait_sec": 29.4,
  "wait_time_reduction_pct": 30.8,
  "queue_reduction_pct": 31.9,
  "total_delay_saved_pcu_sec": 4350.0,
  "estimated_fuel_saved_liters": 0.96,
  "co2_reduction_kg": 2.22
}
```

- **Central Ingestion Payload:**
```json
{
  "junction_id": "NGP_J01_SITABULDI",
  "timestamp": 1723800000.0,
  "active_phase_id": 1,
  "signal_state": "GREEN",
  "pressures": {"1": 18.4, "2": 7.2, "3": 4.1},
  "approaches": {
    "APP_NORTH": {
      "total_pcu": 14.5,
      "vehicle_counts": {"two_wheeler": 12, "auto_rickshaw": 4, "car": 5, "bus": 1},
      "queue_length_m": 87.0,
      "avg_speed_kmh": 24.5,
      "emergency": false
    }
  },
  "emergency_active": false
}
```

## 4. Cost & Scale Notes
- **Edge Hardware per Junction:** ₹45,000 – ₹70,000 one-time cost (Industrial edge AI box or Jetson Orin Nano / RK3588 with NPU) retrofitted inside existing traffic controller cabinet.
- **Bandwidth per Junction:** Standard 4G SIM (₹300/month per junction) uploading ~750 MB/month total metadata.
- **Central Server Infrastructure:** Single mid-tier VM / local server (8 vCPUs, 16GB RAM, ~200GB SSD) costing ~₹6,000 – ₹10,000/month or zero incremental cloud cost on Smart City ICCC on-premise hardware.
- **Total Estimated City Rollout (100 Junctions):**
  - Capex: ~₹50L – ₹70L total for 100 junction edge units + installation.
  - Opex: ~₹40,000 – ₹50,000/month total across all 100 junctions for 4G connectivity and server maintenance.

## 5. Status / What's Built vs. Planned
- [x] Baseline architecture documents (`DECISIONS.md`, `FLOW.md`).
- [x] Modular repository layout with clean separation of concerns.
- [x] Zero-hardcoding configuration system (`config/default_config.yaml`, `config/junctions/*.yaml`, `config/settings.py`).
- [x] Indian Traffic PCU calculation engine (`edge/vision/pcu_engine.py`).
- [x] **YOLOv8 Edge Detection & ByteTrack Multi-Object Tracking Pipeline** (`edge/vision/`):
  - [x] YOLOv8 base detector with PyTorch and ONNX backends (`edge/vision/detector.py`).
  - [x] ByteTrack multi-object tracking with trajectory history & velocity calculation (`edge/vision/tracker.py`).
  - [x] Indian traffic class taxonomy mapping with auto-rickshaw/cart heuristics (`edge/vision/taxonomy.py`).
  - [x] Lane-free Approach ROI queue length ($m$) & speed ($km/h$) aggregation (`edge/vision/detector.py`, `video_pipeline.py`).
  - [x] ONNX FP16/INT8 export pipeline for Jetson Orin Nano edge deployment (`edge/vision/export_onnx.py`).
  - [x] Structured JSON & CSV telemetry logging (`edge/vision/video_pipeline.py`).
  - [x] CLI execution runner & synthetic Nagpur traffic video generator (`scripts/run_traffic_pipeline.py`).
  - [!] *Note on IDD fine-tuning:* Full dataset fine-tuning on India Driving Dataset (IDD) is **DEFERRED** due to dataset volume and compute constraints; baseline uses pretrained COCO weights with geometric taxonomy translation heuristics.
- [x] **Adaptive Signal Control & Before/After Comparison Module** (`edge/controller/`):
  - [x] Max-Pressure adaptive controller with pressure smoothing & hysteresis (`edge/controller/max_pressure.py`).
  - [x] Safety state machine & guardrails: min green (15s), max green (60s), amber (4s), all-red (2s) (`edge/controller/signal_state.py`).
  - [x] Human operator override hook & governance audit logging (`edge/controller/override_manager.py`).
  - [x] Signal performance comparison harness computing wait time and queue reduction from real tracked data (`edge/controller/comparison_harness.py`).
  - [x] Before/after performance comparison CLI tool (`scripts/compare_signal_performance.py`).
  - [!] *Note on RL controller:* Reinforcement learning is explicitly **DEFERRED** in favor of mathematically provable, safe Max-Pressure control.
- [x] Edge telemetry client with offline buffer (`edge/telemetry/edge_client.py`).
- [x] Central FastAPI backend with REST & WebSockets (`central/api/`).
- [x] Holt's Linear Queue Forecaster & Z-Score Anomaly Detector (`central/analytics/`).
- [x] Junction Risk Index Engine (`central/analytics/risk_index.py`).
- [x] Corridor Green Wave Progression Coordinator (`central/coordinator/green_wave.py`).
- [x] Nagpur Multi-Junction Traffic Simulator (`simulation/city_simulator.py`).
- [x] React Vite Operator Dashboard (`frontend/`).


