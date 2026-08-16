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
|           +---> [Time-Series & Incident Store (SQLite/PostgreSQL)]     |
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
- **Edge Vision Worker:** Ingests local RTSP camera streams, performs quantized object detection, multi-lane tracking, and emergency vehicle spotting at ~10-15 FPS.
- **Queue & PCU Engine:** Converts vehicle bounding boxes and lane occupancy into Indian Traffic Standard PCU counts (Two-Wheeler: 0.5, Auto: 0.8, Car: 1.0, Bus/Truck: 3.0).
- **Edge Adaptive Signal Controller:** Executes fail-safe Max-Pressure green time allocation with guardrails (min green 15s, max green 60s, amber 4s, all-red 2s).
- **Central Telemetry Ingestor & Store:** Receives lightweight JSON telemetry from 50-150 junctions, indexes metrics, and logs municipal audit trails.
- **Corridor Coordinator:** Computes dynamic progression offsets along high-density arterial roads (e.g., Wardha Road in Nagpur) for emergency green-waves.
- **ICCC Operator Dashboard:** Responsive governance UI providing real-time city-wide junction states, manual phase overrides, and predictive bottleneck risk alerts.

### Data Flow
`Camera (RTSP) -> Edge Vision Worker -> PCU Queue Estimator -> Local Signal Actuation Controller -> Edge Telemetry Client -> (WAN / 4G JSON) -> Central Ingestor -> Analytics & Coordinator -> Operator Dashboard`

### What Runs at the Edge vs. Centrally
- **Edge (Per Junction):** RTSP decoding, object detection, vehicle tracking, PCU queue computation, emergency vehicle detection, and autonomous fail-safe signal phase switching. Runs locally to guarantee sub-second actuation latency and prevent traffic stoppage during network loss.
- **Centrally (ICCC Server):** Multi-junction coordination, arterial green-wave synchronization, historical congestion analytics, city-wide predictive heatmaps, manual police overrides, and governance reporting.

### Scale Assumptions (Nagpur-Like Scale)
- **Signalized Junction Count:** 50 – 150 junctions (baseline: 100 junctions).
- **Approaches/Cameras per Junction:** 3 to 4 approaches (avg 4 cameras per junction = ~400 total city cameras).
- **Telemetry Frequency:** 1 telemetry packet per junction every 3 to 5 seconds.
- **Expected Requests/sec at Central Server:** ~20 to 50 req/sec (easily handled by a single standard FastAPI instance).
- **Central Bandwidth Consumption:** ~5 KB/s per junction -> ~500 KB/s total city-wide telemetry bandwidth.
- **Daily Telemetry Volume:** ~15-25 MB/junction/day -> ~2.5 GB/day total for 100 junctions.

## 3. Low-Level Design (LLD)
*(This section will be populated with exact interfaces, schemas, and signatures as each component is implemented in code.)*

## 4. Cost & Scale Notes
- **Edge Hardware per Junction:** ₹45,000 – ₹70,000 one-time cost (Industrial edge AI box or Jetson Orin Nano / RK3588 with NPU) retrofitted inside existing traffic controller cabinet.
- **Bandwidth per Junction:** Standard 4G SIM (₹300/month per junction) uploading ~750 MB/month total metadata.
- **Central Server Infrastructure:** Single mid-tier VM / local server (8 vCPUs, 16GB RAM, ~200GB SSD) costing ~₹6,000 – ₹10,000/month or zero incremental cloud cost if deployed on existing Smart City ICCC on-premise hardware.
- **Total Estimated City Rollout (100 Junctions):**
  - Capex: ~₹50L – ₹70L total for 100 junction edge units + installation.
  - Opex: ~₹40,000 – ₹50,000/month total across all 100 junctions for 4G connectivity and server maintenance.
  - *Contrast with Cloud Video Streaming:* Central video streaming of 400 RTSP feeds would cost >₹35L/month in bandwidth and cloud GPU transcode/inference.

## 5. Status / What's Built vs. Planned
- [x] Baseline architecture documents (`DECISIONS.md`, `FLOW.md`).
- [ ] Edge Simulation & Video Processing Pipeline (Quantized vehicle detection, Indian traffic PCU engine, Ambulance priority detection).
- [ ] Adaptive Signal Control Core (Max-Pressure algorithm with safety guardrails).
- [ ] Central Ingestion & Multi-Junction Telemetry API (FastAPI backend, WebSocket live streams).
- [ ] Corridor Synchronization & Arterial Green Wave Coordinator.
- [ ] ICCC Operator Dashboard & Governance Console.
- [ ] Nagpur 100-Junction City Traffic Simulator & Load Test Harness.
