# DECISIONS.md

Log of every non-trivial engineering/product decision made on GATI.

## [2026-08-16] Nagpur-Scale (~50-150 Junctions) Architecture Baseline
- **Decision:** Anchor all design, compute, bandwidth, and storage sizing strictly to a Tier-1/Tier-2 Indian city (specifically Nagpur scale: ~50-150 signalized junctions, ~4 camera feeds per junction).
- **Context:** Traffic AI systems are frequently over-engineered for millions of continuous video streams or multi-region cloud infrastructures, leading to exorbitant operational costs and procurement failure for municipal traffic police departments.
- **Alternatives considered:**
  - *Cloud-Centric Video Streaming:* Streaming all RTSP CCTV video feeds directly to central cloud GPUs for inference. Rejected due to crushing 4G/optical fiber bandwidth costs and extreme cloud GPU rental bills (> ₹25L/month).
  - *Single-Junction Toy Demo:* Building only a localized desktop script without network aggregation or multi-junction coordinator. Rejected because it fails the municipal scalability and ICCC integration requirement.
- **Impact:** Enforces edge inference with lightweight telemetry (< 5 KB/s per junction). The central aggregation layer can run on a single modest on-premise server or entry-level VM.
- **Reversibility:** High if city expands; additional junctions scale horizontally with local edge units without requiring quadratic central server upgrades.

## [2026-08-16] Edge-First Quantized Inference & Metadata-Only Upstream Telemetry
- **Decision:** Perform vehicle detection, tracking, queue estimation, and local emergency vehicle detection directly on edge compute nodes (e.g., Jetson / industrial mini-PC / NVR co-processor) at the junction; transmit only structured JSON telemetry packets (counts, PCU density, phase recommendations, incident alerts) over standard 4G/WAN.
- **Context:** Retrofitting onto existing city CCTV infrastructure means bandwidth from roadside cabinets to the Integrated Command & Control Centre (ICCC) is constrained and jitter-prone.
- **Alternatives considered:**
  - *Periodic Snapshot Uploads:* Uploading raw frames every 2 seconds. Rejected as redundant and bandwidth-heavy compared to structured telemetry.
  - *Hybrid Centralized Video Processing:* Centralized processing with frame dropping. Rejected due to vulnerability to network dropouts impacting real-time signal timing.
- **Impact:** System operates fail-safe even when network drops (junction edge controller continues local adaptive signal actuation autonomously). Total daily upstream data per junction remains < 15-30 MB.
- **Reversibility:** High. Central dashboard consumes standardized REST/WebSocket JSON schemas, agnostic to whether edge is real edge hardware or a local edge emulator process.

## [2026-08-16] Robust Baseline Algorithms Over Undertrained Black-Box Models
- **Decision:** Prioritize mathematically sound, verifiable baselines (Max-Pressure adaptive signal control, Passenger Car Unit [PCU] weighting, Holt-Winters / Exponential Smoothing for short-term congestion forecasting) before introducing complex deep reinforcement learning or heavy neural forecasters.
- **Context:** High-stakes municipal traffic control requires deterministic bounds, auditability for traffic police operators, and reliable operation without months of real-world RL exploration trial-and-error.
- **Alternatives considered:**
  - *Deep Q-Networks (DQN) / Multi-Agent RL:* Popular in academic papers, but prone to reward hacking, catastrophic forgetting, and safety risks during unconstrained phase switching in real traffic.
  - *Complex Transformer/LSTM Congestion Predictors:* Require massive historical dataset collection before achieving convergence.
- **Impact:** Provides immediate, explainable, transparent signal phase optimization and risk scoring that governance bodies can audit and override instantly.
- **Reversibility:** High. Modern modular controller design allows swapping or blending the actuation policy (e.g. Max-Pressure + safety guardrails + optional RL policy shadow mode).
