# GATI: Competition Day Pitch Cheat Sheet & Judge Q&A Guide

**Use this 1-page quick-reference sheet during your live presentation tomorrow.**

---

## ⏱️ 30-Second Elevator Pitch
> *"Every Indian Smart City has spent crores installing CCTV and ANPR cameras, but they are only used for issuing challans after an accident occurs. **GATI** is a retrofit software layer that connects to existing junction cameras, runs edge computer vision, and dynamically optimizes traffic signals using Max-Pressure control while predicting congestion 30 minutes ahead. We cut average vehicular wait time by **30.8%**, reduce 4G bandwidth by **99%**, and save a city like Nagpur **₹10 Crore** over 3 years without buying a single new camera."*

---

## 🎯 3-Minute Live Demo Sequence

| Time | Screen / Action | What to Say & Point At |
| :--- | :--- | :--- |
| **0:00 - 0:45** | **Terminal / Launcher** (`launch_demo.bat`) | Point to the clean modular architecture. Mention that edge detection runs locally on Jetson hardware with strictly metadata (< 5 KB/s) sent upstream. |
| **0:45 - 1:30** | **Panel 1: Live Junction View** (`http://localhost:5173`) | Point to **Approach-based polygons** (not lane lines) accommodating 2-wheelers and autos filtering laterally. Point to live Indian vehicle taxonomy classes (`two_wheeler`, `auto`, `car`, `bus`). Show active signal phase and countdowns. |
| **1:30 - 2:15** | **Panel 2: Command View** | Highlight the headline banner: **30.8% Wait Time Reduction**, **31.9% Queue Reduction**. Demonstrate **Manual Police Override**: enter Operator ID `POLICE_402`, select Phase 2, click Lock $\rightarrow$ show live audit logging and 300s safety auto-release. |
| **2:15 - 3:00** | **Panel 3: Predictive & Risk View** | Point to the **10-30 min Holt Linear Trend Congestion Forecast**. Point to **Live Kinematic Surrogate Safety Risk** (derived from real speed variance and hard braking, not fake historical data). Show Stalled Vehicle incident alert. |

---

## 📊 Key Numbers to Memorize

- **Wait Time Reduction:** **-30.8%** (42.5s down to 29.4s per PCU).
- **Peak Queue Reduction:** **-31.9%** (112m down to 68m).
- **Nagpur Scale Target:** **100 Signalized Junctions** (~400 camera streams).
- **Bandwidth Consumption:** **< 5 KB/s JSON per junction** (vs. 16 Mbps continuous 1080p raw video).
- **3-Year TCO Savings:** **₹57.96 Lakh total** vs **₹10.5+ Crore** for traditional cloud video ICCC (**>94% cost savings**).
- **Code Test Coverage:** **48 / 48 Automated Tests Passing**.

---

## 🥊 Tough Judge Questions & Winning Answers

### Q1: *"Why did you use Max-Pressure instead of Deep Reinforcement Learning (RL)?"*
> **Answer:** *"In high-stakes municipal traffic control, safety and auditability are non-negotiable. Deep RL suffers from reward hacking, lack of explainability, and unsafe trial-and-error exploration on live roads. Max-Pressure (Varaiya-Tassiulas) is mathematically proven to maximize throughput and ensure queue stability, computes in < 1ms on edge hardware, and is 100% deterministic with IRC SP:41 safety guardrails. We treat RL as future shadow-mode work, not an unverified controller."*

### Q2: *"How do you handle Indian traffic where there are no lane markings and 3 bikes squeeze side-by-side?"*
> **Answer:** *"Standard Western systems use virtual lane tripwires which fail completely in Indian conditions. GATI uses **Lane-Free Approach ROI Polygons**. We aggregate all vehicles in the approach polygon into standardized Indian Passenger Car Units (PCU) (Two-Wheeler: 0.5, Auto: 0.8, Car: 1.0, Bus/Truck: 3.0), measuring total volumetric pressure regardless of lane indiscipline."*

### Q3: *"How does this scale to 100 junctions without crashing the server?"*
> **Answer:** *"Because heavy YOLOv8 detection runs at the roadside edge, only lightweight JSON (~5 KB/s) is sent upstream. For 100 junctions, that is only ~33 HTTP requests/sec and ~500 KB/s total bandwidth across the whole city. Our FastAPI backend processes each report in 0.8ms, and adding junction #101 requires only adding one YAML configuration file with zero code changes."*

### Q4: *"What happens if the 4G network drops or a camera gets covered in dust/fog?"*
> **Answer:** *"GATI has code-level graceful degradation:
> 1. If 4G drops, the edge controller continues 100% autonomous adaptive actuation locally and caches telemetry in a 500-packet buffer.
> 2. If camera confidence drops below 0.40 (fog/dust), the controller enters `LOW_CONFIDENCE_HOLD`, holds the last known-good state, and alerts the operator.
> 3. If all approaches gridlock (>25 PCU), it safely falls back to a 30-second round-robin fixed cycle."*

### Q5: *"How do you comply with India's DPDP Act 2023?"*
> **Answer:** *"We strictly adhere to Data Minimization and Purpose Limitation: zero facial recognition is used, video stays at the edge with short 24-48h retention, only anonymized PCU metadata is stored centrally, and all manual overrides are logged with operator ID and timestamps in tamper-evident audit logs."*
